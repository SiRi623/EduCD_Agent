from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from tools.diagnosis_tool import diagnose_student


def analyze_class(
    responses: pd.DataFrame,
    q_matrix: pd.DataFrame,
    knowledge_base: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    knowledge_base = knowledge_base or {}
    student_ids = sorted(responses["student_id"].dropna().unique().tolist())
    student_mastery = {
        student_id: diagnose_student(student_id, responses, q_matrix)
        for student_id in student_ids
    }

    concept_ids = [column for column in q_matrix.columns if column != "question_id"]
    class_average = {}
    for concept_id in concept_ids:
        values = [mastery.get(concept_id, 0.0) for mastery in student_mastery.values()]
        class_average[concept_id] = round(sum(values) / len(values), 4) if values else 0.0

    weak_rank = sorted(class_average.items(), key=lambda item: item[1])
    weak_top3 = [
        {
            "concept_id": concept_id,
            "concept_name": _concept_name(concept_id, knowledge_base),
            "average_mastery": average_mastery,
        }
        for concept_id, average_mastery in weak_rank[:3]
    ]

    high_risk_student_details: List[Dict[str, Any]] = []
    for student_id, mastery in student_mastery.items():
        average_mastery = sum(mastery.values()) / len(mastery) if mastery else 0.0
        if average_mastery < 0.6:
            high_risk_student_details.append(
                {
                    "student_id": student_id,
                    "student_name": _student_name(student_id, responses),
                    "average_mastery": round(average_mastery, 4),
                    "weak_concepts": [
                        {
                            "concept_id": concept_id,
                            "concept_name": _concept_name(concept_id, knowledge_base),
                            "mastery": round(float(score), 4),
                        }
                        for concept_id, score in mastery.items()
                        if float(score) < 0.6
                    ],
                }
            )

    return {
        "student_mastery": student_mastery,
        "class_average_mastery": class_average,
        "class_average_mastery_detail": [
            {
                "concept_id": concept_id,
                "concept_name": _concept_name(concept_id, knowledge_base),
                "average_mastery": score,
            }
            for concept_id, score in class_average.items()
        ],
        "weak_knowledge_top3": [(item["concept_id"], item["average_mastery"]) for item in weak_top3],
        "weak_concepts_rank": weak_top3,
        "high_risk_students": [item["student_id"] for item in high_risk_student_details],
        "high_risk_student_details": high_risk_student_details,
        "teacher_suggestions": _build_teacher_suggestions(weak_top3, high_risk_student_details),
    }


def _build_teacher_suggestions(
    weak_top3: List[Dict[str, Any]],
    high_risk_students: List[Dict[str, Any]],
) -> List[str]:
    suggestions = []
    if weak_top3:
        names = "、".join(item["concept_name"] for item in weak_top3)
        suggestions.append(f"优先围绕 {names} 设计 10 到 15 分钟的课堂补救练习。")
        suggestions.append("对薄弱知识点采用基础题、同类题、变式题的递进练习路径。")
    if high_risk_students:
        suggestions.append("对风险学生安排错题面批或小组辅导，重点检查解题步骤是否完整。")
    return suggestions or ["班级整体掌握较稳定，可继续通过综合题保持迁移训练。"]


def _concept_name(concept_id: str, knowledge_base: Dict[str, Any]) -> str:
    item = knowledge_base.get(concept_id, {})
    return str(item.get("concept_name") or item.get("knowledge_name") or concept_id)


def _student_name(student_id: str, responses: pd.DataFrame) -> str:
    if "student_name" not in responses.columns:
        return student_id
    rows = responses[responses["student_id"] == student_id]
    names = rows["student_name"].dropna().astype(str).unique().tolist()
    return names[0] if names else student_id
