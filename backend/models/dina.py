from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd


class DINA:
    """Train and infer a deterministic-input noisy-and-gate CDM model.

    The implementation uses EM over all latent mastery patterns. This is a good
    fit for the demo dataset because the number of concepts is small and the
    resulting student mastery vector is easy to feed into the agent layer.
    """

    def __init__(
        self,
        max_iter: int = 200,
        tol: float = 1e-5,
        min_param: float = 0.01,
        max_param: float = 0.45,
    ) -> None:
        self.max_iter = max_iter
        self.tol = tol
        self.min_param = min_param
        self.max_param = max_param

        self.concept_ids: List[str] = []
        self.question_ids: List[str] = []
        self.student_ids: List[str] = []
        self.student_names: Dict[str, str] = {}
        self.patterns: np.ndarray | None = None
        self.eta: np.ndarray | None = None
        self.slip: np.ndarray | None = None
        self.guess: np.ndarray | None = None
        self.prior: np.ndarray | None = None
        self.posterior: np.ndarray | None = None
        self.log_likelihood_history: List[float] = []
        self.converged = False
        self.n_iter = 0

    def fit(self, responses: pd.DataFrame, q_matrix: pd.DataFrame) -> "DINA":
        self._prepare_metadata(responses, q_matrix)
        response_matrix = self._build_response_matrix(responses)
        q_values = q_matrix.set_index("question_id").loc[self.question_ids, self.concept_ids].to_numpy(dtype=int)

        self.patterns = self._build_patterns(len(self.concept_ids))
        self.eta = self._build_eta(self.patterns, q_values)
        pattern_count = len(self.patterns)
        item_count = len(self.question_ids)

        self.prior = np.full(pattern_count, 1.0 / pattern_count)
        self.slip = np.full(item_count, 0.2)
        self.guess = np.full(item_count, 0.2)

        previous_ll = -np.inf
        for iteration in range(1, self.max_iter + 1):
            posterior, log_likelihood = self._e_step(response_matrix)
            self.posterior = posterior
            self.log_likelihood_history.append(float(log_likelihood))
            self._m_step(response_matrix, posterior)

            self.n_iter = iteration
            if abs(log_likelihood - previous_ll) < self.tol:
                self.converged = True
                break
            previous_ll = log_likelihood

        if self.posterior is None:
            self.posterior, _ = self._e_step(response_matrix)
        return self

    def predict_mastery(self) -> Dict[str, Dict[str, float]]:
        self._ensure_fitted()
        assert self.posterior is not None
        assert self.patterns is not None

        mastery_results: Dict[str, Dict[str, float]] = {}
        for student_index, student_id in enumerate(self.student_ids):
            mastery_prob = self.posterior[student_index] @ self.patterns
            mastery_results[student_id] = {
                concept_id: round(float(prob), 4)
                for concept_id, prob in zip(self.concept_ids, mastery_prob)
            }
        return mastery_results

    def predict_student(self, student_id: str) -> Dict[str, float]:
        mastery_results = self.predict_mastery()
        if student_id not in mastery_results:
            raise ValueError(f"未找到学生 {student_id} 的 DINA 诊断结果")
        return mastery_results[student_id]

    def get_item_params(self) -> Dict[str, Dict[str, float]]:
        self._ensure_fitted()
        assert self.slip is not None
        assert self.guess is not None

        return {
            question_id: {
                "slip": round(float(self.slip[index]), 4),
                "guess": round(float(self.guess[index]), 4),
            }
            for index, question_id in enumerate(self.question_ids)
        }

    def to_mastery_payload(self) -> Dict[str, Any]:
        self._ensure_fitted()
        assert self.posterior is not None
        assert self.patterns is not None

        mastery = self.predict_mastery()
        students: Dict[str, Any] = {}
        for student_index, student_id in enumerate(self.student_ids):
            best_pattern_index = int(np.argmax(self.posterior[student_index]))
            best_pattern = self.patterns[best_pattern_index]
            students[student_id] = {
                "student_id": student_id,
                "student_name": self.student_names.get(student_id, student_id),
                "mastery": mastery[student_id],
                "most_likely_pattern": {
                    concept_id: int(value)
                    for concept_id, value in zip(self.concept_ids, best_pattern)
                },
                "pattern_probability": round(float(self.posterior[student_index, best_pattern_index]), 4),
            }

        return {
            "model": "DINA",
            "concept_ids": self.concept_ids,
            "question_ids": self.question_ids,
            "students": students,
        }

    def to_params_payload(self) -> Dict[str, Any]:
        self._ensure_fitted()
        final_ll = self.log_likelihood_history[-1] if self.log_likelihood_history else None
        return {
            "model": "DINA",
            "concept_ids": self.concept_ids,
            "question_ids": self.question_ids,
            "item_params": self.get_item_params(),
            "slip": {
                question_id: params["slip"]
                for question_id, params in self.get_item_params().items()
            },
            "guess": {
                question_id: params["guess"]
                for question_id, params in self.get_item_params().items()
            },
            "training": {
                "max_iter": self.max_iter,
                "n_iter": self.n_iter,
                "converged": self.converged,
                "log_likelihood": round(float(final_ll), 6) if final_ll is not None else None,
                "log_likelihood_history": [round(value, 6) for value in self.log_likelihood_history],
            },
        }

    def save_outputs(self, mastery_path: Path, params_path: Path) -> None:
        mastery_path.parent.mkdir(parents=True, exist_ok=True)
        params_path.parent.mkdir(parents=True, exist_ok=True)
        mastery_path.write_text(
            json.dumps(self.to_mastery_payload(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        params_path.write_text(
            json.dumps(self.to_params_payload(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _prepare_metadata(self, responses: pd.DataFrame, q_matrix: pd.DataFrame) -> None:
        required_response_columns = {"student_id", "question_id", "is_correct"}
        missing = required_response_columns - set(responses.columns)
        if missing:
            raise ValueError(f"responses 缺少字段：{sorted(missing)}")
        if "question_id" not in q_matrix.columns:
            raise ValueError("q_matrix 缺少 question_id 列")

        self.concept_ids = [column for column in q_matrix.columns if column != "question_id"]
        self.question_ids = q_matrix["question_id"].astype(str).tolist()
        self.student_ids = sorted(responses["student_id"].dropna().astype(str).unique().tolist())
        if "student_name" in responses.columns:
            self.student_names = (
                responses[["student_id", "student_name"]]
                .dropna()
                .drop_duplicates(subset=["student_id"])
                .set_index("student_id")["student_name"]
                .astype(str)
                .to_dict()
            )
        else:
            self.student_names = {}

    def _build_response_matrix(self, responses: pd.DataFrame) -> np.ndarray:
        student_index = {student_id: index for index, student_id in enumerate(self.student_ids)}
        question_index = {question_id: index for index, question_id in enumerate(self.question_ids)}
        matrix = np.full((len(self.student_ids), len(self.question_ids)), np.nan)

        for _, row in responses.iterrows():
            student_id = str(row["student_id"])
            question_id = str(row["question_id"])
            if student_id not in student_index or question_id not in question_index:
                continue
            matrix[student_index[student_id], question_index[question_id]] = int(row["is_correct"])

        return matrix

    def _e_step(self, response_matrix: np.ndarray) -> tuple[np.ndarray, float]:
        assert self.prior is not None
        assert self.slip is not None
        assert self.guess is not None
        assert self.eta is not None

        correct_prob = self.eta * (1.0 - self.slip) + (1.0 - self.eta) * self.guess
        correct_prob = np.clip(correct_prob, 1e-9, 1.0 - 1e-9)

        log_prior = np.log(np.clip(self.prior, 1e-12, 1.0))
        log_likelihood_by_pattern = np.tile(log_prior, (len(self.student_ids), 1))

        for student_index in range(response_matrix.shape[0]):
            observed_mask = ~np.isnan(response_matrix[student_index])
            if not observed_mask.any():
                continue
            observed = response_matrix[student_index, observed_mask]
            prob = correct_prob[:, observed_mask]
            log_likelihood_by_pattern[student_index] += (
                observed * np.log(prob) + (1.0 - observed) * np.log(1.0 - prob)
            ).sum(axis=1)

        log_norm = self._logsumexp(log_likelihood_by_pattern, axis=1)
        posterior = np.exp(log_likelihood_by_pattern - log_norm[:, None])
        return posterior, float(log_norm.sum())

    def _m_step(self, response_matrix: np.ndarray, posterior: np.ndarray) -> None:
        assert self.eta is not None

        self.prior = posterior.mean(axis=0)
        slip_values = []
        guess_values = []

        for item_index in range(response_matrix.shape[1]):
            observed_mask = ~np.isnan(response_matrix[:, item_index])
            if not observed_mask.any():
                slip_values.append(0.2)
                guess_values.append(0.2)
                continue

            observed = response_matrix[observed_mask, item_index]
            weights = posterior[observed_mask]
            eta_item = self.eta[:, item_index]

            mastered_weight = weights * eta_item
            non_mastered_weight = weights * (1.0 - eta_item)

            slip_denominator = mastered_weight.sum()
            guess_denominator = non_mastered_weight.sum()
            slip = (mastered_weight * (1.0 - observed[:, None])).sum() / slip_denominator if slip_denominator else 0.2
            guess = (non_mastered_weight * observed[:, None]).sum() / guess_denominator if guess_denominator else 0.2

            slip_values.append(float(np.clip(slip, self.min_param, self.max_param)))
            guess_values.append(float(np.clip(guess, self.min_param, self.max_param)))

        self.slip = np.asarray(slip_values)
        self.guess = np.asarray(guess_values)

    @staticmethod
    def _build_patterns(concept_count: int) -> np.ndarray:
        return np.asarray(list(itertools.product([0, 1], repeat=concept_count)), dtype=int)

    @staticmethod
    def _build_eta(patterns: np.ndarray, q_values: np.ndarray) -> np.ndarray:
        eta = np.ones((patterns.shape[0], q_values.shape[0]), dtype=float)
        for item_index, q_row in enumerate(q_values):
            required = q_row == 1
            if required.any():
                eta[:, item_index] = (patterns[:, required] == 1).all(axis=1).astype(float)
        return eta

    @staticmethod
    def _logsumexp(values: np.ndarray, axis: int) -> np.ndarray:
        max_values = np.max(values, axis=axis, keepdims=True)
        stable = max_values + np.log(np.exp(values - max_values).sum(axis=axis, keepdims=True))
        return np.squeeze(stable, axis=axis)

    def _ensure_fitted(self) -> None:
        if self.posterior is None or self.slip is None or self.guess is None:
            raise RuntimeError("DINA 模型尚未训练，请先调用 fit()")
