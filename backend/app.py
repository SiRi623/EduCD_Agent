from __future__ import annotations

import os
from typing import Any, Dict, List

import pandas as pd
from flask import Flask, jsonify
from flask_cors import CORS

from agents.cot_agent import analyze_diagnosis
from agents.qwen_client import QwenClient
from agents.reflection_agent import optimize_report
from agents.report_agent import generate_report
from tools.class_analyzer import analyze_class
from tools.data_loader import (
    load_all_data,
    load_knowledge_base,
    load_q_matrix,
    load_questions,
    load_responses,
    validate_dataset,
)
from tools.diagnosis_tool import (
    DINA_PARAMS_PATH,
    MASTERY_RESULTS_PATH,
    diagnose_student,
    load_dina_params,
    train_and_save_dina,
)
from tools.memory_store import (
    clear_memory,
    get_class_recent_memory,
    get_memory_context,
    get_student_memory,
    save_diagnosis_memory,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.json.ensure_ascii = False
CORS(app)

analysis_cache: Dict[str, Dict[str, Any]] = {}


def success_response(data: Any = None, message: str = "请求成功"):
    return jsonify({"success": True, "message": message, "data": data})


def error_response(message: str, status_code: int = 500):
    response = jsonify({"success": False, "message": message, "data": None})
    response.status_code = status_code
    return response


def handle_api_error(exc: Exception):
    status_code = 404 if isinstance(exc, FileNotFoundError) else 400 if isinstance(exc, ValueError) else 500
    return error_response(str(exc), status_code=status_code)


def analyze_student(student_id: str) -> Dict[str, Any]:
    """Run the CDM-driven diagnosis and agent explanation chain for one student."""
    questions, q_matrix, responses, knowledge_base = load_all_data()
    student_responses = _get_student_responses(student_id, responses)
    question_map = {question["question_id"]: question for question in questions}
    student_name = _get_student_name(student_id, student_responses)

    mastery = diagnose_student(student_id, responses, q_matrix)
    wrong_questions = _build_wrong_questions(student_responses, question_map)

    qwen_client = QwenClient()
    cot_result = analyze_diagnosis(
        qwen_client=qwen_client,
        diagnosis_input={
            "student_id": student_id,
            "student_name": student_name,
            "mastery": mastery,
            "wrong_questions": wrong_questions,
            "knowledge_base": knowledge_base,
        },
    )
    error_analysis = cot_result["question_explanations"]

    overall_performance = _calculate_overall_performance(student_responses)
    memory_context = get_memory_context(student_id, recent_limit=3)
    original_report = generate_report(
        qwen_client=qwen_client,
        student_id=student_id,
        mastery=mastery,
        error_analyses=error_analysis,
        overall_performance=overall_performance,
        knowledge_base=knowledge_base,
        student_name=student_name,
        memory_context=memory_context,
    )
    structured_report = optimize_report(
        qwen_client=qwen_client,
        original_report=original_report,
        mastery=mastery,
        error_analyses=error_analysis,
    )
    memory_record = _save_analysis_memory(
        student_id=student_id,
        student_name=student_name,
        mastery=mastery,
        wrong_questions=wrong_questions,
        structured_report=structured_report,
    )

    return {
        "student_id": student_id,
        "student_name": student_name,
        "mastery": mastery,
        "wrong_questions": wrong_questions,
        "cot_result": cot_result,
        "error_analysis": error_analysis,
        "report": structured_report.get("report_text", ""),
        "structured_report": structured_report,
        "memory": get_student_memory(student_id),
        "memory_record": memory_record,
    }


def get_cached_analysis(student_id: str, record_memory: bool = False) -> Dict[str, Any]:
    was_cached = student_id in analysis_cache
    if not was_cached:
        analysis_cache[student_id] = analyze_student(student_id)
    elif record_memory:
        analysis = analysis_cache[student_id]
        analysis["memory_record"] = _save_analysis_memory(
            student_id=analysis["student_id"],
            student_name=analysis["student_name"],
            mastery=analysis["mastery"],
            wrong_questions=analysis["wrong_questions"],
            structured_report=analysis["structured_report"],
        )
        analysis["memory"] = get_student_memory(student_id)
    return analysis_cache[student_id]


def _save_analysis_memory(
    student_id: str,
    student_name: str,
    mastery: Dict[str, float],
    wrong_questions: List[Dict[str, Any]],
    structured_report: Dict[str, Any],
) -> Dict[str, Any]:
    return save_diagnosis_memory(
        student_id=student_id,
        student_name=student_name,
        mastery=mastery,
        wrong_question_count=len(wrong_questions),
        structured_report=structured_report,
    )


def _get_student_responses(student_id: str, responses: pd.DataFrame) -> pd.DataFrame:
    student_responses = responses[responses["student_id"] == student_id].copy()
    if student_responses.empty:
        raise ValueError(f"未找到学生 {student_id} 的答题记录")
    return student_responses


def _build_wrong_questions(
    student_responses: pd.DataFrame,
    question_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    wrong_responses = student_responses[student_responses["is_correct"] == 0]
    wrong_questions: List[Dict[str, Any]] = []

    for _, response in wrong_responses.iterrows():
        question = question_map.get(response["question_id"])
        if not question:
            continue
        wrong_questions.append(
            {
                "question_id": question["question_id"],
                "content": question["content"],
                "student_answer": str(response["student_answer"]),
                "correct_answer": question["correct_answer"],
                "concept_ids": question.get("concept_ids", question.get("knowledge_points", [])),
                "knowledge_points": question["knowledge_points"],
                "difficulty": question.get("difficulty"),
            }
        )

    return wrong_questions


def _get_student_name(student_id: str, student_responses: pd.DataFrame) -> str:
    if "student_name" not in student_responses.columns:
        return student_id
    names = student_responses["student_name"].dropna().astype(str).unique().tolist()
    return names[0] if names else student_id


def _calculate_overall_performance(student_responses: pd.DataFrame) -> Dict[str, Any]:
    total_questions = len(student_responses)
    correct_count = int(student_responses["is_correct"].sum())
    accuracy = correct_count / total_questions if total_questions else 0.0
    return {
        "total_questions": total_questions,
        "correct_count": correct_count,
        "wrong_count": total_questions - correct_count,
        "accuracy": accuracy,
    }


@app.route("/api/health", methods=["GET"])
def health_check():
    try:
        qwen_client = QwenClient()
        return success_response(
            data={
                "service": "EduCD-Agent",
                "version": "0.4.0",
                "qwen": {
                    "status": qwen_client.status_text(),
                    "api_key_configured": bool(qwen_client.api_key),
                    "model": qwen_client.model,
                },
                "dina": {
                    "mastery_results_ready": MASTERY_RESULTS_PATH.exists(),
                    "params_ready": DINA_PARAMS_PATH.exists(),
                    "mastery_results_path": str(MASTERY_RESULTS_PATH),
                    "params_path": str(DINA_PARAMS_PATH),
                },
            },
            message="EduCD-Agent backend is running",
        )
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/students", methods=["GET"])
def get_students():
    try:
        responses = load_responses()
        student_ids = sorted(responses["student_id"].dropna().unique().tolist())
        return success_response(student_ids)
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/students/detail", methods=["GET"])
def get_students_detail():
    try:
        responses = load_responses()
        return success_response(_build_student_list(responses))
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/questions", methods=["GET"])
def get_questions():
    try:
        questions = load_questions()
        knowledge_base = load_knowledge_base()
        return success_response(_enrich_questions(questions, knowledge_base))
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/diagnose/<student_id>", methods=["GET"])
def diagnose(student_id: str):
    try:
        responses = load_responses()
        q_matrix = load_q_matrix()
        student_responses = _get_student_responses(student_id, responses)
        mastery = diagnose_student(student_id, responses, q_matrix)
        knowledge_base = load_knowledge_base()
        return success_response(
            {
                "student_id": student_id,
                "student_name": _get_student_name(student_id, student_responses),
                "mastery": mastery,
                "mastery_detail": _build_mastery_detail(mastery, knowledge_base),
            }
        )
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/errors/<student_id>", methods=["GET"])
def get_error_analysis(student_id: str):
    try:
        analysis = get_cached_analysis(student_id)
        return success_response(
            {
                "student_id": student_id,
                "wrong_questions": analysis["wrong_questions"],
                "error_analysis": analysis["error_analysis"],
            }
        )
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/report/<student_id>", methods=["GET"])
def get_report(student_id: str):
    try:
        analysis = get_cached_analysis(student_id)
        return success_response(
            {
                "student_id": student_id,
                "report": analysis["report"],
                "structured_report": analysis["structured_report"],
            }
        )
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/full-analysis/<student_id>", methods=["GET"])
def get_full_analysis(student_id: str):
    try:
        return success_response(get_cached_analysis(student_id, record_memory=True))
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/memory/<student_id>", methods=["GET"])
def get_memory(student_id: str):
    try:
        return success_response(get_student_memory(student_id))
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/memory/class/recent", methods=["GET"])
def get_class_memory():
    try:
        return success_response(get_class_recent_memory())
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/memory/clear", methods=["POST"])
def clear_memory_api():
    try:
        clear_memory()
        analysis_cache.clear()
        return success_response(data=None, message="诊断记忆已清空")
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/class/summary", methods=["GET"])
@app.route("/api/class-summary", methods=["GET"])
def get_class_summary():
    try:
        responses = load_responses()
        q_matrix = load_q_matrix()
        knowledge_base = load_knowledge_base()
        summary = analyze_class(responses, q_matrix, knowledge_base)
        return success_response(
            {
                "class_average_mastery": summary["class_average_mastery"],
                "class_average_mastery_detail": summary["class_average_mastery_detail"],
                "weak_knowledge_top3": [
                    {
                        "knowledge": item["concept_id"],
                        "concept_id": item["concept_id"],
                        "concept_name": item["concept_name"],
                        "average_mastery": item["average_mastery"],
                    }
                    for item in summary["weak_concepts_rank"]
                ],
                "weak_concepts_rank": summary["weak_concepts_rank"],
                "high_risk_students": summary["high_risk_students"],
                "high_risk_student_details": summary["high_risk_student_details"],
                "teacher_suggestions": summary["teacher_suggestions"],
            }
        )
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/train/dina", methods=["POST"])
def train_dina_api():
    try:
        result = train_and_save_dina()
        analysis_cache.clear()
        training = result["dina_params"]["training"]
        return success_response(
            {
                "training": training,
                "dataset": result["dataset"],
                "outputs": {
                    "mastery_results": str(MASTERY_RESULTS_PATH),
                    "dina_params": str(DINA_PARAMS_PATH),
                },
                "student_count": len(result["mastery_results"]["students"]),
                "concept_count": len(result["mastery_results"]["concept_ids"]),
                "question_count": len(result["mastery_results"]["question_ids"]),
            },
            message="DINA 模型训练完成",
        )
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/dina/params", methods=["GET"])
def get_dina_params():
    try:
        return success_response(load_dina_params())
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/dataset/validate", methods=["GET"])
def validate_dataset_api():
    try:
        report = validate_dataset()
        if report["is_valid"]:
            return success_response(report)
        response = jsonify({"success": False, "message": "数据集校验失败", "data": report})
        response.status_code = 400
        return response
    except Exception as exc:
        return handle_api_error(exc)


@app.route("/api/cache/clear", methods=["GET"])
def clear_cache():
    try:
        analysis_cache.clear()
        return success_response(data=None, message="缓存已清空")
    except Exception as exc:
        return handle_api_error(exc)


def _build_student_list(responses: pd.DataFrame) -> List[Dict[str, str]]:
    students: List[Dict[str, str]] = []
    for student_id in sorted(responses["student_id"].dropna().unique().tolist()):
        rows = responses[responses["student_id"] == student_id]
        student_name = _get_student_name(student_id, rows)
        students.append({"student_id": student_id, "student_name": student_name, "label": f"{student_name}（{student_id}）"})
    return students


def _enrich_questions(
    questions: List[Dict[str, Any]],
    knowledge_base: Dict[str, Any],
) -> List[Dict[str, Any]]:
    enriched = []
    for question in questions:
        concepts = [
            {
                "concept_id": concept_id,
                "concept_name": _concept_name(concept_id, knowledge_base),
            }
            for concept_id in question.get("concept_ids", question.get("knowledge_points", []))
        ]
        enriched.append({**question, "concepts": concepts})
    return enriched


def _build_mastery_detail(
    mastery: Dict[str, float],
    knowledge_base: Dict[str, Any],
) -> List[Dict[str, Any]]:
    return [
        {
            "concept_id": concept_id,
            "concept_name": _concept_name(concept_id, knowledge_base),
            "mastery": round(float(score), 4),
            "level": _mastery_level(float(score)),
        }
        for concept_id, score in mastery.items()
    ]


def _concept_name(concept_id: str, knowledge_base: Dict[str, Any]) -> str:
    item = knowledge_base.get(concept_id, {})
    return str(item.get("concept_name") or item.get("knowledge_name") or concept_id)


def _mastery_level(score: float) -> str:
    if score >= 0.8:
        return "掌握较好"
    if score >= 0.6:
        return "基本掌握"
    if score >= 0.4:
        return "掌握不稳"
    return "明显薄弱"


if __name__ == "__main__":
    print("EduCD-Agent Flask backend is running...")
    print("API base URL: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
