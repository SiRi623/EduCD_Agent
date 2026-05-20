from __future__ import annotations

import json
import sys

from tools.diagnosis_tool import DINA_PARAMS_PATH, MASTERY_RESULTS_PATH, train_and_save_dina


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    result = train_and_save_dina()
    params = result["dina_params"]
    mastery = result["mastery_results"]

    summary = {
        "model": "DINA",
        "student_count": len(mastery["students"]),
        "concept_count": len(mastery["concept_ids"]),
        "question_count": len(mastery["question_ids"]),
        "n_iter": params["training"]["n_iter"],
        "converged": params["training"]["converged"],
        "mastery_output": str(MASTERY_RESULTS_PATH),
        "params_output": str(DINA_PARAMS_PATH),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
