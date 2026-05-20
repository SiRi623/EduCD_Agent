from __future__ import annotations

import json
import os
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


class QwenClient:
    """Single Qwen/DashScope client used by all agents.

    If DASHSCOPE_API_KEY is absent, the client returns deterministic structured
    mock results so the CDM pipeline can still be demonstrated offline.
    """

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("DASHSCOPE_MODEL", "qwen3.6-plus")
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.base_url = os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.mock_mode = not bool(self.api_key)
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None

    def status_text(self) -> str:
        return "mock 模式" if self.mock_mode else f"真实 Qwen API 模式，模型：{self.model}"

    def chat(self, messages: List[Dict[str, str]], task_type: str = "general") -> str:
        if self.mock_mode:
            return self._mock_response(task_type)

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            self.mock_mode = True
            print(f"[QwenClient] 真实调用失败，已切换到 mock 模式：{exc}")
            return self._mock_response(task_type)

    def _mock_response(self, task_type: str) -> str:
        if task_type == "cot":
            return json.dumps(
                {
                    "weak_concepts": [],
                    "reasoning_steps": [
                        "先根据 DINA 掌握度定位低掌握知识点。",
                        "再结合错题涉及的 Q 矩阵知识点判断认知断点。",
                        "最后给出可执行的补救建议。",
                    ],
                    "error_type": "ConceptError",
                    "error_reason": "学生在题目涉及的低掌握知识点上存在概念理解或步骤迁移不足。",
                    "cognitive_breakpoint": "没有把题目条件、所需知识点和解题步骤稳定连接起来。",
                    "learning_suggestion": [
                        "先复述题目条件和目标。",
                        "写出对应公式或定理。",
                        "完成同类基础题后再做变式题。",
                    ],
                    "confidence": 0.72,
                },
                ensure_ascii=False,
            )

        if task_type == "report":
            return json.dumps(
                {
                    "overall_diagnosis": "本次诊断显示学生存在部分知识点掌握不稳，需要围绕低掌握知识点进行针对性巩固。",
                    "mastery_summary": [],
                    "weak_concepts": [],
                    "typical_error_analysis": [],
                    "personalized_suggestions": [
                        "优先复盘低掌握知识点对应错题。",
                        "每道错题按条件、知识点、步骤、检验四步重写。",
                    ],
                    "practice_path": [
                        "完成基础概念题。",
                        "完成同类计算或证明题。",
                        "完成综合变式题并复盘。",
                    ],
                },
                ensure_ascii=False,
            )

        if task_type == "reflection":
            return json.dumps(
                {
                    "is_consistent_with_cdm": True,
                    "has_specific_error_reason": True,
                    "has_actionable_suggestion": True,
                    "has_vague_expression": False,
                    "issues": [],
                    "revision_suggestions": [],
                },
                ensure_ascii=False,
            )

        return "mock 模式下的通用回复"
