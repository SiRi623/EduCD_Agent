from __future__ import annotations

import json
from typing import Any, Dict, List

from agents.qwen_client import QwenClient


SELF_CHECK_FIELDS = {
    "is_consistent_with_cdm",
    "has_specific_error_reason",
    "has_actionable_suggestion",
    "has_vague_expression",
    "issues",
    "revision_suggestions",
}


def optimize_report(
    qwen_client: QwenClient,
    original_report: Dict[str, Any] | str,
    mastery: Dict[str, float],
    error_analyses: List[Dict[str, Any]],
) -> Dict[str, Any]:
    report = _ensure_report_dict(original_report)
    if qwen_client.mock_mode:
        self_check = _local_self_check(report, mastery, error_analyses)
        report["self_check"] = self_check
        report["reflection_summary"] = _format_reflection_summary(self_check)
        return report

    prompt_payload = {
        "cdm_mastery": mastery,
        "error_analyses": error_analyses,
        "report": report,
    }
    prompt = f"""
请对下面的结构化学情报告做自我检查。只输出合法 JSON，不要输出 Markdown。
检查标准：
1. 是否与 CDM 掌握度一致；
2. 是否指出具体错因；
3. 是否包含可执行建议；
4. 是否存在空泛表达或过度推断。

输入：
{json.dumps(prompt_payload, ensure_ascii=False)}

JSON 字段必须包含：
- is_consistent_with_cdm: boolean
- has_specific_error_reason: boolean
- has_actionable_suggestion: boolean
- has_vague_expression: boolean
- issues: 字符串数组
- revision_suggestions: 字符串数组
""".strip()

    raw = qwen_client.chat(
        [
            {"role": "system", "content": "你是负责检查教育诊断报告可信度和可执行性的反思智能体。"},
            {"role": "user", "content": prompt},
        ],
        task_type="reflection",
    )
    self_check = _safe_parse_self_check(raw, report, mastery, error_analyses)
    report["self_check"] = self_check
    report["reflection_summary"] = _format_reflection_summary(self_check)
    return report


def _safe_parse_self_check(
    raw: str,
    report: Dict[str, Any],
    mastery: Dict[str, float],
    error_analyses: List[Dict[str, Any]],
) -> Dict[str, Any]:
    try:
        data = json.loads(_extract_json_text(raw))
    except json.JSONDecodeError:
        data = {}

    if not SELF_CHECK_FIELDS.issubset(set(data.keys())):
        data = _local_self_check(report, mastery, error_analyses)

    return {
        "is_consistent_with_cdm": bool(data.get("is_consistent_with_cdm")),
        "has_specific_error_reason": bool(data.get("has_specific_error_reason")),
        "has_actionable_suggestion": bool(data.get("has_actionable_suggestion")),
        "has_vague_expression": bool(data.get("has_vague_expression")),
        "issues": _normalize_text_list(data.get("issues"), default=[]),
        "revision_suggestions": _normalize_text_list(data.get("revision_suggestions"), default=[]),
    }


def _local_self_check(
    report: Dict[str, Any],
    mastery: Dict[str, float],
    error_analyses: List[Dict[str, Any]],
) -> Dict[str, Any]:
    weak_from_cdm = {concept_id for concept_id, score in mastery.items() if float(score) < 0.6}
    weak_from_report = {
        str(item.get("concept_id"))
        for item in report.get("weak_concepts", [])
        if isinstance(item, dict) and item.get("concept_id")
    }
    report_text = str(report.get("report_text", ""))
    vague_terms = ["较差", "不认真", "能力不足", "长期", "一直", "课堂表现"]

    issues = []
    suggestions = []
    is_consistent = weak_from_cdm.issubset(weak_from_report) if weak_from_cdm else True
    if not is_consistent:
        issues.append("报告中的薄弱知识点没有完全覆盖 CDM 低掌握知识点。")
        suggestions.append("将 DINA 掌握度低于 0.60 的知识点明确列入薄弱项。")

    has_error_reason = any(
        item.get("error_reason") or item.get("reason")
        for item in error_analyses
        if isinstance(item, dict)
    )
    if error_analyses and not has_error_reason:
        issues.append("错因分析缺少具体原因。")
        suggestions.append("为每道错题补充与知识点和解题步骤相关的具体错因。")

    has_action = bool(report.get("personalized_suggestions")) and bool(report.get("practice_path"))
    if not has_action:
        issues.append("报告缺少可执行学习建议或后续练习路径。")
        suggestions.append("补充分步骤练习路径，例如基础题、同类题、变式题。")

    has_vague = any(term in report_text for term in vague_terms)
    if has_vague:
        issues.append("报告可能包含空泛或过度推断表达。")
        suggestions.append("删除无法由本次答题数据支持的判断。")

    return {
        "is_consistent_with_cdm": is_consistent,
        "has_specific_error_reason": (not error_analyses) or has_error_reason,
        "has_actionable_suggestion": has_action,
        "has_vague_expression": has_vague,
        "issues": issues,
        "revision_suggestions": suggestions,
    }


def _ensure_report_dict(report: Dict[str, Any] | str) -> Dict[str, Any]:
    if isinstance(report, dict):
        return dict(report)
    return {
        "overall_diagnosis": str(report),
        "mastery_summary": [],
        "weak_concepts": [],
        "typical_error_analysis": [],
        "personalized_suggestions": [],
        "practice_path": [],
        "report_text": str(report),
    }


def _format_reflection_summary(self_check: Dict[str, Any]) -> str:
    passed = [
        self_check["is_consistent_with_cdm"],
        self_check["has_specific_error_reason"],
        self_check["has_actionable_suggestion"],
        not self_check["has_vague_expression"],
    ]
    return f"Reflection 自检通过 {sum(passed)}/4 项。"


def _normalize_text_list(value: Any, default: List[str] | None = None) -> List[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str) and value.strip():
        items = [value.strip()]
    else:
        items = []
    return items if items else (default or [])


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
