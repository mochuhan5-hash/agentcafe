from __future__ import annotations

import json
import re
from typing import TypedDict

from world_cafe.llm import CafeLLM


class FacilitatedTable(TypedDict):
    table_id: str
    question: str


class FacilitationResult(TypedDict):
    facilitation_note: str
    tables: list[FacilitatedTable]


async def facilitate_request(
    llm: CafeLLM,
    user_request: str,
    table_count: int = 4,
    background_context: str = "",
    background_filename: str = "",
) -> FacilitationResult:
    if table_count < 1:
        raise ValueError("table_count must be at least 1")
    system = (
        "你是世界咖啡流程中的 facilitator。"
        f"你的任务是把用户的一段请求拆成 {table_count} 个彼此互补、适合并行小桌讨论的初始问题。"
        "问题应当覆盖不同视角，避免重复；每个问题都应能引发开放讨论，而不是是/否判断。"
        "如果用户提供了背景材料，请优先基于材料中的事实、目标、约束和术语来拆题。"
        "只输出 JSON，不要输出 Markdown。"
    )
    examples = ",\n".join(
        f'    {{"table_id": "table_{index:02d}", "question": "..."}}'
        for index in range(1, table_count + 1)
    )
    user = (
        "用户请求：\n"
        f"{user_request}\n\n"
        f"{_format_background(background_context, background_filename)}"
        "请严格输出如下 JSON 结构：\n"
        "{\n"
        '  "facilitation_note": "一句话说明拆分逻辑",\n'
        '  "tables": [\n'
        f"{examples}\n"
        "  ]\n"
        "}"
    )
    content = await llm.agenerate(system, user)
    return _parse_facilitation(content, table_count=table_count)


def _format_background(background_context: str, background_filename: str = "") -> str:
    context = background_context.strip()
    if not context:
        return ""
    title = f"背景材料（{background_filename}）" if background_filename else "背景材料"
    max_chars = 16000
    if len(context) > max_chars:
        context = f"{context[:max_chars]}\n\n[背景材料过长，已截断到前 {max_chars} 字符。]"
    return f"{title}：\n{context}\n\n"


def _parse_facilitation(content: str, table_count: int = 4) -> FacilitationResult:
    data = _loads_jsonish(content)
    tables = data.get("tables", [])
    if not isinstance(tables, list) or len(tables) != table_count:
        raise ValueError(f"facilitator must return exactly {table_count} table questions")

    normalized: list[FacilitatedTable] = []
    for index, item in enumerate(tables, start=1):
        if not isinstance(item, dict):
            raise ValueError("each facilitated table must be an object")
        question = str(item.get("question", "")).strip()
        if not question:
            raise ValueError("facilitated table question cannot be empty")
        normalized.append(
            {
                "table_id": str(item.get("table_id") or f"table_{index:02d}"),
                "question": question,
            }
        )
    return {
        "facilitation_note": str(data.get("facilitation_note") or f"已拆分为 {table_count} 个小桌初始问题。"),
        "tables": normalized,
    }


def _loads_jsonish(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match is None:
            raise
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("facilitator response must be a JSON object")
    return data
