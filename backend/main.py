from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

import pandas as pd

from agents.cot_agent import analyze_wrong_answer
from agents.qwen_client import QwenClient
from agents.reflection_agent import optimize_report
from agents.report_agent import generate_report
from tools.class_analyzer import analyze_class
from tools.data_loader import load_all_data
from tools.diagnosis_tool import diagnose_student


DEFAULT_STUDENT_ID = "S001"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    questions, q_matrix, responses, knowledge_base = load_all_data()
    question_map = {question["question_id"]: question for question in questions}

    student_id = DEFAULT_STUDENT_ID
    qwen_client = QwenClient()

    print("=" * 72)
    print("EduCD-Agent：面向智慧教育认知诊断的思维链可解释智能体 Demo")
    print("=" * 72)
    print(f"当前学生 ID：{student_id}")
    print(f"Qwen 运行状态：{qwen_client.status_text()}")
    print()

    mastery = diagnose_student(student_id, responses, q_matrix)
    student_responses = responses[responses["student_id"] == student_id].copy()
    wrong_responses = student_responses[student_responses["is_correct"] == 0]

    print("【知识点掌握度】")
    print(format_mastery(mastery))
    print()

    error_analyses = build_error_analyses(
        qwen_client=qwen_client,
        wrong_responses=wrong_responses,
        question_map=question_map,
        mastery=mastery,
        knowledge_base=knowledge_base,
    )

    print("【错因分析 JSON】")
    print(json.dumps(error_analyses, ensure_ascii=False, indent=2))
    print()

    overall_performance = calculate_overall_performance(student_responses)
    original_report = generate_report(
        qwen_client=qwen_client,
        student_id=student_id,
        mastery=mastery,
        error_analyses=error_analyses,
        overall_performance=overall_performance,
        knowledge_base=knowledge_base,
    )
    final_report = optimize_report(
        qwen_client=qwen_client,
        original_report=original_report,
        mastery=mastery,
        error_analyses=error_analyses,
    )

    print("【最终学情报告】")
    print(final_report.get("report_text", final_report))
    print()
    print("【Reflection 自检】")
    print(json.dumps(final_report.get("self_check", {}), ensure_ascii=False, indent=2))
    print()

    class_summary = analyze_class(responses, q_matrix)
    print("【班级诊断摘要】")
    print("班级薄弱知识点 Top3：")
    for index, (knowledge, score) in enumerate(class_summary["weak_knowledge_top3"], start=1):
        print(f"{index}. {knowledge}：平均掌握度 {score:.2f}")
    high_risk_students = class_summary["high_risk_students"]
    print(f"高风险学生列表：{', '.join(high_risk_students) if high_risk_students else '无'}")
    print("=" * 72)


def build_error_analyses(
    qwen_client: QwenClient,
    wrong_responses: pd.DataFrame,
    question_map: Dict[str, Dict[str, Any]],
    mastery: Dict[str, float],
    knowledge_base: Dict[str, Any],
) -> List[Dict[str, Any]]:
    analyses: List[Dict[str, Any]] = []
    for _, response in wrong_responses.iterrows():
        question = question_map.get(response["question_id"])
        if not question:
            continue

        analysis = analyze_wrong_answer(
            qwen_client=qwen_client,
            wrong_question=question,
            student_answer=str(response["student_answer"]),
            mastery=mastery,
            knowledge_base=knowledge_base,
        )
        analysis["question_id"] = question["question_id"]
        analysis["student_answer"] = str(response["student_answer"])
        analysis["correct_answer"] = question["correct_answer"]
        analyses.append(analysis)

    return analyses


def calculate_overall_performance(student_responses: pd.DataFrame) -> Dict[str, Any]:
    total_questions = len(student_responses)
    correct_count = int(student_responses["is_correct"].sum())
    accuracy = correct_count / total_questions if total_questions else 0.0
    return {
        "total_questions": total_questions,
        "correct_count": correct_count,
        "wrong_count": total_questions - correct_count,
        "accuracy": accuracy,
    }


def format_mastery(mastery: Dict[str, float]) -> str:
    return "\n".join(f"- {knowledge}：{score:.2f}" for knowledge, score in mastery.items())


if __name__ == "__main__":
    main()
