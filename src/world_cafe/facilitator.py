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

    expert_skill = await _route_expert_skill(llm, user_request, background_context)
    persona_content = load_persona(expert_skill)

    system = (
        "You are the facilitator agent in a World Cafe workflow. The user input is a design question.\n"
        "Always write all generated questions and JSON string values in English, even when the user request, background material, or persona references are in another language.\n"
        "Your responsibility is to use the selected design expert skill as a lens and generate one initial discussion question for each small table, with different tables exploring different design dimensions.\n\n"
    )
    if persona_content:
        display = SKILL_DISPLAY_NAMES.get(expert_skill, expert_skill)
        system += (
            f"The selected expert lens is: {display} ({expert_skill}).\n"
            f"Use the following persona and knowledge as background reference only:\n\n{persona_content}\n\n"
            "Use this expert's perspective, thinking style, and domain concerns to break down the user's design question, but write the result in English.\n\n"
        )
    system += (
        "Every question must satisfy these criteria:\n"
        "- It is a design question about user experience, stakeholder relationships, system mechanisms, behavior, motivation, or meaning, not merely technical implementation or management process.\n"
        "- It is open-ended and cannot be answered with yes/no.\n"
        "- It is generative, able to trigger new observation instead of confirming known conclusions.\n"
        "- It is neutral and does not imply a preferred answer.\n"
        "- It travels well across table rotations and cross-pollination.\n"
        "- It does not mechanically split by feature module.\n"
        "- It does not propose a solution too early.\n"
        "- It does not quote or narrate specific examples from the background material.\n\n"
        "Use these calibration lenses to make the question set complementary: user journey, stakeholder tension, root mechanism, edge case, future scenario, and problem reframing.\n\n"
        "Each table must have exactly one brief, open, neutral, portable question. Do not include explanations, details, framing preambles, or solutions. "
        "The final number of tables must exactly equal table_count. Output JSON only, with no Markdown."
    )
    examples = ",\n".join(
        (
            f'    {{"table_id": "table_{index:02d}", '
            '"dimension": "the design dimension explored by this table", '
            '"question": "A brief open design question?"}}'
        )
        for index in range(1, table_count + 1)
    )
    user = (
        "User design question (highest priority; all sub-questions must stay grounded in it):\n"
        f"{user_request}\n\n"
        f"{_format_background(background_context, background_filename)}"
        f"Generate table_count={table_count} small-table design questions. The tables array length must be exactly {table_count}.\n\n"
        "Process:\n"
        f"1. You have been assigned the {expert_skill} expert lens.\n"
        "2. Use that expert skill to break the user question into distinct design dimensions, one table per dimension and one design sub-question per table.\n"
        "3. Check that the set covers meaningfully different dimensions, is complementary and portable, and follows design-question phrasing.\n\n"
        "Each question must contain one English design question only, ideally 5-14 words. Do not include colons, explanations, bullet points, background details, or preambles.\n"
        "Questions should be meaningfully different from one another and should trigger heterogeneous dimensions of design thinking.\n"
        "Strictly output this JSON structure:\n"
        "{\n"
        f'  "expert_skill": "{expert_skill}",\n'
        f'  "expert_rationale": "why this design expert lens was selected, in one sentence",\n'
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
        "You are an expert-skill router. Select the single best matching expert lens for the user's design question from the options below:\n"
        f"{briefs}\n\n"
        "Output only one key: louyongqi, wangmeng, wangshouzhi, or liulong. Do not output anything else."
    )
    user = f"User design question: {user_request}"
    if background_context:
        user += f"\n\nBackground summary (first 500 characters): {background_context[:500]}"
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
            "expert_rationale": str(data.get("expert_rationale") or item.get("expert_rationale") or "No expert-routing rationale was provided."),
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
