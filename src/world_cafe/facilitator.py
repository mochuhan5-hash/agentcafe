from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from world_cafe.llm import CafeLLM


class FacilitatedTable(TypedDict, total=False):
    table_id: str
    parent_question: str
    question: str
    expert_skill: str
    expert_rationale: str
    lens: str
    guiding_question: str
    why_this_matters: str
    evidence_basis: list[str]
    avoid_solution_bias: str
    round_subquestions: dict[str, list[str]]


class FacilitationResult(TypedDict, total=False):
    facilitation_note: str
    tables: list[FacilitatedTable]
    table_question_plan: dict[str, Any]
    table_specs: dict[str, dict[str, Any]]
    expert_skill_routes: dict[str, Any]


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
        "你是世界咖啡流程中的 facilitator agent。你的职责分两步：\n"
        "1. Expert-skill routing：根据用户问题和背景材料，判断哪些专家视角（如服务设计、行为心理、系统工程、利益相关者分析、政策制度等）最能提升讨论质量，为每张桌分配一个 expert_skill。\n"
        "2. 问题生成：基于专家视角生成每张小桌的讨论问句。\n\n"
        "问题生成标准——每个问句必须同时满足：\n"
        "- 有证据支撑（能从背景材料中找到对应现象或张力）\n"
        "- 开放式（不能用是/否回答）\n"
        "- 具有生成性（能引发新观察，而非确认已知结论）\n"
        "- 不带诱导性（不暗示特定答案方向）\n"
        "- 能 travel well（适合跨桌迁移和交叉授粉）\n"
        "- 不按功能模块机械拆分\n"
        "- 不过早提出解决方案\n\n"
        "质量校准透镜（用于检查问题组合的互补性，优先级低于 expert-skill routing）：\n"
        "用户旅程 / 利益相关者张力 / 根因机制 / 边缘案例 / 未来场景 / 问题重构\n\n"
        "每张桌只能有一个问句；问句必须简短、开放、中立、可迁移，不要带解释、细节、引导语或解决方案。"
        "最终 tables 数量必须严格等于 table_count；只输出 JSON，不要输出 Markdown。"
    )
    examples = ",\n".join(
        (
            f'    {{"table_id": "table_{index:02d}", '
            '"expert_skill": "专家视角名称", '
            '"expert_rationale": "为何选此专家视角（一句话）", '
            '"question": "一个简短问句？"}'
        )
        for index in range(1, table_count + 1)
    )
    user = (
        "用户请求：\n"
        f"{user_request}\n\n"
        f"{_format_background(background_context, background_filename)}"
        f"本次必须生成 table_count={table_count} 张小桌问句，tables 数组长度必须等于 {table_count}。\n\n"
        "流程：\n"
        "1. 先阅读用户问题和背景材料，识别最相关的专家视角（expert_skill），每桌分配一个不同的专家视角。\n"
        "2. 基于该专家视角生成问句，确保问句满足上述所有标准。\n"
        "3. 用透镜框架检查问句组合是否覆盖不同维度、互补且可迁移。\n\n"
        "每个 question 必须只有一个问句，建议 8-24 个汉字，不要包含冒号、解释、分点、背景信息或引导语。\n"
        "每个 question 之间要有较大的差距，要引发不同（异质）维度的设计思考。\n"
        "请严格输出如下 JSON 结构：\n"
        "{\n"
        '  "tables": [\n'
        f"{examples}\n"
        "  ]\n"
        "}"
    )
    content = await llm.agenerate(system, user)
    return _parse_facilitation(content, table_count=table_count, parent_question=user_request)


def _format_background(background_context: str, background_filename: str = "") -> str:
    context = background_context.strip()
    if not context:
        return ""
    title = f"背景材料（{background_filename}）" if background_filename else "背景材料"
    max_chars = 4000
    if len(context) > max_chars:
        context = f"{context[:max_chars]}\n\n[背景材料过长，已截断到前 {max_chars} 字符。]"
    return f"{title}：\n{context}\n\n"


def _parse_facilitation(
    content: str,
    table_count: int = 4,
    parent_question: str = "",
) -> FacilitationResult:
    data = _loads_jsonish(content)
    tables = data.get("tables", [])
    if not isinstance(tables, list):
        plan_tables = data.get("table_question_plan", {})
        if isinstance(plan_tables, dict):
            tables = plan_tables.get("tables", [])
    if isinstance(tables, dict):
        tables = list(tables.values())
    if not isinstance(tables, list) or len(tables) < table_count:
        actual_count = len(tables) if isinstance(tables, list) else 0
        raise ValueError(f"facilitator returned {actual_count} table questions; expected {table_count}")
    if len(tables) > table_count:
        tables = tables[:table_count]

    normalized: list[FacilitatedTable] = []
    for index, item in enumerate(tables, start=1):
        if not isinstance(item, dict):
            raise ValueError("each facilitated table must be an object")
        question = _single_question(str(item.get("question") or item.get("guiding_question") or ""))
        if not question:
            raise ValueError("facilitated table question cannot be empty")
        table_id = str(item.get("table_id") or f"table_{index:02d}")
        parent = str(
            item.get("parent_question")
            or item.get("main_question")
            or item.get("user_question")
            or parent_question
        )
        normalized_item: FacilitatedTable = {
            "table_id": table_id,
            "parent_question": parent,
            "question": question,
            "guiding_question": question,
            "expert_skill": str(item.get("expert_skill") or "mixed"),
            "expert_rationale": str(item.get("expert_rationale") or "未提供专家路由理由。"),
            "lens": str(item.get("lens") or "reframing"),
            "why_this_matters": str(item.get("why_this_matters") or ""),
            "evidence_basis": _string_list(item.get("evidence_basis")),
            "avoid_solution_bias": str(item.get("avoid_solution_bias") or "避免直接提出解决方案，优先讨论问题条件。"),
            "round_subquestions": _round_subquestions(item.get("round_subquestions")),
        }
        normalized.append(normalized_item)
    table_specs = {table["table_id"]: dict(table) for table in normalized}
    plan = data.get("table_question_plan")
    if not isinstance(plan, dict):
        plan = {
            "context_reading": {
                "user_needs": [],
                "pain_points": [],
                "design_tensions": [],
                "weak_signals": [],
                "reframe_directions": [],
            },
            "expert_skill_routes": {},
        }
    plan["tables"] = [dict(table) for table in normalized]
    return {
        "facilitation_note": str(data.get("facilitation_note") or "已生成小桌问句。"),
        "tables": normalized,
        "table_question_plan": plan,
        "table_specs": table_specs,
        "expert_skill_routes": plan.get("expert_skill_routes", {}) if isinstance(plan.get("expert_skill_routes"), dict) else {},
    }


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _round_subquestions(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        value = {}
    return {
        "round_1": _string_list(value.get("round_1")) or ["本桌问题中有哪些值得先观察的真实现象？"],
        "round_2": _string_list(value.get("round_2")) or ["上一轮观察之间出现了哪些连接、分歧或张力？"],
        "round_3": _string_list(value.get("round_3")) or ["这些张力是否提示我们需要重构原问题？"],
    }


def _single_question(value: str) -> str:
    text = " ".join(value.strip().split())
    text = re.sub(r"^[\-\*\d\.\s、:：]+", "", text)
    if not text:
        return ""
    match = re.search(r"[^？?。！!；;]*[？?]", text)
    if match:
        question = match.group(0).strip()
    else:
        question = re.split(r"[。！!；;]", text, maxsplit=1)[0].strip()
    question = question.rstrip("。！!；;，,、")
    if not question.endswith(("？", "?")):
        question += "？"
    return question


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
