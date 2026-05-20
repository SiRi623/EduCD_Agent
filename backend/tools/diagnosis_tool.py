from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from models.dina import DINA
from tools.data_loader import load_q_matrix, load_responses, validate_dataset


BACKEND_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BACKEND_DIR / "outputs"
MASTERY_RESULTS_PATH = OUTPUT_DIR / "mastery_results.json"
DINA_PARAMS_PATH = OUTPUT_DIR / "dina_params.json"


def train_and_save_dina(
    responses: pd.DataFrame | None = None,
    q_matrix: pd.DataFrame | None = None,
    mastery_path: Path = MASTERY_RESULTS_PATH,
    params_path: Path = DINA_PARAMS_PATH,
) -> Dict[str, Any]:
    dataset_report = validate_dataset()
    if not dataset_report["is_valid"]:
        raise ValueError(f"数据集校验失败：{dataset_report['errors']}")

    model = train_dina_model(
        responses=responses if responses is not None else load_responses(),
        q_matrix=q_matrix if q_matrix is not None else load_q_matrix(),
    )
    model.save_outputs(mastery_path=mastery_path, params_path=params_path)
    return {
        "mastery_results": model.to_mastery_payload(),
        "dina_params": model.to_params_payload(),
        "dataset": dataset_report,
    }


def train_dina_model(responses: pd.DataFrame, q_matrix: pd.DataFrame) -> DINA:
    model = DINA()
    model.fit(responses=responses, q_matrix=q_matrix)
    return model


def diagnose_student(
    student_id: str,
    responses: pd.DataFrame,
    q_matrix: pd.DataFrame,
) -> Dict[str, float]:
    student_responses = responses[responses["student_id"] == student_id].copy()
    if student_responses.empty:
        raise ValueError(f"未找到学生 {student_id} 的答题记录")

    _ = q_matrix  # Preserve the existing function signature used by app.py and class_analyzer.py.
    trained_mastery = _load_student_mastery(student_id)
    if trained_mastery is None:
        raise FileNotFoundError(
            "未找到已训练的 DINA 诊断结果，请先在 backend 目录运行：python train_dina.py"
        )
    return trained_mastery


def load_mastery_results(path: Path = MASTERY_RESULTS_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"未找到 DINA 掌握度结果文件：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_dina_params(path: Path = DINA_PARAMS_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"未找到 DINA 参数文件：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_student_mastery(student_id: str) -> Dict[str, float] | None:
    if not MASTERY_RESULTS_PATH.exists():
        return None

    payload = load_mastery_results(MASTERY_RESULTS_PATH)
    student_payload = payload.get("students", {}).get(student_id)
    if not student_payload:
        return None

    mastery = student_payload.get("mastery", {})
    return {concept_id: float(probability) for concept_id, probability in mastery.items()}
