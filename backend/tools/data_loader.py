from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def load_questions(path: Path | None = None) -> List[Dict[str, Any]]:
    file_path = path or DATA_DIR / "questions.json"
    with file_path.open("r", encoding="utf-8") as file:
        questions = json.load(file)

    for question in questions:
        question["question_id"] = str(question["question_id"]).strip()
        concept_ids = question.get("concept_ids") or question.get("knowledge_points") or []
        normalized_concepts = [str(concept_id).strip() for concept_id in concept_ids]
        question["concept_ids"] = normalized_concepts
        # Keep the original demo contract: other modules still read knowledge_points.
        question["knowledge_points"] = normalized_concepts

    return questions


def load_q_matrix(path: Path | None = None) -> pd.DataFrame:
    file_path = path or DATA_DIR / "q_matrix.csv"
    q_matrix = pd.read_csv(file_path, dtype={"question_id": str})
    q_matrix["question_id"] = q_matrix["question_id"].str.strip()

    for column in _concept_columns(q_matrix):
        q_matrix[column] = q_matrix[column].fillna(0).astype(int)

    return q_matrix


def load_responses(path: Path | None = None) -> pd.DataFrame:
    file_path = path or DATA_DIR / "responses.csv"
    responses = pd.read_csv(file_path, dtype={"student_id": str, "question_id": str})
    responses["student_id"] = responses["student_id"].str.strip()
    responses["question_id"] = responses["question_id"].str.strip()

    if "score" not in responses.columns and "is_correct" in responses.columns:
        responses["score"] = responses["is_correct"].astype(float)
    if "is_correct" not in responses.columns and "score" in responses.columns:
        responses["is_correct"] = (responses["score"].astype(float) >= 1.0).astype(int)

    responses["score"] = responses["score"].astype(float)
    responses["is_correct"] = responses["is_correct"].astype(int)
    return responses


def load_knowledge_base(path: Path | None = None) -> Dict[str, Any]:
    file_path = path or DATA_DIR / "knowledge_base.json"
    with file_path.open("r", encoding="utf-8") as file:
        knowledge_base = json.load(file)

    normalized: Dict[str, Any] = {}
    for concept_id, item in knowledge_base.items():
        normalized_id = str(item.get("concept_id", concept_id)).strip()
        normalized[normalized_id] = {**item, "concept_id": normalized_id}

    return normalized


def load_all_data() -> Tuple[List[Dict[str, Any]], pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    return load_questions(), load_q_matrix(), load_responses(), load_knowledge_base()


def validate_dataset(
    questions_path: Path | None = None,
    q_matrix_path: Path | None = None,
    responses_path: Path | None = None,
    knowledge_base_path: Path | None = None,
) -> Dict[str, Any]:
    """Validate the local education dataset before CDM training.

    The function returns a structured report instead of raising immediately so
    CLI scripts, APIs, and tests can show actionable errors to the user.
    """
    errors: List[str] = []
    warnings: List[str] = []

    try:
        questions = load_questions(questions_path)
        q_matrix = load_q_matrix(q_matrix_path)
        responses = load_responses(responses_path)
        knowledge_base = load_knowledge_base(knowledge_base_path)
    except Exception as exc:
        return {
            "is_valid": False,
            "errors": [f"数据文件读取失败：{exc}"],
            "warnings": [],
            "stats": {},
        }

    _validate_questions(questions, knowledge_base, errors, warnings)
    _validate_q_matrix(q_matrix, questions, knowledge_base, errors, warnings)
    _validate_responses(responses, questions, errors, warnings)

    concept_ids = sorted(knowledge_base.keys())
    question_ids = [question["question_id"] for question in questions]
    student_ids = sorted(responses["student_id"].dropna().unique().tolist())
    stats = {
        "question_count": len(question_ids),
        "concept_count": len(concept_ids),
        "student_count": len(student_ids),
        "response_count": int(len(responses)),
        "concept_ids": concept_ids,
        "student_ids": student_ids,
    }

    return {
        "is_valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
    }


def _validate_questions(
    questions: List[Dict[str, Any]],
    knowledge_base: Dict[str, Any],
    errors: List[str],
    warnings: List[str],
) -> None:
    required_fields = {"question_id", "content", "correct_answer", "difficulty", "concept_ids"}
    seen_question_ids: set[str] = set()

    for index, question in enumerate(questions, start=1):
        missing = required_fields - set(question.keys())
        if missing:
            errors.append(f"questions.json 第 {index} 条缺少字段：{sorted(missing)}")
            continue

        question_id = question["question_id"]
        if question_id in seen_question_ids:
            errors.append(f"questions.json 存在重复 question_id：{question_id}")
        seen_question_ids.add(question_id)

        if question["difficulty"] not in VALID_DIFFICULTIES:
            warnings.append(f"{question_id} 的 difficulty 不是推荐值 easy/medium/hard：{question['difficulty']}")

        concept_ids = question.get("concept_ids", [])
        if not concept_ids:
            errors.append(f"{question_id} 未绑定任何知识点")

        for concept_id in concept_ids:
            if concept_id not in knowledge_base:
                errors.append(f"{question_id} 引用了知识库中不存在的 concept_id：{concept_id}")


def _validate_q_matrix(
    q_matrix: pd.DataFrame,
    questions: List[Dict[str, Any]],
    knowledge_base: Dict[str, Any],
    errors: List[str],
    warnings: List[str],
) -> None:
    if "question_id" not in q_matrix.columns:
        errors.append("q_matrix.csv 缺少 question_id 列")
        return

    question_ids = {question["question_id"] for question in questions}
    q_question_ids = set(q_matrix["question_id"].dropna().tolist())
    concept_columns = _concept_columns(q_matrix)
    concept_column_set = set(concept_columns)
    knowledge_concepts = set(knowledge_base.keys())

    duplicated = q_matrix[q_matrix["question_id"].duplicated()]["question_id"].tolist()
    if duplicated:
        errors.append(f"q_matrix.csv 存在重复 question_id：{sorted(set(duplicated))}")

    missing_in_q = sorted(question_ids - q_question_ids)
    extra_in_q = sorted(q_question_ids - question_ids)
    if missing_in_q:
        errors.append(f"q_matrix.csv 缺少题目：{missing_in_q}")
    if extra_in_q:
        errors.append(f"q_matrix.csv 包含 questions.json 中不存在的题目：{extra_in_q}")

    missing_concepts = sorted(knowledge_concepts - concept_column_set)
    extra_concepts = sorted(concept_column_set - knowledge_concepts)
    if missing_concepts:
        errors.append(f"q_matrix.csv 缺少知识点列：{missing_concepts}")
    if extra_concepts:
        errors.append(f"q_matrix.csv 包含 knowledge_base.json 中不存在的知识点列：{extra_concepts}")

    invalid_values = {}
    for column in concept_columns:
        invalid_rows = q_matrix[~q_matrix[column].isin([0, 1])]["question_id"].tolist()
        if invalid_rows:
            invalid_values[column] = invalid_rows
    if invalid_values:
        errors.append(f"q_matrix.csv 只能使用 0/1 标记知识点，异常位置：{invalid_values}")

    for question in questions:
        question_id = question["question_id"]
        row = q_matrix[q_matrix["question_id"] == question_id]
        if row.empty:
            continue

        q_concepts = {
            column
            for column in concept_columns
            if int(row.iloc[0][column]) == 1
        }
        declared_concepts = set(question.get("concept_ids", []))
        if q_concepts != declared_concepts:
            errors.append(
                f"{question_id} 的 questions.json 知识点 {sorted(declared_concepts)} "
                f"与 q_matrix.csv 标记 {sorted(q_concepts)} 不一致"
            )
        if not q_concepts:
            warnings.append(f"{question_id} 在 q_matrix.csv 中没有标记任何知识点")


def _validate_responses(
    responses: pd.DataFrame,
    questions: List[Dict[str, Any]],
    errors: List[str],
    warnings: List[str],
) -> None:
    required_columns = {"student_id", "question_id", "student_answer", "score", "is_correct"}
    missing_columns = required_columns - set(responses.columns)
    if missing_columns:
        errors.append(f"responses.csv 缺少字段：{sorted(missing_columns)}")
        return

    question_ids = {question["question_id"] for question in questions}
    response_question_ids = set(responses["question_id"].dropna().tolist())
    unknown_questions = sorted(response_question_ids - question_ids)
    if unknown_questions:
        errors.append(f"responses.csv 包含未知 question_id：{unknown_questions}")

    invalid_scores = responses[~responses["score"].between(0.0, 1.0)]
    if not invalid_scores.empty:
        errors.append(f"responses.csv 的 score 必须在 0 到 1 之间，异常行数：{len(invalid_scores)}")

    invalid_correct = responses[~responses["is_correct"].isin([0, 1])]
    if not invalid_correct.empty:
        errors.append(f"responses.csv 的 is_correct 必须为 0 或 1，异常行数：{len(invalid_correct)}")

    duplicated = responses[responses.duplicated(subset=["student_id", "question_id"], keep=False)]
    if not duplicated.empty:
        pairs = duplicated[["student_id", "question_id"]].drop_duplicates().to_dict("records")
        errors.append(f"responses.csv 存在重复答题记录：{pairs}")

    students = responses["student_id"].dropna().unique().tolist()
    for student_id in students:
        answered = set(responses[responses["student_id"] == student_id]["question_id"].tolist())
        missing = sorted(question_ids - answered)
        if missing:
            warnings.append(f"学生 {student_id} 缺少部分题目答题记录：{missing}")


def _concept_columns(q_matrix: pd.DataFrame) -> List[str]:
    return [column for column in q_matrix.columns if column != "question_id"]
