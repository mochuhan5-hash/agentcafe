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
from world_cafe.state import AgentProfile, CarryOverPacket, TableMemory, TableSpec, UserNote


def format_agent(profile: AgentProfile) -> str:
    skills = "、".join(profile.get("skills", [])) or "未填写"
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
        f"桌长记忆：\n{format_memory(memory, view='speaker')}\n\n"
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
        f"既有 table_memory（按开场问题裁剪）：\n{format_memory(memory, view='host_opening')}\n\n"
        f"background_context：\n{format_background(background_context)}\n\n"
        "请输出简短 Markdown，系统会只把 opening 展示给用户，question_seeds 只用于流程引导：\n"
        "## opening\n"
        "提出2-3个可直接开启讨论的简短开放问句，每个问题尽量一句话。\n\n"
        "## question_seeds\n"
        "查看本桌所有已完成轮次的 table_memory（如有），在本桌问题背景下，按照不同的 round 提出以下不同维度的引导性子问题：\n"
        "- Round 1 发散观察：基于本桌问题和背景材料，引导参与者打开观察面。\n"
        "- Round 2 连接与张力：结合 Round 1 的 table_memory，避开已稳定共识，追问新的转变、挑战少数观点、利益相关者/机制张力等。\n"
        "- Round 3 问题重构：结合前两轮 table_memory，追问原始问题是否要改写、哪个未解决张力可能变成设计机会、哪个假设最值得验证。\n"
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
        "你是这个 table host 的内部迁移记忆生成视角，正在记录每轮的 formatmemory。"
        "formatmemory 每轮按顺序记录，只从本轮 speaking agents 的发言中提取：桌子问题下重复出现的主题、少数但有启发的观点、未解决张力。"
        "这是内部记忆，不是可见发言；不要写会议纪要，不要生成完整方案，不要暴露给用户看的 Markdown。"
        "请输出可供系统路由和被上下文引用的严格 JSON。"
    )
    system += (
        "\n\n若存在 user_marked_notes，可把它们作为高优先级证据帮助判断哪些少数观点或张力值得保留；"
        "但 formatmemory 仍必须以本轮 speaking agents 的发言为输入，不要机械复制笔记。"
    )
    joined_contributions = "\n\n".join(contributions)
    formatted_user_notes = format_user_notes(user_notes)
    user = (
        f"桌子：{table_id}\n"
        f"轮次：{round_index + 1}\n"
        f"用户原始大问题：{parent_question_from_spec(question, table_spec or {})}\n"
        f"本桌初始问题：{question}\n\n"
        f"table_spec（只作问题边界参考）：\n{format_table_spec(table_spec or {})}\n\n"
        f"User-marked notes for this table/round (highest-priority evidence):\n{formatted_user_notes}\n\n"
        f"桌长画像：\n{format_agent(host)}\n\n"
        f"既有 formatmemory（按轮顺序记录）：\n{format_memory(memory, view='host_synthesis')}\n\n"
        f"背景材料（只作任务边界参考）：\n{format_background(background_context)}\n\n"
        f"本轮 speaking agents 的全部发言：\n{joined_contributions}\n\n"
        "请输出 JSON：\n"
        "{\n"
        '  "formatmemory": {\n'
        '    "table_question": "本桌问题原文",\n'
        f'    "round_index": {round_index + 1},\n'
        '    "repeated_themes": ["桌子问题下重复出现的主题"],\n'
        '    "minority_inspiring_views": ["少数但有启发的观点"],\n'
        '    "unresolved_tensions": ["未解决张力"]\n'
        '  },\n'
        '  "next_round_question_seeds": ["可选，下一轮继续追问的1-3个问题"]\n'
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
        f"桌子：{table_id}\n"
        f"轮次：{round_index + 1}\n"
        f"用户原始大问题：{parent_question_from_spec(question, table_spec or {})}\n"
        f"本桌问题：{question}\n\n"
        f"table_spec：\n{format_table_spec(table_spec or {})}\n\n"
        f"桌长画像：\n{format_agent(host)}\n\n"
        f"既有 table_memory（按结束语裁剪）：\n{format_memory(memory, view='host_closing')}\n\n"
        f"用户标记笔记（优先参考）：\n{format_user_notes(user_notes)}\n\n"
        f"本轮内在记忆合成后的可见上下文：\n{format_closing_context(memory_update)}\n\n"
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
        "采用 LLM-generated template：固定路由外壳，内部记忆模板根据 agent 角色和该 agent 在上一桌的发言动态生成。"
        "这是内部迁移记忆，不是可见发言。请输出可供系统路由和下轮上下文引用的严格 JSON。"
    )
    user = (
        f"agent：\n{format_agent(agent)}\n\n"
        f"from_table：{from_table}\n"
        f"to_table：{to_table}\n"
        f"after_round：{after_round + 1}\n\n"
        f"该 speaking agent 在本轮对话中的所有发言：\n{chr(10).join(agent_contributions) or '暂无'}\n\n"
        f"下一桌问题（只帮助生成可迁移洞察，不要写成解决方案）：{to_question}\n\n"
        "请输出 JSON：\n"
        "{\n"
        '  "agent": {"id": "...", "name": "...", "role": "...", "skills": ["..."]},\n'
        f'  "from_table": "{from_table}",\n'
        f'  "to_table": "{to_table}",\n'
        f'  "after_round": {after_round + 1},\n'
        '  "agent_generated_memory": {\n'
        '    "skill_lens": "这个 agent 使用了什么 skill 或角色视角",\n'
        '    "personal_insight": "基于该 agent 本轮发言生成的个人洞察",\n'
        '    "carry_forward_question": "下一桌可检验或连接的追问"\n'
        '  }\n'
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
        memories.append(f"## {table_id}\n{format_memory(memory, view='harvest')}")
    memories_text = "\n\n".join(memories)
    summaries = "\n".join(str(summary) for summary in round_summaries)
    user = (
        "以下是所有桌子的桌长记忆：\n\n"
        f"{memories_text}\n\n"
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


def _round_focus(round_index: int) -> str:
    if round_index <= 0:
        return "发散观察"
    if round_index == 1:
        return "连接与张力"
    return "问题重构"
