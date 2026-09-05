from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from world_cafe.llm import CafeLLM
from world_cafe.skills import all_skill_briefs, load_persona, SKILL_DISPLAY_NAMES


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

    # Step 1: Route to expert skill
    expert_skill = await _route_expert_skill(llm, user_request, background_context)
    persona_content = load_persona(expert_skill)

    # Step 2: Generate table questions using the selected skill's persona
    system = (
        "你是世界咖啡流程中的 facilitator agent。用户输入的是一个【设计问题】。\n"
        "你的职责：用所选设计专家 skill 的视角，从不同维度拆解用户的设计问题，为每张小桌生成一个【设计子问题】。\n\n"
    )
    if persona_content:
        display = SKILL_DISPLAY_NAMES.get(expert_skill, expert_skill)
        system += (
            f"你当前使用的专家视角是：{display}（{expert_skill}）。\n"
            f"以下是该专家的完整人格与知识：\n\n{persona_content}\n\n"
            "请用此专家的视角、思维方式和关注领域来拆解用户的设计问题。\n\n"
        )
    system += (
        "设计问题生成标准——每个问句必须同时满足：\n"
        "- 是设计问题（关注用户体验、利益相关者关系、系统机制、行为动机等，而非技术实现或管理流程）\n"
        "- 开放式（不能用是/否回答）\n"
        "- 具有生成性（能引发新观察，而非确认已知结论）\n"
        "- 不带诱导性（不暗示特定答案方向）\n"
        "- 能 travel well（适合跨桌迁移和交叉授粉）\n"
        "- 不按功能模块机械拆分\n"
        "- 不过早提出解决方案\n"
        "- 不要在问题中叙述或引用背景材料的具体内容、场景或例子\n\n"
        "质量校准透镜（检查问题组合的互补性）：\n"
        "用户旅程 / 利益相关者张力 / 根因机制 / 边缘案例 / 未来场景 / 问题重构\n\n"
        "每张桌只能有一个问句；问句必须简短、开放、中立、可迁移，严禁带解释、细节、引导语或解决方案。"
        "最终 tables 数量必须严格等于 table_count；只输出 JSON，不要输出 Markdown。"
        "一定要是设计问题（要模仿设计领域提问的范式），不能是其他领域（如治理、管理、政治）的问题。"
    )
    examples = ",\n".join(
        (
            f'    {{"table_id": "table_{index:02d}", '
            '"dimension": "该桌探索的设计维度", '
            '"question": "一个简短设计问句？"}}'
        )
        for index in range(1, table_count + 1)
    )
    user = (
        "用户的设计问题（最高优先级，所有子问题必须围绕此展开）：\n"
        f"{user_request}\n\n"
        f"{_format_background(background_context, background_filename)}"
        f"本次必须生成 table_count={table_count} 张小桌设计问题，tables 数组长度必须等于 {table_count}。\n\n"
        "流程：\n"
        f"1. 你已经被分配使用 {expert_skill} 专家的视角。\n"
        "2. 用该专家 skill 的视角，从不同设计维度拆解用户问题，每桌一个维度、一个设计子问题。\n"
        "3. 用透镜框架检查问题组合是否覆盖不同维度、互补且可迁移。检查是否是设计问题，是否符合设计领域提问的范式。\n\n"
        "每个 question 必须是一个设计问题（关注体验、关系、动机、机制，而非技术方案），建议 8-15个汉字。\n"
        "每个 question 必须只有一个问句，不要包含冒号、解释、分点、背景信息或引导语。\n"
        "每个 question 之间要有较大的差距，要引发不同（异质）维度的设计思考。\n"
        "请严格输出如下 JSON 结构：\n"
        "{\n"
        f'  "expert_skill": "{expert_skill}",\n'
        f'  "expert_rationale": "为何选择此设计专家视角（一句话）",\n'
        '  "tables": [\n'
        f"{examples}\n"
        "  ]\n"
        "}"
    )
    content = await llm.agenerate(system, user)
    result = _parse_facilitation(content, table_count=table_count, parent_question=user_request)
    # Ensure the routed skill is reflected in the result
    for table in result["tables"]:
        table["expert_skill"] = expert_skill
    return result


async def _route_expert_skill(llm: CafeLLM, user_request: str, background_context: str) -> str:
    """Use LLM to select the most appropriate expert skill for this design question."""
    briefs = all_skill_briefs()
    system = (
        "你是一个 expert-skill 路由器。根据用户的设计问题，从以下专家中选择一位最匹配的：\n"
        f"{briefs}\n\n"
        "只输出专家的 key（louyongqi / wangmeng / wangshouzhi / liulong 之一），不要输出其他任何内容。"
    )
    user = f"用户的设计问题：{user_request}"
    if background_context:
        user += f"\n\n背景材料摘要（前500字）：{background_context[:500]}"
    raw = await llm.agenerate(system, user)
    # Parse the response - should be just the key
    result = raw.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
    for key in ("louyongqi", "wangmeng", "wangshouzhi", "liulong"):
        if key in result:
            return key
    # Fallback: default to louyongqi
    return "louyongqi"


def _format_background(background_context: str, background_filename: str = "") -> str:
    context = background_context.strip()
    if not context:
        return ""
    title = f"Background material ({background_filename})" if background_filename else "Background material"
    max_chars = 4000
    if len(context) > max_chars:
        context = f"{context[:max_chars]}\n\n[Background material is too long and has been truncated to the first {max_chars} characters.]"
    return f"{title}:\n{context}\n\n"


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
            "expert_skill": str(data.get("expert_skill") or item.get("expert_skill") or "mixed"),
            "expert_rationale": str(data.get("expert_rationale") or item.get("expert_rationale") or "未提供专家路由理由。"),
            "lens": str(item.get("dimension") or item.get("lens") or "reframing"),
            "why_this_matters": str(item.get("why_this_matters") or ""),
            "evidence_basis": _string_list(item.get("evidence_basis")),
            "avoid_solution_bias": str(item.get("avoid_solution_bias") or "Avoid proposing solutions directly; explore problem conditions first."),
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
        "facilitation_note": str(data.get("facilitation_note") or "Small-table questions generated."),
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
        "round_1": _string_list(value.get("round_1")) or ["What real situations should this table observe first?"],
        "round_2": _string_list(value.get("round_2")) or ["What connections, disagreements, or tensions emerged from the previous round?"],
        "round_3": _string_list(value.get("round_3")) or ["Do these tensions suggest the original problem should be reframed?"],
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
        question += "?"
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
