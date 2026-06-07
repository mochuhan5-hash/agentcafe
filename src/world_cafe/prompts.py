from __future__ import annotations

import json
from typing import Any

from world_cafe.state import AgentProfile, CarryOverPacket, TableMemory, TableSpec, UserNote


def format_agent(profile: AgentProfile) -> str:
    skills = "、".join(profile.get("skills", [])) or "未填写"
    return (
        f"{profile['name']} ({profile['id']})\n"
        f"- role: {profile.get('role', '')}\n"
        f"- skills: {skills}\n"
        f"- style: {profile.get('style', '')}"
    )


def format_memory(memory: TableMemory) -> str:
    insights = "\n".join(f"- {item}" for item in memory.get("key_insights", [])) or "- 暂无"
    questions = "\n".join(f"- {item}" for item in memory.get("open_questions", [])) or "- 暂无"
    tensions = "\n".join(f"- {item}" for item in memory.get("tensions", [])) or "- 暂无"
    stable_patterns = _format_items(memory.get("stable_patterns"))
    weak_patterns = _format_items(memory.get("incomplete_or_weak_patterns"))
    contested_points = _format_items(memory.get("contested_points"))
    blind_spots = _format_items(memory.get("blind_spots_or_ambiguities"))
    dynamic_memory = memory.get("host_generated_table_memory") or ""
    cumulative_evolution = memory.get("cumulative_pattern_evolution") or "暂无"
    recurring_patterns = _format_items(memory.get("recurring_patterns_across_rounds"))
    emerging_signals = _format_items(memory.get("emerging_or_fading_signals"))
    unresolved_over_time = _format_items(memory.get("unresolved_tensions_over_time"))
    pattern_delta = memory.get("round_pattern_delta") or "暂无"
    question_seeds = "\n".join(f"- {item}" for item in memory.get("next_round_question_seeds", [])) or "- 暂无"
    round_history = _format_round_history(memory)
    return (
        f"桌子问题：{memory['question']}\n"
        f"活记忆摘要：{memory.get('living_summary') or '暂无'}\n"
        f"关键洞察：\n{insights}\n"
        f"开放问题：\n{questions}\n"
        f"张力：\n{tensions}\n"
        f"已成形模式：\n{stable_patterns}\n"
        f"仍不完善或证据不足的模式：\n{weak_patterns}\n"
        f"冲突或违背直觉的观点：\n{contested_points}\n"
        f"空白、盲点或模糊处：\n{blind_spots}\n"
        f"动态桌长记忆：{_compact_json(dynamic_memory)}\n"
        f"累计模式演化：{cumulative_evolution}\n"
        f"跨轮重复模式：\n{recurring_patterns}\n"
        f"新出现或正在减弱的信号：\n{emerging_signals}\n"
        f"持续未解张力：\n{unresolved_over_time}\n"
        f"最新 round pattern delta：{pattern_delta}\n"
        f"已完成轮次历史：\n{round_history}\n"
        f"下一轮问题种子：\n{question_seeds}"
    )


def format_table_spec(table_spec: TableSpec | dict[str, Any]) -> str:
    if not table_spec:
        return "暂无。"
    return _compact_json(table_spec)


def parent_question_from_spec(question: str, table_spec: TableSpec | dict[str, Any] | None) -> str:
    if isinstance(table_spec, dict):
        parent = str(
            table_spec.get("parent_question")
            or table_spec.get("main_question")
            or table_spec.get("user_question")
            or ""
        ).strip()
        if parent:
            return parent
    return question


def format_packet(packet: CarryOverPacket | dict[str, Any] | None) -> str:
    if not packet:
        return "暂无。"
    return _compact_json(packet)


def format_background(background_context: str) -> str:
    context = background_context.strip()
    if not context:
        return "暂无。"
    max_chars = 12000
    if len(context) > max_chars:
        context = f"{context[:max_chars]}\n\n[背景材料过长，已截断到前 {max_chars} 字符。]"
    return context


def format_user_notes(notes: list[UserNote] | list[dict[str, Any]] | None) -> str:
    if not notes:
        return "No user-marked notes submitted for this table/round."
    lines: list[str] = []
    for index, note in enumerate(notes[:24], start=1):
        text = str(note.get("text") or "").strip()
        if not text:
            continue
        if len(text) > 500:
            text = f"{text[:500].rstrip()}..."
        speaker = note.get("speaker_name") or note.get("speakerName") or note.get("speaker_id") or "unknown speaker"
        speech_id = note.get("speech_id") or note.get("speechId") or ""
        lines.append(f"{index}. [{speaker}; speech={speech_id}] {text}")
    return "\n".join(lines) or "No usable user-marked notes submitted for this table/round."


def format_closing_context(memory_update: dict[str, Any]) -> str:
    lines: list[str] = []
    field_labels = [
        ("stable_patterns", "暂时成形的模式"),
        ("incomplete_or_weak_patterns", "仍不完善或证据不足的模式"),
        ("contested_points", "冲突或违背直觉的观点"),
        ("tensions", "未解决张力"),
        ("blind_spots_or_ambiguities", "空白、盲点或模糊处"),
        ("open_questions", "下一轮追问"),
        ("round_pattern_delta", "本轮相对累计历史的新变化"),
        ("next_round_question_seeds", "可带走的问题种子"),
    ]
    for key, label in field_labels:
        value = memory_update.get(key)
        if value in ("", None, [], {}):
            continue
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            if items:
                lines.append(f"{label}：")
                lines.extend(f"- {item}" for item in items[:5])
        elif isinstance(value, dict):
            text = _compact_json(value)
            if text and text != "暂无":
                lines.append(f"{label}：{text}")
        else:
            text = str(value).strip()
            if text:
                lines.append(f"{label}：{text}")
    return "\n".join(lines) or "本轮内在记忆没有提取到可见结束语线索。"


def contribution_prompt(
    *,
    table_id: str,
    question: str,
    round_index: int,
    agent: AgentProfile,
    table_agents: list[AgentProfile],
    memory: TableMemory,
    table_spec: TableSpec | dict[str, Any] | None = None,
    carry_over_packet: CarryOverPacket | dict[str, Any] | None = None,
    conversation: list[str],
    background_context: str,
    turn_index: int,
    cycle_index: int,
) -> tuple[str, str]:
    system = (
        "你是 World Cafe 轮换参与者。你的可见发言应当像真实小桌对话中的自然接话，不是结构化报告。"
        "table_spec、background_context、table_memory 和 carry_over_packet 只作为你的内在记忆和上下文参考，不能机械复述，也不要暴露 JSON、字段名、模板名或 pocket 结构。"
        "用户原始大问题和背景材料是上位任务边界，本桌问题是当前小桌切入点；不要只围绕小桌问题而忘记上位任务。"
        "你要综合所有上下文形成判断，但发言时优先回应当前对话，尤其接住上一位参与者刚刚说的话，再自然补充、追问或提出不同观察。"
        "不要重新概括 table question，也不要重复已经稳定的共识；如果讨论开始回到上一轮已经说清楚的内容，请转向差异、盲点、边缘案例、具体证据或可检验追问。"
        "每次发言尽量完成一种对话动作：补充异质场景、指出盲点/风险、对比上一桌个人洞见与本桌观点、提出具体追问，或识别一个尚未展开成方案的设计机会。"
        "不要按“上一桌/当前桌/新连接”等来源标签组织输出，除非当前对话本身确实需要非常简短地提及。"
        "不要主导新桌，不要复述上一桌完整内容，不要直接提出完整解决方案。"
        "如果发言中出现设计机会、机会假设或类似表达，请把相关词组或句子加粗。"
    )
    peers = "\n\n".join(format_agent(profile) for profile in table_agents)
    transcript = "\n\n".join(conversation) or "暂无。"
    user = (
        f"桌子：{table_id}\n"
        f"轮次：{round_index + 1}\n"
        f"本桌总发言序号：{turn_index + 1}\n"
        f"这是你本轮第几次发言：{cycle_index + 1}\n"
        f"用户原始大问题：{parent_question_from_spec(question, table_spec)}\n"
        f"本桌初始问题：{question}\n\n"
        f"本桌 table_spec：\n{format_table_spec(table_spec or {})}\n\n"
        f"背景材料：\n{format_background(background_context)}\n\n"
        f"你的画像：\n{format_agent(agent)}\n\n"
        f"本桌成员：\n{peers}\n\n"
        f"桌长记忆：\n{format_memory(memory)}\n\n"
        f"你的 carry_over_packet（agent-level migrant memory）：\n{format_packet(carry_over_packet)}\n\n"
        f"本轮到目前为止的对话：\n{transcript}\n\n"
        "现在轮到你发言。请像真实小桌参与者一样结合table_spec、background_context、table_memory 和 carry_over_packet(包含你从上一轮讨论产生的个人洞察) 自然回应，不要按字段、来源或小标题输出。"
        "如果前面已经有人发言，先回应最近一位发言者的意思，再把你的观察自然接进去；"
        "如果当前讨论已经重复上一轮的稳定 pattern，请不要再阐述同一观点，而是带入一个不同用户/场景/机制盲点/反例/追问。"
        "如果你使用了 carry_over_packet 或 table_memory，只让它影响你的判断，不要说明你正在使用它。"
        "请控制在200字以内。"
    )
    return system, user


def host_opening_prompt(
    *,
    question: str,
    parent_question: str,
    memory: TableMemory,
    background_context: str = "",
) -> tuple[str, str]:
    system = (
        "你是 World Cafe table host agent。"
        "你的任务是在每轮开始前提出中立、简短、开放的引导性子问题。"
        "如果 opening 中出现设计机会、机会假设或类似表达，请把相关词组或句子加粗。"
    )
    user = (
        f"用户原始大问题：{parent_question}\n"
        f"本桌问题：{question}\n\n"
        f"既有 table_memory（含所有已完成轮次摘要）：\n{format_memory(memory)}\n\n"
        f"background_context：\n{format_background(background_context)}\n\n"
        "请输出简短 Markdown，系统会只把 opening 展示给用户，question_seeds 只用于流程引导：\n"
        "## opening\n"
        "提出2-3个可直接开启讨论的简短开放问句，每个问题尽量一句话。\n\n"
        "## question_seeds\n"
        "查看本桌所有已完成轮次的 table_memory（如有），在本桌问题背景下，按照不同的 round 提出以下不同维度的引导性子问题：\n"
        "- Round 1 发散观察：基于 table_spec、source_context 和本桌 lens，引导参与者打开观察面。\n"
        "- Round 2 连接与张力：仍以 table_spec、source_context 和本桌 lens 为锚，结合 Round 1 的 table_memory，避开已稳定共识（已重复出现的主题），追问新的转变、挑战少数观点、利益相关者/机制张力等。\n"
        "- Round 3 问题重构：仍以 table_spec、source_context 和本桌 lens 为锚，结合前两轮 table_memory，追问原始问题是否要改写、哪个未解决张力可能变成设计机会、哪个假设最值得验证。\n"
        "注意：最后只提出2-3个可直接开启讨论的简短开放问句，每个问题尽量一句话。不添加太多背景、解释或引导信息；每轮的子问题之间要形成推进。"
    )
    return system, user


def host_synthesis_prompt(
    *,
    table_id: str,
    question: str,
    round_index: int,
    host: AgentProfile,
    memory: TableMemory,
    table_spec: TableSpec | dict[str, Any] | None = None,
    contributions: list[str],
    background_context: str = "",
    user_notes: list[UserNote] | list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    system = (
        "你是 World Cafe table host agent。你的任务是维护 table-level intrinsic memory。"
        "不要把讨论压缩成普通会议纪要；要动态保留已成形 pattern、仍不完善或证据不足的 pattern、少数但有启发的观点、内部冲突、未解决张力、累计模式演化、跨轮重复模式、变化信号、本轮相对累计历史的位置、低价值归档和下一轮 question seeds。"
        "使用 LLM-generated template 策略：固定外壳可以稳定，但内部记忆维度应根据用户原始大问题、本桌问题、source_context、所有已完成轮次的 table_memory/round history digest 和本轮讨论动态决定。"
        "你要观察 Round 1 到当前轮之间问题理解如何演化：哪些主题持续共振，哪些 pattern 仍不完善，哪些少数观点被放大或消失，哪些观点互相冲突，哪些张力反复未解决。"
        "这是内部记忆更新，不是用户可见发言。请优先输出严格 JSON，不要输出面向用户的 Markdown。"
    )
    system += (
        "\n\nMemory priority for this synthesis: user_marked_notes are the highest-priority evidence; "
        "existing table_memory and all prior round history are second; current conversation transcript is third; "
        "table_spec and source_context remain task/evidence anchors throughout. "
        "Use submitted notes to detect intentional design insights and design opportunities, but do not mechanically copy all notes into visible host remarks."
    )
    joined_contributions = "\n\n".join(contributions)
    formatted_user_notes = format_user_notes(user_notes)
    user = (
        f"桌子：{table_id}\n"
        f"轮次：{round_index + 1}\n"
        f"用户原始大问题：{parent_question_from_spec(question, table_spec or {})}\n"
        f"本桌初始问题：{question}\n\n"
        f"table_spec：\n{format_table_spec(table_spec or {})}\n\n"
        f"User-marked notes for this table/round (highest-priority evidence):\n{formatted_user_notes}\n\n"
        f"桌长画像：\n{format_agent(host)}\n\n"
        f"既有桌长记忆（含所有已完成轮次摘要）：\n{format_memory(memory)}\n\n"
        f"背景材料参考：\n{format_background(background_context)}\n\n"
        f"本轮发言：\n{joined_contributions}\n\n"
        "请输出 JSON：\n"
        "{\n"
        '  "synthesis": "80-160字综合摘要，说明本轮如何进入或改变本桌累计讨论",\n'
        '  "key_insights": ["..."],\n'
        '  "stable_patterns": ["本轮比较成形、证据相对充分的 pattern"],\n'
        '  "incomplete_or_weak_patterns": ["仍不完善、证据不足或表述模糊的 pattern"],\n'
        '  "contested_points": ["互相冲突、互相拉扯或违背直觉的观点"],\n'
        '  "open_questions": ["..."],\n'
        '  "tensions": ["..."],\n'
        '  "blind_spots_or_ambiguities": ["下一轮应补足的空白、盲点或模糊处"],\n'
        '  "source_context_anchor": ["本轮讨论用到的原文证据线索"],\n'
        '  "host_memory_update_instruction": "本轮应该如何更新桌长内在记忆",\n'
        '  "llm_generated_table_memory_template": {"template_name": "...", "fields": {}},\n'
        '  "host_generated_table_memory": {},\n'
        '  "cumulative_pattern_evolution": "从 Round 1 到当前轮，本桌问题理解如何演化",\n'
        '  "recurring_patterns_across_rounds": ["跨多个轮次重复出现或持续共振的模式"],\n'
        '  "emerging_or_fading_signals": ["本轮新出现、被放大、减弱或消失的少数信号"],\n'
        '  "unresolved_tensions_over_time": ["跨轮持续未解决或反复出现的张力"],\n'
        '  "round_pattern_delta": "本轮相对累计历史的新变化（兼容字段，不只是上一轮差异）",\n'
        '  "next_round_question_seeds": ["..."]\n'
        "}"
    )
    return system, user


def host_closing_prompt(
    *,
    table_id: str,
    question: str,
    round_index: int,
    host: AgentProfile,
    memory: TableMemory,
    table_spec: TableSpec | dict[str, Any] | None = None,
    memory_update: dict[str, Any],
    contributions: list[str],
    user_notes: list[UserNote] | list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    system = (
        "你是 World Cafe table host agent。现在你要输出本轮可见结束语，而不是内在记忆 JSON。"
        "结束语的任务不是完整总结，而是让参与者看见本轮的pattern：重复出现的主题（共识）、讨论的转变、少数但有启发的观点、未解决张力。"
        "只输出自然语言 Markdown，不要暴露字段名、JSON、模板名或内部记忆说明。"
        "用关键词式短句，300字以内，最多4行；不要写成长段落，不要复述每个人发言。"
    )
    user = (
        f"用户原始大问题：{parent_question_from_spec(question, table_spec or {})}\n"
        f"本桌问题：{question}\n\n"
        f"既有 table_memory：\n{format_memory(memory)}\n\n"
        f"用户标记笔记（优先参考）：\n{format_user_notes(user_notes)}\n\n"
        f"本轮发言摘录：\n{chr(10).join(contributions[:12])}\n\n"
        "请输出 300 字以内的本轮结束语。建议形式：\n"
        "- 共识：关键词/短句\n"
        "- 转变：关键词/短句\n"
        "- 隐藏观点：（对应少数但有启发的观点）关键词/短句\n"
        "- 张力：关键词/短句\n"
        "可以调整措辞，但重点必须是差异、缺口、冲突和未完成问题，不要做完整摘要。"
    )
    return system, user


def carry_over_packet_prompt(
    *,
    agent: AgentProfile,
    from_table: str,
    to_table: str,
    after_round: int,
    from_memory: TableMemory,
    to_question: str,
    agent_contributions: list[str],
) -> tuple[str, str]:
    system = (
        "你是这个 World Cafe speaking agent 的内部迁移记忆生成视角，正在为自己生成 carry_over_packet。"
        "你不是 table host，也不是 summarizer；packet 是你的 agent-level migrant memory，不是 table_memory 复制，也不是上一桌完整摘要。"
        "采用 LLM-generated template：固定路由外壳，内部记忆模板根据 agent 角色、上一桌讨论和下一桌任务动态生成。"
        "这是内部迁移记忆，不是可见发言。请输出可供系统路由和下轮上下文引用的 JSON。"
    )
    user = (
        f"agent：\n{format_agent(agent)}\n\n"
        f"from_table：{from_table}\n"
        f"to_table：{to_table}\n"
        f"after_round：{after_round + 1}\n\n"
        f"上一桌 table_memory（只作证据背景，不要复制成你的个人记忆）：\n{format_memory(from_memory)}\n\n"
        f"该 agent 本轮发言：\n{chr(10).join(agent_contributions) or '暂无'}\n\n"
        f"下一桌问题：{to_question}\n\n"
        "请输出 JSON：\n"
        "{\n"
        '  "memory_update_instruction": "...",\n'
        '  "llm_generated_memory_template": {"template_name": "...", "fields": {}},\n'
        '  "agent_generated_memory": {},\n'
        '  "bridge_intent": "一句自然语言：如何把上一桌个人洞见带到下一桌任务中测试"\n'
        "}"
    )
    return system, user


def global_harvest_prompt(table_memories: dict[str, TableMemory], round_summaries: list[dict]) -> tuple[str, str]:
    system = (
        "你负责 World Cafe 的全局 harvest。你不是 summary merger。"
        "你要做四件事：聚类、连接、张力识别、机会生成。"
        "必须显式区分 Pattern Channel（多桌重复出现的主题）与 Weak Signal Channel（只出现一次但高张力/高新颖/高启发的少数观点）。"
        "内部可以使用 JSON 组织分析，但给用户展示的 display_markdown 必须自然可读，不要暴露内部字段解释。"
        "如果展示内容中出现设计机会、机会假设或类似表达，请把相关词组或句子加粗。"
    )
    memories = []
    for table_id, memory in sorted(table_memories.items()):
        memories.append(f"## {table_id}\n{format_memory(memory)}")
    summaries = "\n".join(str(summary) for summary in round_summaries)
    user = (
        "以下是所有桌子的桌长记忆：\n\n"
        f"{'\n\n'.join(memories)}\n\n"
        "轮次摘要：\n"
        f"{summaries}\n\n"
        "请优先输出 JSON，并包含 500字以内、可直接给用户看的 display_markdown。display_markdown 建议包含：\n"
        "## Shared Patterns\n"
        "## Weak Signals\n"
        "## Cross-table Tensions\n"
        "## Reframed Questions\n"
        "## Next Experiments\n"
        "如果无法输出 JSON，则直接输出同样结构的自然 Markdown。"
    )
    return system, user

def _compact_json(value: Any) -> str:
    if value in ("", None, [], {}):
        return "暂无"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def _format_items(value: Any, limit: int = 8) -> str:
    if value in ("", None, [], {}):
        return "- 暂无"
    if isinstance(value, dict):
        items = [f"{key}: {item}" for key, item in value.items()]
    elif isinstance(value, list):
        items = [str(item) for item in value]
    else:
        items = [str(value)]
    items = [item.strip() for item in items if item and item.strip()]
    return "\n".join(f"- {item}" for item in items[:limit]) or "- 暂无"


def _format_round_history(memory: TableMemory, limit: int = 6) -> str:
    rounds = memory.get("rounds", [])
    if not rounds:
        return "- 暂无"
    lines: list[str] = []
    for item in rounds[-limit:]:
        round_no = int(item.get("round_index", 0)) + 1
        update = item.get("table_memory_update") or {}
        synthesis = update.get("synthesis") or item.get("synthesis") or ""
        evolution = update.get("cumulative_pattern_evolution") or ""
        delta = update.get("round_pattern_delta") or ""
        insights = _format_inline_list(item.get("key_insights"))
        tensions = _format_inline_list(item.get("tensions"))
        questions = _format_inline_list(item.get("open_questions"))
        stable = _format_inline_list(update.get("stable_patterns"))
        weak = _format_inline_list(update.get("incomplete_or_weak_patterns"))
        contested = _format_inline_list(update.get("contested_points"))
        blind = _format_inline_list(update.get("blind_spots_or_ambiguities"))
        parts = [f"Round {round_no}: {str(synthesis).strip() or '暂无摘要'}"]
        if evolution:
            parts.append(f"累计演化: {evolution}")
        if delta:
            parts.append(f"本轮位置/变化: {delta}")
        if insights:
            parts.append(f"洞察: {insights}")
        if tensions:
            parts.append(f"张力: {tensions}")
        if questions:
            parts.append(f"开放问题: {questions}")
        if stable:
            parts.append(f"成形: {stable}")
        if weak:
            parts.append(f"不完善: {weak}")
        if contested:
            parts.append(f"冲突: {contested}")
        if blind:
            parts.append(f"盲点: {blind}")
        lines.append("- " + " | ".join(parts))
    return "\n".join(lines)


def _format_inline_list(value: Any, limit: int = 3) -> str:
    if not isinstance(value, list):
        return ""
    items = [str(item).strip() for item in value[:limit] if str(item).strip()]
    return "；".join(items)
