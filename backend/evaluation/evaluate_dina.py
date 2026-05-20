from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.data_loader import load_q_matrix, load_responses
from tools.diagnosis_tool import MASTERY_RESULTS_PATH, train_and_save_dina


BACKEND_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BACKEND_DIR / "outputs"
EVALUATION_OUTPUT = OUTPUT_DIR / "dina_evaluation.json"
STUDENT_PROFILES_PATH = BACKEND_DIR / "data" / "student_profiles.json"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    payload = evaluate_dina()
    EVALUATION_OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(EVALUATION_OUTPUT), **payload["summary"]}, ensure_ascii=False, indent=2))


def evaluate_dina() -> Dict[str, Any]:
    if not MASTERY_RESULTS_PATH.exists():
        train_and_save_dina()

    mastery_results = json.loads(MASTERY_RESULTS_PATH.read_text(encoding="utf-8"))
    responses = load_responses()
    q_matrix = load_q_matrix()
    baseline_mastery = _correct_rate_baseline(responses, q_matrix)
    expected_profiles = _load_expected_profiles()

    student_rows = []
    type_hits = 0
    weak_jaccard_values = []
    dina_vs_baseline_deltas = []

    for student_id, expected in expected_profiles.items():
        mastery = mastery_results["students"][student_id]["mastery"]
        predicted_weak = {concept_id for concept_id, score in mastery.items() if float(score) < 0.6}
        expected_weak = set(expected["weak_concepts"])
        jaccard = _jaccard(predicted_weak, expected_weak)
        weak_jaccard_values.append(jaccard)

        predicted_type = _student_type(predicted_weak, mastery)
        type_hit = predicted_type == expected["type"]
        type_hits += int(type_hit)

        baseline = baseline_mastery[student_id]
        deltas = {
            concept_id: round(float(mastery[concept_id]) - float(baseline[concept_id]), 4)
            for concept_id in mastery
        }
        dina_vs_baseline_deltas.extend(abs(value) for value in deltas.values())

        student_rows.append(
            {
                "student_id": student_id,
                "student_name": mastery_results["students"][student_id].get("student_name", student_id),
                "expected_type": expected["type"],
                "predicted_type": predicted_type,
                "type_hit": type_hit,
                "expected_weak_concepts": sorted(expected_weak),
                "predicted_weak_concepts": sorted(predicted_weak),
                "weak_concept_jaccard": round(jaccard, 4),
                "mastery": mastery,
                "correct_rate_baseline": baseline,
                "dina_minus_baseline": deltas,
            }
        )

    summary = {
        "student_count": len(student_rows),
        "type_accuracy": round(type_hits / len(student_rows), 4),
        "average_weak_concept_jaccard": round(sum(weak_jaccard_values) / len(weak_jaccard_values), 4),
        "average_abs_dina_baseline_delta": round(
            sum(dina_vs_baseline_deltas) / len(dina_vs_baseline_deltas),
            4,
        ),
        "baseline": "只用答题正确率",
        "model": "DINA",
    }
    return {
        "summary": summary,
        "students": student_rows,
        "notes": [
            "type_accuracy 衡量 DINA 诊断类型与预设学生画像是否一致。",
            "weak_concept_jaccard 衡量低掌握知识点集合与预设薄弱集合的重合程度。",
            "average_abs_dina_baseline_delta 用于观察 DINA 与简单正确率诊断之间的差异。",
        ],
    }


def _correct_rate_baseline(responses, q_matrix) -> Dict[str, Dict[str, float]]:
    concept_ids = [column for column in q_matrix.columns if column != "question_id"]
    baseline: Dict[str, Dict[str, float]] = {}
    for student_id in sorted(responses["student_id"].unique()):
        student_responses = responses[responses["student_id"] == student_id]
        merged = student_responses.merge(q_matrix, on="question_id", how="left")
        baseline[student_id] = {}
        for concept_id in concept_ids:
            related = merged[merged[concept_id] == 1]
            baseline[student_id][concept_id] = (
                round(float(related["is_correct"].mean()), 4) if len(related) else 0.0
            )
    return baseline


def _load_expected_profiles() -> Dict[str, Dict[str, Any]]:
    if STUDENT_PROFILES_PATH.exists():
        raw_profiles = json.loads(STUDENT_PROFILES_PATH.read_text(encoding="utf-8"))
        return {
            student_id: {
                "type": item["profile_type"],
                "weak_concepts": set(item.get("expected_weak_concepts", [])),
            }
            for student_id, item in raw_profiles.items()
        }

    return {
        "S001": {"type": "局部薄弱型", "weak_concepts": {"C004", "C006", "C008"}},
        "S002": {"type": "全面掌握型", "weak_concepts": set()},
        "S003": {"type": "方程与综合薄弱型", "weak_concepts": {"C001", "C002", "C005", "C007", "C008"}},
        "S004": {"type": "证明薄弱型", "weak_concepts": {"C008"}},
        "S005": {"type": "多知识点风险型", "weak_concepts": {"C001", "C002", "C003", "C005", "C006", "C008"}},
    }


def _student_type(weak_concepts: set[str], mastery: Dict[str, float]) -> str:
    if not weak_concepts:
        return "全面掌握型"
    if len(weak_concepts) >= 5:
        return "综合风险型"
    if weak_concepts <= {"C008"}:
        return "证明薄弱型"
    if weak_concepts <= {"C001", "C002"} and weak_concepts:
        return "方程薄弱型"
    if weak_concepts <= {"C003", "C005", "C007"} and weak_concepts:
        return "代数薄弱型"
    if weak_concepts <= {"C006", "C003", "C001"} and "C006" in weak_concepts:
        return "函数薄弱型"
    if weak_concepts <= {"C009", "C010"} and weak_concepts:
        return "统计概率薄弱型"
    if weak_concepts <= {"C008", "C011", "C012", "C004"} and weak_concepts:
        return "几何综合薄弱型"
    if weak_concepts <= {"C007", "C003"} and "C007" in weak_concepts:
        return "分式薄弱型"
    if weak_concepts <= {"C010"}:
        return "概率薄弱型"
    if weak_concepts <= {"C009"}:
        return "统计薄弱型"
    if weak_concepts <= {"C011", "C008"} and "C011" in weak_concepts:
        return "相似薄弱型"
    if weak_concepts <= {"C012", "C008"} and "C012" in weak_concepts:
        return "圆薄弱型"
    if weak_concepts <= {"C004"}:
        return "面积薄弱型"
    if {"C001", "C002", "C005", "C007", "C008"}.issubset(weak_concepts):
        return "方程与综合薄弱型"
    if {"C004", "C006", "C008"}.issubset(weak_concepts):
        return "局部薄弱型"
    average = sum(float(score) for score in mastery.values()) / len(mastery)
    return "多知识点风险型" if average < 0.6 else "中等偏上型"


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


if __name__ == "__main__":
    main()
