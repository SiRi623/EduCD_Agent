from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


BACKEND_DIR = Path(__file__).resolve().parents[1]
MEMORY_DIR = BACKEND_DIR / "memory"
SHORT_MEMORY_PATH = MEMORY_DIR / "short_memory.json"
HISTORY_RECORDS_PATH = MEMORY_DIR / "history_records.json"
MAX_HISTORY_PER_STUDENT = 10


def get_student_memory(student_id: str, recent_limit: int = MAX_HISTORY_PER_STUDENT) -> Dict[str, Any]:
    short_memory = load_short_memory()
    history_records = load_history_records()
    student_history = [
        record for record in history_records if record.get("student_id") == student_id
    ]
    student_history = sorted(
        student_history,
        key=lambda record: str(record.get("diagnosed_at", "")),
        reverse=True,
    )
    return {
        "student_id": student_id,
        "short_memory": short_memory.get(student_id),
        "history": student_history[:recent_limit],
        "history_count": len(student_history),
    }


def get_memory_context(student_id: str, recent_limit: int = 3) -> Dict[str, Any]:
    memory = get_student_memory(student_id, recent_limit=recent_limit)
    history = memory["history"]
    persistent_weak = _persistent_weak_concepts(history)
    return {
        "recent_diagnoses": history,
        "persistent_weak_concepts": persistent_weak,
        "has_history": bool(history),
    }


def get_class_recent_memory() -> Dict[str, Any]:
    short_memory = load_short_memory()
    history_records = load_history_records()
    latest_by_student: Dict[str, Dict[str, Any]] = {}
    for record in sorted(history_records, key=lambda item: str(item.get("diagnosed_at", ""))):
        latest_by_student[record["student_id"]] = record

    return {
        "short_memory": short_memory,
        "latest_records": list(latest_by_student.values()),
        "history_count": len(history_records),
    }


def save_diagnosis_memory(
    student_id: str,
    student_name: str,
    mastery: Dict[str, float],
    wrong_question_count: int,
    structured_report: Dict[str, Any],
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    weak_concepts = _extract_weak_concepts(structured_report, mastery)
    report_summary = str(structured_report.get("overall_diagnosis", "")).strip()
    self_check = structured_report.get("self_check", {})

    record = {
        "diagnosed_at": now,
        "student_id": student_id,
        "student_name": student_name,
        "mastery": {concept_id: round(float(score), 4) for concept_id, score in mastery.items()},
        "weak_concepts": weak_concepts,
        "wrong_question_count": int(wrong_question_count),
        "report_summary": report_summary,
        "reflection": {
            "is_consistent_with_cdm": bool(self_check.get("is_consistent_with_cdm")),
            "has_specific_error_reason": bool(self_check.get("has_specific_error_reason")),
            "has_actionable_suggestion": bool(self_check.get("has_actionable_suggestion")),
            "has_vague_expression": bool(self_check.get("has_vague_expression")),
            "issues": self_check.get("issues", []),
        },
    }

    short_memory = load_short_memory()
    short_memory[student_id] = {
        "student_id": student_id,
        "student_name": student_name,
        "mastery": record["mastery"],
        "weak_concepts": weak_concepts,
        "wrong_question_count": record["wrong_question_count"],
        "report_summary": report_summary,
        "updated_at": now,
    }
    _write_json(SHORT_MEMORY_PATH, short_memory)

    history_records = load_history_records()
    history_records.append(record)
    history_records = _trim_history(history_records)
    _write_json(HISTORY_RECORDS_PATH, history_records)
    return record


def clear_memory() -> None:
    _write_json(SHORT_MEMORY_PATH, {})
    _write_json(HISTORY_RECORDS_PATH, [])


def load_short_memory() -> Dict[str, Any]:
    data = _read_json(SHORT_MEMORY_PATH, default={})
    return data if isinstance(data, dict) else {}


def load_history_records() -> List[Dict[str, Any]]:
    data = _read_json(HISTORY_RECORDS_PATH, default=[])
    return data if isinstance(data, list) else []


def _trim_history(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        student_id = str(record.get("student_id", "")).strip()
        if not student_id:
            continue
        grouped.setdefault(student_id, []).append(record)

    trimmed: List[Dict[str, Any]] = []
    for student_records in grouped.values():
        ordered = sorted(
            student_records,
            key=lambda item: str(item.get("diagnosed_at", "")),
            reverse=True,
        )
        trimmed.extend(ordered[:MAX_HISTORY_PER_STUDENT])

    return sorted(trimmed, key=lambda item: str(item.get("diagnosed_at", "")))


def _extract_weak_concepts(
    structured_report: Dict[str, Any],
    mastery: Dict[str, float],
) -> List[Dict[str, Any]]:
    weak_concepts = structured_report.get("weak_concepts", [])
    if isinstance(weak_concepts, list) and weak_concepts:
        return [
            {
                "concept_id": str(item.get("concept_id", "")),
                "concept_name": str(item.get("concept_name", item.get("concept_id", ""))),
                "mastery": round(float(item.get("mastery", mastery.get(item.get("concept_id", ""), 0.0))), 4),
            }
            for item in weak_concepts
            if isinstance(item, dict) and item.get("concept_id")
        ]

    return [
        {
            "concept_id": concept_id,
            "concept_name": concept_id,
            "mastery": round(float(score), 4),
        }
        for concept_id, score in mastery.items()
        if float(score) < 0.6
    ]


def _persistent_weak_concepts(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts: Dict[str, Dict[str, Any]] = {}
    for record in records:
        for item in record.get("weak_concepts", []):
            concept_id = item.get("concept_id")
            if not concept_id:
                continue
            current = counts.setdefault(
                concept_id,
                {
                    "concept_id": concept_id,
                    "concept_name": item.get("concept_name", concept_id),
                    "count": 0,
                },
            )
            current["count"] += 1

    return sorted(counts.values(), key=lambda item: item["count"], reverse=True)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
