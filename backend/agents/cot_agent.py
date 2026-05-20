from __future__ import annotations

import json
from typing import Any, Dict, List

from agents.qwen_client import QwenClient


ERROR_TYPES = {
    "ConceptError",
    "FormulaError",
    "CalculationError",
    "StepJumpError",
    "TransferError",
    "CarelessError",
}


DIFFICULTY_COT_POLICIES = {
    "easy": {
        "label": "基础题精简链",
        "target_steps": 2,
        "focus": "用最短链路确认低掌握知识点和答案差异，避免简单题解释过长。",
    },
    "medium": {
        "label": "中等题标准链",
        "target_steps": 4,
        "focus": "依次检查掌握度、Q 矩阵知识点、作答差异和认知断点。",
    },
    "hard": {
        "label": "复杂题精细链",
        "target_steps": 6,
        "focus": "拆解条件、知识关联、关键步骤、迁移障碍、认知断点和干预建议。",
    },
}

DEFAULT_COT_POLICY = DIFFICULTY_COT_POLICIES["medium"]


def analyze_diagnosis(qwen_client: QwenClient, diagnosis_input: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a student diagnosis payload with CDM evidence as constraints."""
    explanations = []
    for wrong_question in diagnosis_input.get("wrong_questions", []):
        explanations.append(
            analyze_wrong_answer(
                qwen_client=qwen_client,
                wrong_question=wrong_question,
                student_answer=str(wrong_question.get("student_answer", "")),
                mastery=diagnosis_input.get("mastery", {}),
                knowledge_base=diagnosis_input.get("knowledge_base", {}),
                student_id=diagnosis_input.get("student_id"),
                student_name=diagnosis_input.get("student_name"),
            )
        )

    weak_concepts = _rank_weak_concepts(
        mastery=diagnosis_input.get("mastery", {}),
        concept_ids=list(diagnosis_input.get("mastery", {}).keys()),
    )
    return {
        "student_id": diagnosis_input.get("student_id"),
        "student_name": diagnosis_input.get("student_name"),
        "weak_concepts": weak_concepts,
        "question_explanations": explanations,
    }


def analyze_wrong_answer(
    qwen_client: QwenClient,
    wrong_question: Dict[str, Any],
    student_answer: str,
    mastery: Dict[str, float],
    knowledge_base: Dict[str, Any],
    student_id: str | None = None,
    student_name: str | None = None,
) -> Dict[str, Any]:
    concept_ids = _get_question_concepts(wrong_question)
    difficulty = _normalize_difficulty(wrong_question.get("difficulty"))
    cot_policy = _difficulty_policy(difficulty)
    prompt_payload = {
        "student_id": student_id,
        "student_name": student_name,
        "mastery": {concept_id: mastery.get(concept_id, 0.0) for concept_id in concept_ids},
        "cot_strategy": cot_policy,
        "wrong_question": {
            "question_id": wrong_question.get("question_id"),
            "content": wrong_question.get("content"),
            "student_answer": student_answer,
            "correct_answer": wrong_question.get("correct_answer"),
            "difficulty": difficulty,
            "q_matrix_concepts": _build_concept_payload(concept_ids, mastery, knowledge_base),
            "error_type": wrong_question.get("error_type"),
        },
    }
    prompt = f"""
你是面向智慧教育认知诊断的 CoT 可解释智能体。
请严格基于以下 CDM/DINA 诊断结果和错题信息分析，不要编造课堂表现、教材进度或长期能力。
只输出合法 JSON，不要输出 Markdown。

输入：
{json.dumps(prompt_payload, ensure_ascii=False)}

JSON 字段必须包含：
- weak_concepts: 字符串数组，使用 concept_id
- cot_strategy: 对象，包含 difficulty、label、target_steps、focus
- reasoning_steps: 字符串数组，说明从 CDM 掌握度到错因判断的推理链；必须严格匹配 cot_strategy.target_steps 的步数
- error_type: ConceptError / FormulaError / CalculationError / StepJumpError / TransferError / CarelessError
- error_reason: 具体错因
- cognitive_breakpoint: 认知断点
- learning_suggestion: 字符串数组，可执行建议
- confidence: 0 到 1 的数字

动态 CoT 规则：
- easy: 输出 2 步精简链，只解释核心知识点和答案差异。
- medium: 输出 4 步标准链，覆盖掌握度、Q 矩阵、作答差异、认知断点。
- hard: 输出 6 步精细链，覆盖条件拆解、知识关联、关键步骤、迁移障碍、认知断点、干预建议。
""".strip()

    raw = qwen_client.chat(
        [
            {"role": "system", "content": "你是只基于结构化 CDM 证据进行错因解释的教育智能体。"},
            {"role": "user", "content": prompt},
        ],
        task_type="cot",
    )
    parsed = _safe_parse_cot(raw, concept_ids, mastery, student_answer, difficulty, cot_policy)
    return _with_compatibility_aliases(parsed, wrong_question, mastery, knowledge_base)


def _safe_parse_cot(
    raw: str,
    concept_ids: List[str],
    mastery: Dict[str, float],
    student_answer: str,
    difficulty: str,
    cot_policy: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        data = json.loads(_extract_json_text(raw))
    except json.JSONDecodeError:
        data = _local_cot_fallback(concept_ids, mastery, student_answer, difficulty, cot_policy)

    weak_concepts = data.get("weak_concepts") or []
    if not isinstance(weak_concepts, list):
        weak_concepts = [str(weak_concepts)]
    weak_concepts = [str(item).strip() for item in weak_concepts if str(item).strip()]
    if not weak_concepts:
        weak_concepts = _rank_weak_concepts(mastery, concept_ids)

    reasoning_steps = data.get("reasoning_steps") or []
    if isinstance(reasoning_steps, str):
        reasoning_steps = [reasoning_steps]
    reasoning_steps = _normalize_reasoning_steps(
        reasoning_steps=reasoning_steps,
        difficulty=difficulty,
        cot_policy=cot_policy,
        weak_concepts=weak_concepts,
    )

    error_type = data.get("error_type")
    if error_type not in ERROR_TYPES:
        error_type = _infer_error_type(student_answer, weak_concepts, mastery)

    result = {
        "weak_concepts": weak_concepts,
        "cot_strategy": {
            "difficulty": difficulty,
            "label": cot_policy["label"],
            "target_steps": cot_policy["target_steps"],
            "focus": cot_policy["focus"],
        },
        "reasoning_steps": [str(step).strip() for step in reasoning_steps if str(step).strip()],
        "error_type": error_type,
        "error_reason": str(data.get("error_reason") or data.get("reason") or "错因需要结合本题步骤继续复盘。").strip(),
        "cognitive_breakpoint": str(
            data.get("cognitive_breakpoint")
            or data.get("thinking_breakpoint")
            or "题目条件、知识点和解题步骤之间的连接不够稳定。"
        ).strip(),
        "learning_suggestion": _normalize_suggestions(data.get("learning_suggestion") or data.get("suggestion")),
        "confidence": _normalize_confidence(data.get("confidence", 0.6)),
    }
    return result


def _local_cot_fallback(
    concept_ids: List[str],
    mastery: Dict[str, float],
    student_answer: str,
    difficulty: str = "medium",
    cot_policy: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    policy = cot_policy or _difficulty_policy(difficulty)
    weak_concepts = _rank_weak_concepts(mastery, concept_ids)
    error_type = _infer_error_type(student_answer, weak_concepts, mastery)
    return {
        "weak_concepts": weak_concepts,
        "cot_strategy": {
            "difficulty": difficulty,
            "label": policy["label"],
            "target_steps": policy["target_steps"],
            "focus": policy["focus"],
        },
        "reasoning_steps": _default_reasoning_steps(difficulty, weak_concepts)[: policy["target_steps"]],
        "error_type": error_type,
        "error_reason": "学生在本题涉及知识点上的掌握不够稳定，导致关键步骤或结果判断出错。",
        "cognitive_breakpoint": "不能稳定识别题目需要调用的知识点，或不能把知识点转化为完整解题步骤。",
        "learning_suggestion": [
            "先复述题目条件和目标。",
            "标出本题对应知识点并写出公式、性质或定理。",
            "完成 2 到 3 道同类基础题后再做变式题。",
        ],
        "confidence": 0.68,
    }


def _with_compatibility_aliases(
    data: Dict[str, Any],
    wrong_question: Dict[str, Any],
    mastery: Dict[str, float],
    knowledge_base: Dict[str, Any],
) -> Dict[str, Any]:
    weak_names = [_concept_name(concept_id, knowledge_base) for concept_id in data["weak_concepts"]]
    suggestion = data["learning_suggestion"]
    result = {
        **data,
        "question_id": wrong_question.get("question_id"),
        "difficulty": _normalize_difficulty(wrong_question.get("difficulty")),
        "concepts": _build_concept_payload(data["weak_concepts"], mastery, knowledge_base),
        "weak_concept_names": weak_names,
        # Compatibility fields used by the current frontend and old report code.
        "weak_knowledge": weak_names or data["weak_concepts"],
        "reason": data["error_reason"],
        "thinking_breakpoint": data["cognitive_breakpoint"],
        "suggestion": suggestion,
    }
    return result


def _normalize_difficulty(value: Any) -> str:
    difficulty = str(value or "medium").strip().lower()
    return difficulty if difficulty in DIFFICULTY_COT_POLICIES else "medium"


def _difficulty_policy(difficulty: str) -> Dict[str, Any]:
    policy = DIFFICULTY_COT_POLICIES.get(difficulty, DEFAULT_COT_POLICY)
    return {
        "difficulty": difficulty if difficulty in DIFFICULTY_COT_POLICIES else "medium",
        "label": policy["label"],
        "target_steps": policy["target_steps"],
        "focus": policy["focus"],
    }


def _normalize_reasoning_steps(
    reasoning_steps: List[Any],
    difficulty: str,
    cot_policy: Dict[str, Any],
    weak_concepts: List[str],
) -> List[str]:
    cleaned = [str(step).strip() for step in reasoning_steps if str(step).strip()]
    target_steps = int(cot_policy["target_steps"])
    defaults = _default_reasoning_steps(difficulty, weak_concepts)

    if len(cleaned) != target_steps:
        cleaned = defaults

    return cleaned[:target_steps]


def _default_reasoning_steps(difficulty: str, weak_concepts: List[str]) -> List[str]:
    weak_text = ", ".join(weak_concepts) if weak_concepts else "暂无明显低掌握项"
    if difficulty == "easy":
        return [
            f"读取本题 Q 矩阵和 DINA 掌握度，定位低掌握知识点：{weak_text}。",
            "对比学生答案与标准答案，判断错误主要来自基础概念或基础计算环节。",
        ]
    if difficulty == "hard":
        return [
            "先拆解题目条件、目标和隐含约束，确定本题不是单一步骤判断。",
            f"将题目涉及知识点与 DINA 掌握度对齐，定位低掌握知识点：{weak_text}。",
            "检查学生答案中缺失或跳过的关键步骤，判断是否存在步骤跳跃或迁移失败。",
            "结合 Q 矩阵知识点之间的依赖关系，分析错误是否来自多个知识点的综合调用。",
            "把低掌握知识点和作答偏差映射为具体认知断点。",
            "给出从基础概念、同类题到综合变式题的分层补救路径。",
        ]
    return [
        "读取 DINA 掌握度，定位本题涉及知识点中的低掌握项。",
        f"结合 Q 矩阵确认本题主要考查的薄弱知识点：{weak_text}。",
        "对比学生答案与标准答案，判断错误发生在概念调用、公式选择或计算步骤。",
        "将低掌握知识点和作答差异映射为认知断点与学习建议。",
    ]


def _get_question_concepts(wrong_question: Dict[str, Any]) -> List[str]:
    concept_ids = wrong_question.get("concept_ids") or wrong_question.get("knowledge_points") or []
    return [str(concept_id).strip() for concept_id in concept_ids if str(concept_id).strip()]


def _build_concept_payload(
    concept_ids: List[str],
    mastery: Dict[str, float],
    knowledge_base: Dict[str, Any],
) -> List[Dict[str, Any]]:
    payload = []
    for concept_id in concept_ids:
        item = knowledge_base.get(concept_id, {})
        payload.append(
            {
                "concept_id": concept_id,
                "concept_name": _concept_name(concept_id, knowledge_base),
                "mastery": mastery.get(concept_id),
                "description": item.get("description", ""),
                "common_errors": item.get("common_errors", []),
            }
        )
    return payload


def _rank_weak_concepts(mastery: Dict[str, float], concept_ids: List[str]) -> List[str]:
    candidates = concept_ids or list(mastery.keys())
    if not candidates:
        return []
    ranked = sorted(candidates, key=lambda concept_id: float(mastery.get(concept_id, 0.0)))
    weak = [concept_id for concept_id in ranked if float(mastery.get(concept_id, 0.0)) < 0.6]
    return weak or ranked[:1]


def _infer_error_type(student_answer: str, weak_concepts: List[str], mastery: Dict[str, float]) -> str:
    answer = student_answer.strip()
    if answer in {"不会", "不知道", ""}:
        return "ConceptError"
    if any(float(mastery.get(concept_id, 0.0)) < 0.4 for concept_id in weak_concepts):
        return "ConceptError"
    if any(char.isdigit() for char in answer):
        return "CalculationError"
    return "StepJumpError"


def _concept_name(concept_id: str, knowledge_base: Dict[str, Any]) -> str:
    item = knowledge_base.get(concept_id, {})
    return str(item.get("concept_name") or item.get("knowledge_name") or concept_id)


def _normalize_suggestions(value: Any) -> List[str]:
    if isinstance(value, list):
        suggestions = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str) and value.strip():
        suggestions = [item.strip() for item in value.replace("；", ";").split(";") if item.strip()]
    else:
        suggestions = []

    return suggestions or [
        "回到本题涉及的低掌握知识点，先做基础概念复述。",
        "重写错题步骤，并在最后加入答案检验。",
    ]


def _normalize_confidence(value: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 2)
    except (TypeError, ValueError):
        return 0.6


def _extract_json_text(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text
