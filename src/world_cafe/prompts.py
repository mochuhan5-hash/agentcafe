from __future__ import annotations

from typing import Any

from world_cafe.context import (
    MemoryView,
    format_background,
    format_carry_over_packet,
    format_closing_context,
    format_table_memory,
    format_table_spec,
    format_user_notes,
    parent_question_from_spec,
)
from world_cafe.state import (
    TABLEMEMORY_USAGE_DESCRIPTION,
    AgentProfile,
    CarryOverPacket,
    TableMemory,
    TableRoundOutput,
    TableSpec,
    UserNote,
)


def format_agent(profile: AgentProfile) -> str:
    skills = ", ".join(profile.get("skills", [])) or "not specified"
    return (
        f"{profile['name']} ({profile['id']})\n"
        f"- role: {profile.get('role', '')}\n"
        f"- skills: {skills}\n"
        f"- style: {profile.get('style', '')}"
    )


def format_memory(memory: TableMemory, *, view: MemoryView = "host_synthesis") -> str:
    return format_table_memory(memory, view=view)


def format_packet(packet: CarryOverPacket | dict[str, Any] | None) -> str:
    return format_carry_over_packet(packet)


def format_speaking_agent_history(table_round_outputs: list[TableRoundOutput]) -> str:
    if not table_round_outputs:
        return "None yet."
    sections: list[str] = []
    outputs = sorted(
        table_round_outputs,
        key=lambda output: (output.get("round_index", 0), output.get("table_id", "")),
    )
    for output in outputs:
        header = (
            f"## Round {int(output.get('round_index', 0)) + 1} · {output.get('table_id', '')}\n"
            f"Table question: {output.get('question', '')}"
        )
        lines = [header]
        contributions = sorted(
            output.get("contributions", []),
            key=lambda item: item.get("turn_index", 0),
        )
        for contribution in contributions:
            agent_name = contribution.get("agent_name", "")
            agent_id = contribution.get("agent_id", "")
            turn_index = int(contribution.get("turn_index", 0)) + 1
            cycle_index = int(contribution.get("cycle_index", 0)) + 1
            content = str(contribution.get("content") or "").strip()
            lines.append(f"- Turn {turn_index} / cycle {cycle_index} · {agent_name} ({agent_id}): {content}")
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def format_user_note_history(table_round_outputs: list[TableRoundOutput]) -> str:
    if not table_round_outputs:
        return "None yet."
    sections: list[str] = []
    outputs = sorted(
        table_round_outputs,
        key=lambda output: (output.get("round_index", 0), output.get("table_id", "")),
    )
    for output in outputs:
        notes = output.get("user_notes") or []
        if not notes:
            continue
        header = (
            f"## Round {int(output.get('round_index', 0)) + 1} · {output.get('table_id', '')}\n"
            f"Table question: {output.get('question', '')}"
        )
        sections.append(f"{header}\n{format_user_notes(notes)}")
    return "\n\n".join(sections) or "None yet."


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
        "你是 World Cafe 轮换参与者，与多位参与者讨论设计问题和机会，你不要列举background_context里用户访谈的例子，清晰重述自己的经验、观点即可。你的可见发言应当像真实小桌对话中的自然接话，不是结构化报告。"
        "每次发言字数严格控制在100字以内，不需要列举背景材料的例子。"
        "table_spec、background_context（仅作参考，不要引用用户访谈具体内容,可以结合自己的经历）、table_memory 和 carry_over_packet （作为你的内在记忆和自我认知对你发言内容和观点的影响很大），不能机械复述，也不要暴露 JSON、字段名、模板名或 pocket 结构。"
        "用户原始大问题和背景材料是上位任务边界，本桌问题是当前小桌切入点；不要只围绕小桌问题而忘记上位任务。"
        "你要综合所有上下文形成判断，但发言时优先回应当前对话，尤其接住上一位参与者刚刚说的话，再自然补充、追问或提出不同观察。"
        "不要重新概括 table question，也不要重复已经稳定的共识；如果讨论开始回到上一轮已经说清楚的内容，请转向差异、盲点、边缘案例、具体证据或可检验追问。"
        "每次发言尽量完成一种对话动作：补充异质场景、指出盲点/风险、对比上一桌个人洞见与本桌观点、提出具体追问，或识别一个尚未展开成方案的设计机会。"
        "不要按“上一桌/当前桌/新连接”等来源标签组织输出，除非当前对话本身确实需要非常简短地提及。"
        "不要主导新桌，不要复述上一桌完整内容，不要直接提出完整解决方案。"
        "如果发言中出现设计机会、机会假设或类似表达，请把相关词组或句子加粗。"
    )
    if table_spec and isinstance(table_spec, dict) and table_spec.get("agent_system_prompt"):
        system += f"\n\nAlso follow this user-provided extra system prompt for this table while still writing the visible answer in English:\n{table_spec['agent_system_prompt']}"
    peers = "\n\n".join(format_agent(profile) for profile in table_agents)
    transcript = "\n\n".join(conversation) or "None yet."
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
        f"桌长记忆（可以回顾上几轮对此问题的讨论）：\n{format_memory(memory, view='speaker')}\n\n"
        f"你的 carry_over_packet（agent-level migrant memory，你上一轮 takeaway 的个人洞察，优先级高发言时必结合反思，作为概论发言的独特认知）：\n{format_packet(carry_over_packet)}\n\n"
        f"本轮到目前为止的对话：\n{transcript}\n\n"
        "现在轮到你发言。请像真实小桌参与者一样结合table_spec、background_context（不需要列举背景材料中的例子）、table_memory（可以回顾上几轮对此问题的讨论，你可以回应、发散、评价、延展、反对等） 和 carry_over_packet(你上一轮takeaway的个人洞察，作为独特认知影响你该轮的发言) 自然回应，不要按字段、来源或小标题输出。"
        "如果前面已经有人发言，先回应最近一位发言者的意思，再把你的观察自然接进去；"
        "如果当前讨论已经重复上一轮的稳定 pattern，请不要再阐述同一观点，而是带入一个不同用户/场景/机制盲点/反例/追问。"
        "如果你使用了 carry_over_packet 或 table_memory，只让它影响你的判断，不要说明你正在使用它。"
        "每次发言请仔细回顾本桌问题（大问题+小问题），不要跑题"
        "每次发言字数严格控制在100字以内。"
    )
    return system, user


def host_opening_prompt(
    *,
    question: str,
    parent_question: str,
    round_index: int,
    memory: TableMemory,
    background_context: str = "",
) -> tuple[str, str]:
    system = (
        "你是 World Cafe table host agent。"
        "你的任务是在每轮开始负责中立、简短、开放的引导。"
        "opening 不能出现设计机会、机会假设或类似表达。"
        "一定要是简单明了的设计问题提问范式。"
    )
    focus = _round_focus(round_index)
    if round_index <= 0:
        round_instruction = (
            f"当前是 Round 1（{focus}）。\n"
            "侧重【发散观察】：不需要提出小问题，引导参与者打开观察面，没有table_memory则不需要提小问题。\n"
        )
    elif round_index == 1:
        round_instruction = (
            f"当前是 Round 2（{focus}）。\n"
            "侧重【连接与张力】：结合 Round 1 的 table_memory，避开已有的重复主题，追问新的转变、挑战少数启发、未解张力等，参考其下一轮种子问题。\n"
            "提出2个可直接开启讨论的简短开放问句，每个问题一句话，不需要用很具体的场景。"
        )
    else:
        round_instruction = (
            f"当前是 Round {round_index + 1}（{focus}）。\n"
            "侧重【问题重构】：结合前几轮 table_memory，追问原始问题是否要改写、哪个未解决张力可能变成设计机会、哪个假设最值得验证。\n"
            "提出2个可直接开启讨论的简短开放问句，每个问题一句话，不需要用很具体的场景。"
        )
    user = (
        f"用户原始大问题：{parent_question}\n"
        f"本桌问题：{question}\n\n"
        f"既有 table_memory：\n{format_memory(memory, view='host_opening')}\n\n"
        f"background_context：\n{format_background(background_context)}\n\n"
        f"{round_instruction}\n\n"
        + (
            "如需提出子问题，请严格使用以下格式：\n"
            "【开场白，说明本轮讨论的关注点（10字以内）】\n"
            "- 【问题一（一句话引导，10字以内）】\n"
            "- 【问题二（一句话引导，10字以内）】\n"
            if round_index > 0
            else "只输出一句简短开场白（10字），不要提出任何问题。\n"
        )
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
        "你是这个 table host 的内部迁移记忆生成视角，正在记录每轮的 formatmemory。"
        "formatmemory 每轮按顺序记录，只从本轮 speaking agents 的发言中提取：桌子问题下重复出现的主题、少数但有启发的观点、未解决张力。概括其中的pattern，而不是具体的设计描述。"
        "这是内部记忆，不是可见发言；不要写会议纪要，不要生成完整方案，不要暴露给用户看的 Markdown。"
        "请输出可供系统路由和被上下文引用的严格 JSON。"
    )
    system += (
        "\n\nIf user_marked_notes exist, treat them as high-priority evidence for deciding which minority views or tensions deserve retention. "
        "However, formatmemory must still be grounded in this round's speaking agents and must not mechanically copy the notes."
    )
    joined_contributions = "\n\n".join(contributions)
    formatted_user_notes = format_user_notes(user_notes)
    user = (
        f"桌子：{table_id}\n"
        f"轮次：{round_index + 1}\n"
        f"用户原始大问题：{parent_question_from_spec(question, table_spec or {})}\n"
        f"本桌初始问题：{question}\n\n"
        f"用户笔记（优先参考其关键词）：\n{formatted_user_notes}\n\n"
        f"本轮 speaking agents 的全部发言（优先参考所有内容）：\n{joined_contributions}\n\n"
        f"背景材料：\n{format_background(background_context)}\n\n"
        "请输出 JSON：\n"
        "{\n"
        f'  "tablememory_usage_description": "{TABLEMEMORY_USAGE_DESCRIPTION}",\n'
        '  "formatmemory": {\n'
        '    "table_question": "original table question",\n'
        f'    "round_index": {round_index + 1},\n'
        '    "repeated_themes": ["桌子问题下重复出现的主题"],\n'
        '    "minority_inspiring_views": ["少数但有启发的观点"],\n'
        '    "unresolved_tensions": ["未解决张力"]\n'
        '  }\n'
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
        "你是 World Cafe table host agent。现在你要阅读本轮所有发言和用户标记笔记，输出本轮可见结束语，而不是内在记忆 JSON。"
        "结束语的任务不是完整总结，而是让参与者看见本轮的pattern：重复出现的主题（共识）、讨论的转变、少数但有启发的观点、未解决张力。"
        "只输出自然语言 Markdown，不要暴露字段名、JSON、模板名或内部记忆说明。"
        "用关键词式短句，300字以内，最多4行；不要写成长段落，不要复述每个人发言。"
    )
    user = (
        f"用户原始大问题：{parent_question_from_spec(question, table_spec or {})}\n\n"
        f"本轮 table_memory：\n{format_closing_context(memory_update)}\n\n"
        f"用户标记笔记（优先参考其中的pattern）：\n{format_user_notes(user_notes)}\n\n"
        f"本轮所有发言：\n{chr(10).join(contributions)}\n\n"
        "请输出 200 字以内的本轮结束语。建议形式：\n"
        "- 共识：关键词/短句\n"
        "- 转变：关键词/短句\n"
        "- 隐藏观点：（对应少数但有启发的观点）关键词/短句\n"
        "- 张力：关键词/短句\n"
        "可以调整措辞，但重点必须是差异、缺口、冲突和未完成问题，不要做完整摘要。"
        "不要总结讨论中出现的具体设计描述，仅总结pattern"
        "如果结束语中使用到了用户标记笔记中的关键词，请将该关键词加粗。"
    )
    return system, user


def carry_over_packet_prompt(
    *,
    agent: AgentProfile,
    from_table: str,
    to_table: str,
    after_round: int,
    from_memory: TableMemory,
    agent_contributions: list[str],
) -> tuple[str, str]:
    system = (
        "You are the internal migration-memory generation perspective of this World Cafe speaking agent, creating your own carry_over_packet. "
        "Always write JSON values in English, even when the user request, background, notes, or prior content are in another language. "
        "You are not the table host and not a summarizer. The packet is agent-level migrant memory, not a copy of table_memory and not a full previous-table summary. "
        "Use an LLM-generated template: keep the routing shell fixed, while the internal memory template should emerge from this agent's role and prior contribution. "
        "This is internal migration memory, not visible speech. Return strict JSON for system routing and next-round context."
    )
    user = (
        f"Agent:\n{format_agent(agent)}\n\n"
        f"from_table: {from_table}\n"
        f"to_table: {to_table}\n"
        f"after_round: {after_round + 1}\n\n"
        f"All contributions by this speaking agent in the current round:\n{chr(10).join(agent_contributions) or 'None yet.'}\n\n"
        "Return JSON:\n"
        "{\n"
        '  "agent": {"id": "...", "name": "...", "role": "...", "skills": ["..."]},\n'
        f'  "from_table": "{from_table}",\n'
        f'  "to_table": "{to_table}",\n'
        f'  "after_round": {after_round + 1},\n'
        '  "agent_generated_memory": {\n'
        '    "personal_insight": "基于该 agent 本轮发言生成的个人洞察（不要直接引用发言的原文，从设计视角反思自己的发言，输出对自己观点的整理认知，要求100字以内）"\n'
        '  }\n'
        "}"
    )
    return system, user


def global_harvest_prompt(table_memories: dict[str, TableMemory], table_round_outputs: list[TableRoundOutput]) -> tuple[str, str]:
    system = (
              "你负责将目前讨论空间内的所有文本和每桌的pattern动态转化为可直接给用户看的结构化设计洞察。"
              "设计洞察包括三个维度：用户需求、设计问题、设计方向。"
              "总字符数必须800字以内，可直接给用户看。"
              "不要写成长段落，不要复述每个人发言，不要展示额外推理过程。"
    )
    speaking_history = format_speaking_agent_history(table_round_outputs)
    all_table_memories = []
    for table_id, memory in sorted(table_memories.items()):
        all_table_memories.append(f"## {table_id}\n{format_memory(memory, view='full')}")
    table_memory_text = "\n\n".join(all_table_memories) or "暂无"
    user = (
        "以下是所有 speaking agents 的历史对话原文（含每桌每轮的桌子问题）：\n\n"
        f"{speaking_history}\n\n"
        "以下是所有桌子的所有轮次 table_memory（用于识别重复的主题和洞察转变）：\n\n"
        f"{table_memory_text}\n\n"
        "请综合所有桌子的讨论，输出一份整合的全局设计洞察（不要按桌分开，不要输出多个洞察）。\n"
        "优先输出 JSON，包含字段 user_needs、reframed_design_problem、next_design_directions、display_markdown。\n"
        "display_markdown 必须800字以内，可直接给用户看，严格使用以下格式：\n\n"
        "## 全局设计洞察\n"
        "### 用户主要需求\n"
        "（综合所有桌子讨论提炼出的核心需求）\n\n"
        "### 设计问题重新界定\n"
        "（基于多轮讨论的转变，重新定义设计问题）\n\n"
        "### 后续设计方向（不超过三个）\n"
        "- ...\n"
        "- ...\n"
        "- ...\n\n"
        "如果无法输出 JSON，则直接输出同样结构的自然 Markdown。"
    )
    return system, user


def _round_focus(round_index: int) -> str:
    if round_index <= 0:
        return "Divergent Observation"
    if round_index == 1:
        return "Connections And Tensions"
    return "Problem Reframing"
