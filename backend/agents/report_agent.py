from __future__ import annotations

import json
from typing import Any, Dict, List

from agents.qwen_client import QwenClient


REPORT_FIELDS = {
    "overall_diagnosis",
    "mastery_summary",
    "weak_concepts",
    "typical_error_analysis",
    "personalized_suggestions",
    "practice_path",
}


def generate_report(
    qwen_client: QwenClient,
    student_id: str,
    mastery: Dict[str, float],
    error_analyses: List[Dict[str, Any]],
    overall_performance: Dict[str, Any],
    knowledge_base: Dict[str, Any] | None = None,
    student_name: str | None = None,
    memory_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    knowledge_base = knowledge_base or {}
    memory_context = memory_context or {"has_history": False, "recent_diagnoses": [], "persistent_weak_concepts": []}
    prompt_payload = {
        "student_id": student_id,
        "student_name": student_name,
        "cdm_mastery": _build_mastery_summary(mastery, knowledge_base),
        "error_analyses": error_analyses,
        "overall_performance": overall_performance,
        "memory_context": memory_context,
    }
    prompt = f"""
请作为智慧教育认知诊断报告智能体，基于 CDM/DINA 掌握度和 CoT 错因解释生成结构化学情报告。
memory_context 是学生最近诊断摘要，只能用于描述诊断趋势和持续薄弱知识点。
不要编造日期、教材版本、课堂表现、长期能力或教师观察。
只输出合法 JSON，不要输出 Markdown。

输入：
{json.dumps(prompt_payload, ensure_ascii=False)}

JSON 必须包含以下字段：
- overall_diagnosis: 总体诊断结论
- mastery_summary: 数组，每项包含 concept_id, concept_name, mastery, level
- weak_concepts: 数组，每项包含 concept_id, concept_name, mastery, reason
- typical_error_analysis: 数组，每项包含 question_id, error_type, error_reason, cognitive_breakpoint
- personalized_suggestions: 字符串数组
- practice_path: 字符串数组
""".strip()

    raw = qwen_client.chat(
        [
            {"role": "system", "content": "你是只依据 CDM 和错因证据生成学情报告的教育智能体。"},
            {"role": "user", "content": prompt},
        ],
        task_type="report",
    )
    report = _safe_parse_report(
        raw,
        student_id,
        mastery,
        error_analyses,
        overall_performance,
        knowledge_base,
        memory_context,
    )
    report["student_id"] = student_id
    report["student_name"] = student_name or student_id
    report["overall_performance"] = overall_performance
    report["memory_context"] = memory_context
    report["report_text"] = _format_report_text(report)
    return report


def _safe_parse_report(
    raw: str,
    student_id: str,
    mastery: Dict[str, float],
    error_analyses: List[Dict[str, Any]],
    overall_performance: Dict[str, Any],
    knowledge_base: Dict[str, Any],
    memory_context: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        data = json.loads(_extract_json_text(raw))
    except json.JSONDecodeError:
        data = {}

    if not REPORT_FIELDS.issubset(set(data.keys())):
        data = _build_local_report(
            student_id,
            mastery,
            error_analyses,
            overall_performance,
            knowledge_base,
            memory_context,
        )

    data["mastery_summary"] = _normalize_mastery_summary(data.get("mastery_summary"), mastery, knowledge_base)
    data["weak_concepts"] = _normalize_weak_concepts(data.get("weak_concepts"), mastery, knowledge_base)
    data["typical_error_analysis"] = _normalize_error_analysis(data.get("typical_error_analysis"), error_analyses)
    data["personalized_suggestions"] = _normalize_text_list(data.get("personalized_suggestions"))
    data["practice_path"] = _normalize_text_list(data.get("practice_path"))
    if not str(data.get("overall_diagnosis", "")).strip():
        data["overall_diagnosis"] = _build_overall_diagnosis(overall_performance, data["weak_concepts"])
    return data


def _build_local_report(
    student_id: str,
    mastery: Dict[str, float],
    error_analyses: List[Dict[str, Any]],
    overall_performance: Dict[str, Any],
    knowledge_base: Dict[str, Any],
    memory_context: Dict[str, Any],
) -> Dict[str, Any]:
    mastery_summary = _build_mastery_summary(mastery, knowledge_base)
    weak_concepts = [
        {
            "concept_id": item["concept_id"],
            "concept_name": item["concept_name"],
            "mastery": item["mastery"],
            "reason": "DINA 掌握概率低于 0.60，且与错题涉及知识点存在关联。",
        }
        for item in mastery_summary
        if item["mastery"] < 0.6
    ]
    if not weak_concepts and mastery_summary:
        weakest = min(mastery_summary, key=lambda item: item["mastery"])
        weak_concepts = [{**weakest, "reason": "相对其他知识点掌握度最低，建议保持跟踪。"}]

    memory_suggestions = _build_memory_suggestions(memory_context)
    return {
        "overall_diagnosis": _build_overall_diagnosis(overall_performance, weak_concepts),
        "mastery_summary": mastery_summary,
        "weak_concepts": weak_concepts,
        "typical_error_analysis": _normalize_error_analysis([], error_analyses),
        "personalized_suggestions": [
            "优先复盘 DINA 掌握度低于 0.60 的知识点。",
            "每道错题按题目条件、调用知识点、关键步骤、答案检验四步重写。",
            "完成同类基础题后再做变式题，避免直接跳到综合题。",
        ]
        + memory_suggestions,
        "practice_path": [
            "第一步：完成薄弱知识点的概念复述和基础例题。",
            "第二步：完成 3 到 5 道同类题，记录每一步依据。",
            "第三步：完成综合变式题，并隔天重做本次错题。",
        ],
    }


def _build_mastery_summary(mastery: Dict[str, float], knowledge_base: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "concept_id": concept_id,
            "concept_name": _concept_name(concept_id, knowledge_base),
            "mastery": round(float(score), 4),
            "level": _mastery_level(float(score)),
        }
        for concept_id, score in mastery.items()
    ]


def _normalize_mastery_summary(
    value: Any,
    mastery: Dict[str, float],
    knowledge_base: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not isinstance(value, list) or not value:
        return _build_mastery_summary(mastery, knowledge_base)

    normalized = []
    for item in value:
        if not isinstance(item, dict):
            continue
        concept_id = str(item.get("concept_id", "")).strip()
        if not concept_id:
            continue
        score = float(item.get("mastery", mastery.get(concept_id, 0.0)))
        normalized.append(
            {
                "concept_id": concept_id,
                "concept_name": str(item.get("concept_name") or _concept_name(concept_id, knowledge_base)),
                "mastery": round(score, 4),
                "level": str(item.get("level") or _mastery_level(score)),
            }
        )
    return normalized or _build_mastery_summary(mastery, knowledge_base)


def _normalize_weak_concepts(
    value: Any,
    mastery: Dict[str, float],
    knowledge_base: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if isinstance(value, list) and value:
        normalized = []
        for item in value:
            if isinstance(item, dict):
                concept_id = str(item.get("concept_id", "")).strip()
                if not concept_id:
                    continue
                score = float(item.get("mastery", mastery.get(concept_id, 0.0)))
                normalized.append(
                    {
                        "concept_id": concept_id,
                        "concept_name": str(item.get("concept_name") or _concept_name(concept_id, knowledge_base)),
                        "mastery": round(score, 4),
                        "reason": str(item.get("reason") or "该知识点掌握度偏低。"),
                    }
                )
        if normalized:
            return normalized

    return [
        {
            "concept_id": concept_id,
            "concept_name": _concept_name(concept_id, knowledge_base),
            "mastery": round(float(score), 4),
            "reason": "DINA 掌握概率低于 0.60。",
        }
        for concept_id, score in mastery.items()
        if float(score) < 0.6
    ]


def _normalize_error_analysis(value: Any, error_analyses: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    source = value if isinstance(value, list) and value else error_analyses
    normalized = []
    for item in source:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "question_id": str(item.get("question_id", "未知题目")),
                "error_type": str(item.get("error_type", "Unknown")),
                "error_reason": str(item.get("error_reason") or item.get("reason") or "暂无具体错因"),
                "cognitive_breakpoint": str(
                    item.get("cognitive_breakpoint") or item.get("thinking_breakpoint") or "暂无认知断点"
                ),
            }
        )
    return normalized


def _build_overall_diagnosis(overall_performance: Dict[str, Any], weak_concepts: List[Dict[str, Any]]) -> str:
    accuracy = float(overall_performance.get("accuracy", 0.0))
    weak_names = "、".join(item["concept_name"] for item in weak_concepts) or "暂无明显薄弱知识点"
    return f"本次诊断正确率为 {accuracy:.0%}，主要需要关注 {weak_names}。结论仅基于本次答题和 DINA 诊断结果。"


def _format_report_text(report: Dict[str, Any]) -> str:
    mastery_lines = "\n".join(
        f"- {item['concept_name']}：{item['mastery']:.2f}（{item['level']}）"
        for item in report["mastery_summary"]
    )
    weak_lines = "\n".join(
        f"- {item['concept_name']}：{item['mastery']:.2f}。{item['reason']}"
        for item in report["weak_concepts"]
    ) or "- 暂无明显薄弱知识点。"
    error_lines = "\n".join(
        f"- {item['question_id']}：{item['error_type']}。{item['error_reason']}认知断点：{item['cognitive_breakpoint']}"
        for item in report["typical_error_analysis"]
    ) or "- 暂无错题分析。"
    suggestion_lines = "\n".join(f"- {item}" for item in report["personalized_suggestions"])
    path_lines = "\n".join(f"- {item}" for item in report["practice_path"])
    memory_text = _format_memory_text(report.get("memory_context", {}))

    return f"""一、总体诊断结论
{report['overall_diagnosis']}

二、知识点掌握情况
{mastery_lines}

三、主要薄弱知识点
{weak_lines}

四、典型错因分析
{error_lines}

五、个性化学习建议
{suggestion_lines}

六、后续练习路径
{path_lines}
{memory_text}"""


def _build_memory_suggestions(memory_context: Dict[str, Any]) -> List[str]:
    persistent = memory_context.get("persistent_weak_concepts", [])
    if not persistent:
        return []
    names = "、".join(str(item.get("concept_name", item.get("concept_id"))) for item in persistent[:3])
    return [f"结合历史诊断，建议持续跟踪 {names}，避免同类薄弱点反复出现。"]


def _format_memory_text(memory_context: Dict[str, Any]) -> str:
    if not memory_context.get("has_history"):
        return ""
    recent_count = len(memory_context.get("recent_diagnoses", []))
    persistent = memory_context.get("persistent_weak_concepts", [])
    persistent_names = "、".join(
        str(item.get("concept_name", item.get("concept_id"))) for item in persistent[:3]
    )
    persistent_text = persistent_names if persistent_names else "暂无持续薄弱知识点"
    return f"""

七、历史诊断记忆
系统参考了最近 {recent_count} 次诊断摘要。持续关注项：{persistent_text}。"""


def _normalize_text_list(value: Any) -> List[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str) and value.strip():
        items = [item.strip() for item in value.replace("；", ";").split(";") if item.strip()]
    else:
        items = []
    return items or ["围绕薄弱知识点进行短题组训练，并复盘错题步骤。"]


def _concept_name(concept_id: str, knowledge_base: Dict[str, Any]) -> str:
    item = knowledge_base.get(concept_id, {})
    return str(item.get("concept_name") or item.get("knowledge_name") or concept_id)


def _mastery_level(score: float) -> str:
    if score >= 0.8:
        return "掌握较好"
    if score >= 0.6:
        return "基本掌握"
    if score >= 0.4:
        return "掌握不稳"
    return "明显薄弱"


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
