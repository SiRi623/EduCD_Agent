from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents.qwen_client import QwenClient
from app import analyze_student, analysis_cache
from tools.data_loader import load_knowledge_base, load_responses
from tools.diagnosis_tool import MASTERY_RESULTS_PATH, train_and_save_dina


BACKEND_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BACKEND_DIR / "outputs"
REPORTS_OUTPUT = OUTPUT_DIR / "reports.json"
EVALUATION_OUTPUT = OUTPUT_DIR / "report_evaluation.json"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    payload = evaluate_reports()
    REPORTS_OUTPUT.write_text(
        json.dumps(payload["reports"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    EVALUATION_OUTPUT.write_text(
        json.dumps(
            {
                "summary": payload["summary"],
                "comparisons": payload["comparisons"],
                "ablation": payload["ablation"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "reports_output": str(REPORTS_OUTPUT),
                "evaluation_output": str(EVALUATION_OUTPUT),
                **payload["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def evaluate_reports() -> Dict[str, Any]:
    if not MASTERY_RESULTS_PATH.exists():
        train_and_save_dina()

    # Keep evaluation deterministic and fast; production API still uses Qwen
    # whenever DASHSCOPE_API_KEY is present.
    original_key = os.environ.get("DASHSCOPE_API_KEY")
    os.environ["DASHSCOPE_API_KEY"] = ""
    analysis_cache.clear()
    try:
        responses = load_responses()
        knowledge_base = load_knowledge_base()
        student_ids = sorted(responses["student_id"].unique().tolist())
        reports: Dict[str, Any] = {}
        comparisons = []
        ablation_rows = []

        for student_id in student_ids:
            analysis = analyze_student(student_id)
            ordinary_report = _build_plain_llm_report(student_id, responses)
            cdm_cot_report = analysis["structured_report"]

            ordinary_score = _score_plain_report(ordinary_report)
            cdm_cot_score = _score_structured_report(cdm_cot_report)
            comparisons.append(
                {
                    "student_id": student_id,
                    "ordinary_llm": ordinary_score,
                    "cdm_cot_agent": cdm_cot_score,
                    "score_delta": round(cdm_cot_score["total_score"] - ordinary_score["total_score"], 4),
                }
            )
            ablation_rows.append(_build_ablation_row(student_id, analysis, responses, knowledge_base))
            reports[student_id] = {
                "student_id": student_id,
                "student_name": analysis.get("student_name", student_id),
                "ordinary_llm_report": ordinary_report,
                "cdm_cot_report": cdm_cot_report,
            }

        summary = {
            "student_count": len(student_ids),
            "ordinary_llm_average_score": _average(
                row["ordinary_llm"]["total_score"] for row in comparisons
            ),
            "cdm_cot_average_score": _average(
                row["cdm_cot_agent"]["total_score"] for row in comparisons
            ),
            "average_score_delta": _average(row["score_delta"] for row in comparisons),
            "qwen_mode_for_evaluation": QwenClient().status_text(),
        }
        return {
            "summary": summary,
            "reports": reports,
            "comparisons": comparisons,
            "ablation": ablation_rows,
        }
    finally:
        if original_key is None:
            os.environ.pop("DASHSCOPE_API_KEY", None)
        else:
            os.environ["DASHSCOPE_API_KEY"] = original_key


def _build_plain_llm_report(student_id: str, responses) -> Dict[str, Any]:
    student_responses = responses[responses["student_id"] == student_id]
    correct_count = int(student_responses["is_correct"].sum())
    total_count = len(student_responses)
    accuracy = correct_count / total_count if total_count else 0.0
    return {
        "student_id": student_id,
        "overall": f"学生本次答题正确率为 {accuracy:.0%}，建议继续巩固错题。",
        "weak_concepts": [],
        "error_reasons": ["根据错题情况进行复习，但未结合 Q 矩阵和 DINA 掌握度。"],
        "suggestions": ["复习错题并完成同类练习。"],
        "uses_cdm": False,
        "uses_cot": False,
    }


def _score_plain_report(report: Dict[str, Any]) -> Dict[str, Any]:
    structure = 0.4
    cdm_consistency = 0.0
    error_specificity = 0.3 if report.get("error_reasons") else 0.0
    actionability = 0.5 if report.get("suggestions") else 0.0
    total = _weighted_total(structure, cdm_consistency, error_specificity, actionability)
    return {
        "structure": structure,
        "cdm_consistency": cdm_consistency,
        "error_specificity": error_specificity,
        "actionability": actionability,
        "total_score": total,
    }


def _score_structured_report(report: Dict[str, Any]) -> Dict[str, Any]:
    required = [
        "overall_diagnosis",
        "mastery_summary",
        "weak_concepts",
        "typical_error_analysis",
        "personalized_suggestions",
        "practice_path",
    ]
    structure = sum(1 for field in required if report.get(field)) / len(required)
    self_check = report.get("self_check", {})
    cdm_consistency = 1.0 if self_check.get("is_consistent_with_cdm") else 0.5
    error_specificity = 1.0 if self_check.get("has_specific_error_reason") else 0.5
    actionability = 1.0 if self_check.get("has_actionable_suggestion") else 0.5
    total = _weighted_total(structure, cdm_consistency, error_specificity, actionability)
    return {
        "structure": round(structure, 4),
        "cdm_consistency": cdm_consistency,
        "error_specificity": error_specificity,
        "actionability": actionability,
        "total_score": total,
    }


def _build_ablation_row(student_id: str, analysis: Dict[str, Any], responses, knowledge_base) -> Dict[str, Any]:
    student_responses = responses[responses["student_id"] == student_id]
    accuracy = float(student_responses["is_correct"].mean()) if len(student_responses) else 0.0
    mastery = analysis["mastery"]
    weak_by_dina = [concept_id for concept_id, score in mastery.items() if float(score) < 0.6]
    weak_by_cot = analysis["cot_result"].get("weak_concepts", [])
    return {
        "student_id": student_id,
        "only_correct_rate": {
            "accuracy": round(accuracy, 4),
            "diagnosis_signal": "整体正确率，无法定位潜在知识点掌握概率。",
        },
        "dina_mastery": {
            "weak_concepts": [
                _concept_name(concept_id, knowledge_base)
                for concept_id in weak_by_dina
            ],
            "diagnosis_signal": "可定位低掌握知识点，但缺少自然语言错因解释。",
        },
        "dina_plus_cot_agent": {
            "weak_concepts": [
                _concept_name(concept_id, knowledge_base)
                for concept_id in weak_by_cot
            ],
            "error_count": len(analysis.get("error_analysis", [])),
            "diagnosis_signal": "同时包含 CDM 掌握度、错因解释、认知断点和学习建议。",
        },
    }


def _weighted_total(structure: float, cdm_consistency: float, error_specificity: float, actionability: float) -> float:
    return round(
        structure * 0.25
        + cdm_consistency * 0.3
        + error_specificity * 0.25
        + actionability * 0.2,
        4,
    )


def _average(values) -> float:
    values = list(values)
    return round(sum(values) / len(values), 4) if values else 0.0


def _concept_name(concept_id: str, knowledge_base: Dict[str, Any]) -> str:
    item = knowledge_base.get(concept_id, {})
    return str(item.get("concept_name") or concept_id)


if __name__ == "__main__":
    main()
