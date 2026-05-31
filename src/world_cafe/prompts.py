from __future__ import annotations

from world_cafe.state import AgentProfile, TableMemory


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
    return (
        f"桌子问题：{memory['question']}\n"
        f"活记忆摘要：{memory.get('living_summary') or '暂无'}\n"
        f"关键洞察：\n{insights}\n"
        f"开放问题：\n{questions}\n"
        f"张力：\n{tensions}"
    )


def format_background(background_context: str) -> str:
    context = background_context.strip()
    if not context:
        return "暂无。"
    max_chars = 12000
    if len(context) > max_chars:
        context = f"{context[:max_chars]}\n\n[背景材料过长，已截断到前 {max_chars} 字符。]"
    return context


def contribution_prompt(
    *,
    table_id: str,
    question: str,
    round_index: int,
    agent: AgentProfile,
    table_agents: list[AgentProfile],
    memory: TableMemory,
    conversation: list[str],
    background_context: str,
    turn_index: int,
    cycle_index: int,
) -> tuple[str, str]:
    system = (
        "你是世界咖啡小桌讨论中的参与者。"
        "请基于你的画像和现场上下文自由发言，可以回应同桌，也可以提出新方向。"
    )
    peers = "\n\n".join(format_agent(profile) for profile in table_agents)
    transcript = "\n\n".join(conversation) or "暂无。"
    user = (
        f"桌子：{table_id}\n"
        f"轮次：{round_index + 1}\n"
        f"本轮发言序号：{turn_index + 1}\n"
        f"本轮对话循环：{cycle_index + 1}\n"
        f"本桌初始问题：{question}\n\n"
        f"你的画像：\n{format_agent(agent)}\n\n"
        f"本桌成员：\n{peers}\n\n"
        f"桌长记忆：\n{format_memory(memory)}\n\n"
        f"背景材料参考：\n{format_background(background_context)}\n\n"
        f"本轮到目前为止的对话：\n{transcript}\n\n"
        "现在轮到你发言。请控制在300字以内。"
    )
    return system, user


def host_synthesis_prompt(
    *,
    table_id: str,
    question: str,
    round_index: int,
    host: AgentProfile,
    memory: TableMemory,
    contributions: list[str],
    background_context: str = "",
) -> tuple[str, str]:
    system = (
        "你是世界咖啡的桌长与记录者。"
        "你的任务是维护本桌记忆，不评价谁赢了，而是保留洞察、分歧、开放问题和下一轮可接续的线索。"
        "请严格使用指定 Markdown 小标题。"
    )
    joined_contributions = "\n\n".join(contributions)
    user = (
        f"桌子：{table_id}\n"
        f"轮次：{round_index + 1}\n"
        f"本桌初始问题：{question}\n\n"
        f"桌长画像：\n{format_agent(host)}\n\n"
        f"既有桌长记忆：\n{format_memory(memory)}\n\n"
        f"背景材料参考：\n{format_background(background_context)}\n\n"
        f"本轮发言：\n{joined_contributions}\n\n"
        "请输出：\n"
        "## synthesis\n"
        "一段 80-160 字综合摘要。\n\n"
        "## key_insights\n"
        "- 3-5 条关键洞察。\n\n"
        "## open_questions\n"
        "- 2-4 条开放问题。\n\n"
        "## tensions\n"
        "- 1-3 条值得保留的张力或分歧。"
    )
    return system, user


def global_harvest_prompt(table_memories: dict[str, TableMemory], round_summaries: list[dict]) -> tuple[str, str]:
    system = (
        "你负责世界咖啡的全局 harvest。"
        "请跨桌提炼共同模式、独特洞察、关键张力和下一步实验。"
        "不要抹平分歧，保留可继续研究的问题。"
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
        "请输出 500字以内的 Markdown，包含：\n"
        "## Shared Patterns\n"
        "## Unique Signals\n"
        "## Cross-table Tensions\n"
        "## Open Questions\n"
        "## Next Experiments"
    )
    return system, user
