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
        "You are a rotating World Cafe participant discussing design questions and insights with other participants. "
        "Always write visible output in English, even when the user request, background, notes, or prior content are in another language. "
        "Do not list interview examples from background_context; speak from your own experience, judgment, and point of view. "
        "Your visible contribution should sound like natural small-table dialogue, not a structured report. "
        "Each turn must stay under 100 English words. "
        "Use table_spec, background_context, table_memory, and carry_over_packet as context that shapes your judgment, but do not mechanically restate them or expose JSON, field names, template names, or pocket structure. "
        "The original user request and background material define the larger task boundary; the table question is the current entry point. "
        "Synthesize all context, but respond first to the current conversation, especially the immediately previous speaker, then add a natural observation, question, disagreement, or extension. "
        "Do not re-summarize the table question or repeat stable consensus; if the discussion starts repeating earlier patterns, move toward differences, blind spots, edge cases, evidence, or testable follow-up questions. "
        "Each turn should perform one conversational move: add a heterogeneous scenario, point out a blind spot or risk, compare your prior table insight with this table's view, ask a concrete follow-up, or identify an early design opportunity. "
        "Avoid labels such as previous table/current table/new connection unless a very brief mention is needed for conversational clarity. "
        "Do not dominate the new table, retell the full previous table discussion, or propose a complete solution. "
        "If your contribution mentions a design opportunity, opportunity hypothesis, or similar phrase, bold the relevant phrase or sentence."
    )
    if table_spec and isinstance(table_spec, dict) and table_spec.get("agent_system_prompt"):
        system += f"\n\nAlso follow this user-provided extra system prompt for this table while still writing the visible answer in English:\n{table_spec['agent_system_prompt']}"
    peers = "\n\n".join(format_agent(profile) for profile in table_agents)
    transcript = "\n\n".join(conversation) or "None yet."
    user = (
        f"Table: {table_id}\n"
        f"Round: {round_index + 1}\n"
        f"Turn number at this table: {turn_index + 1}\n"
        f"Your speaking cycle this round: {cycle_index + 1}\n"
        f"Original user request: {parent_question_from_spec(question, table_spec)}\n"
        f"Initial table question: {question}\n\n"
        f"Table spec:\n{format_table_spec(table_spec or {})}\n\n"
        f"Background material:\n{format_background(background_context)}\n\n"
        f"Your profile:\n{format_agent(agent)}\n\n"
        f"Table members:\n{peers}\n\n"
        f"Host memory, including prior-round discussion about this question:\n{format_memory(memory, view='speaker')}\n\n"
        f"Your carry_over_packet, meaning your agent-level migrant memory and prior-round personal takeaway:\n{format_packet(carry_over_packet)}\n\n"
        f"Conversation so far this round:\n{transcript}\n\n"
        "It is your turn. Respond naturally like a real small-table participant, using table_spec, background_context, table_memory, and carry_over_packet as context without naming those sources or adding headings. "
        "If someone spoke before you, first pick up the most recent speaker's point, then add your observation. "
        "If the current discussion repeats a stable pattern from earlier, introduce a different user, scenario, mechanism blind spot, counterexample, or follow-up question. "
        "If carry_over_packet or table_memory shaped your judgment, do not say that you used it. "
        "Stay anchored to the original user request and this table question. "
        "Write under 100 English words."
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
        "You are a World Cafe table host agent. "
        "Always write visible output in English, even when the user request, background, notes, or prior content are in another language. "
        "At the start of each round, provide neutral, brief, open guiding sub-questions. "
        "If the opening mentions a design opportunity, opportunity hypothesis, or similar phrase, bold the relevant phrase or sentence."
    )
    user = (
        f"Original user request: {parent_question}\n"
        f"Table question: {question}\n\n"
        f"Existing table_memory, trimmed for opening questions:\n{format_memory(memory, view='host_opening')}\n\n"
        f"background_context:\n{format_background(background_context)}\n\n"
        "Return brief Markdown. The system will show only the opening section to the user:\n"
        "## opening\n"
        "Review all completed rounds of table_memory if present, then guide each round differently in the context of this table question:\n"
        "- Round 1 divergent observation: open the field of observation. If there is no table_memory, do not force sub-questions.\n"
        "- Round 2 connections and tensions: use Round 1 memory to avoid settled consensus and ask about new shifts, minority views, stakeholder tensions, or mechanism tensions.\n"
        "- Round 3 problem reframing: use prior memory to ask whether the original problem should be rewritten, which unresolved tension could become a design opportunity, and which assumption deserves testing.\n"
        "When sub-questions are needed, end with only 2-3 brief open questions that can directly start discussion. Keep each question to one sentence. Add little or no background explanation, and let questions progress across rounds."
        "If sub-questions are needed, strictly use this format, omitting the third question when only two are needed:\n"
        "[Opening phrase stating this round's focus in under 10 English words]\n"
        "- [Question 1, one sentence, no extra setup]\n"
        "- [Question 2, one sentence, no extra setup]\n"
        "- [Question 3, one sentence, no extra setup]\n"


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
        "You are the internal memory-generation perspective of this table host, recording each round's formatmemory. "
        "Always write JSON values in English, even when the user request, background, notes, or prior content are in another language. "
        "For each round, formatmemory should append one record drawn only from this round's speaking agents: recurring themes under the table question, minority-but-inspiring views, and unresolved tensions. "
        "Briefly abstract the patterns; do not quote the historical discussion verbatim. "
        "This is internal memory, not visible speech. Do not write minutes, do not generate a complete solution, and do not expose user-facing Markdown. "
        "Return strict JSON for system routing and future context."
    )
    system += (
        "\n\nIf user_marked_notes exist, treat them as high-priority evidence for deciding which minority views or tensions deserve retention. "
        "However, formatmemory must still be grounded in this round's speaking agents and must not mechanically copy the notes."
    )
    joined_contributions = "\n\n".join(contributions)
    formatted_user_notes = format_user_notes(user_notes)
    user = (
        f"Table: {table_id}\n"
        f"Round: {round_index + 1}\n"
        f"Original user request: {parent_question_from_spec(question, table_spec or {})}\n"
        f"Initial table question: {question}\n\n"
        f"table_spec, only as a question-boundary reference:\n{format_table_spec(table_spec or {})}\n\n"
        f"User-marked notes for this table/round (highest-priority evidence):\n{formatted_user_notes}\n\n"
        f"Host profile:\n{format_agent(host)}\n\n"
        f"Existing formatmemory, recorded by round:\n{format_memory(memory, view='host_synthesis')}\n\n"
        f"Background material, only as task-boundary reference:\n{format_background(background_context)}\n\n"
        f"All speaking-agent contributions this round:\n{joined_contributions}\n\n"
        "Return JSON:\n"
        "{\n"
        f'  "tablememory_usage_description": "{TABLEMEMORY_USAGE_DESCRIPTION}",\n'
        '  "formatmemory": {\n'
        '    "table_question": "original table question",\n'
        f'    "round_index": {round_index + 1},\n'
        '    "repeated_themes": ["recurring themes under the table question"],\n'
        '    "minority_inspiring_views": ["minority but inspiring views"],\n'
        '    "unresolved_tensions": ["unresolved tensions"]\n'
        '  },\n'
        '  "next_round_question_seeds": ["optional 1-3 questions to continue probing next round"]\n'
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
        "You are a World Cafe table host agent. Now write the visible closing note for this round, not internal memory JSON. "
        "Always write visible output in English, even when the user request, background, notes, or prior content are in another language. "
        "The closing note should not be a complete summary; it should let participants see this round's pattern: recurring themes, shifts in discussion, minority but inspiring views, and unresolved tensions. "
        "Output only natural-language Markdown. Do not expose field names, JSON, template names, or internal-memory instructions. "
        "Use keyword-like short lines, stay under 300 English words, use at most 4 lines, avoid long paragraphs, and do not recap each person's turn."
    )
    user = (
        f"Table: {table_id}\n"
        f"Round: {round_index + 1}\n"
        f"Original user request: {parent_question_from_spec(question, table_spec or {})}\n"
        f"Table question: {question}\n\n"
        f"table_spec:\n{format_table_spec(table_spec or {})}\n\n"
        f"Host profile:\n{format_agent(host)}\n\n"
        f"Existing table_memory, trimmed for closing:\n{format_memory(memory, view='host_closing')}\n\n"
        f"User-marked notes, priority reference:\n{format_user_notes(user_notes)}\n\n"
        f"Visible context synthesized from this round's internal memory:\n{format_closing_context(memory_update)}\n\n"
        f"This round's contribution excerpts:\n{chr(10).join(contributions[:12])}\n\n"
        "Write this round's closing note in under 300 English words. Suggested form:\n"
        "- Consensus: keywords or short phrase\n"
        "- Shift: keywords or short phrase\n"
        "- Hidden view: keywords or short phrase for the minority-but-inspiring view\n"
        "- Tension: keywords or short phrase\n"
        "You may adjust the wording, but focus on differences, gaps, conflicts, and unfinished questions. Do not write a full summary."
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
        '    "skill_lens": "which skill or role lens this agent used",\n'
        '    "personal_insight": "a personal insight generated from this agent\'s round contribution; do not quote the original wording, reflect on the agent\'s own point of view, under 50 English words"\n'
        '  }\n'
        "}"
    )
    return system, user


def global_harvest_prompt(table_memories: dict[str, TableMemory], table_round_outputs: list[TableRoundOutput]) -> tuple[str, str]:
    system = (
        "You lead the global harvest for a World Cafe. You are not a summary merger. "
        "Always write visible output in English, even when the user request, background, notes, or prior content are in another language. "
        "You must directly read the speaking agents' historical dialogue as the primary evidence, extract the user's main needs, reframe the design problem, and propose next design directions. "
        "tablememory and other secondary synthesis should only support wording and calibration, not serve as the primary harvest input. "
        "The final result must contain exactly three structured design insights. Each insight must include user need, reframed design problem, and next design direction. "
        "Each next design direction must be researchable, testable, or actionable for design progress. "
        "You may use JSON internally, but the user-facing display_markdown must read naturally and must not expose internal field explanations. "
        "display_markdown must stay under 1200 English words and strictly use the requested English three-insight format. "
        "If the display mentions a design opportunity, opportunity hypothesis, or similar phrase, bold the relevant phrase or sentence."
    )
    table_contexts = []
    tablememory_sections = []
    for table_id, memory in sorted(table_memories.items()):
        table_contexts.append(f"## {table_id}\nTable question: {memory.get('question', '')}")
        tablememory_sections.append(f"## {table_id}\n{format_memory(memory, view='full')}")
    table_context_text = "\n\n".join(table_contexts) or "None yet."
    tablememory_text = "\n\n".join(tablememory_sections) or "None yet."
    speaking_history = format_speaking_agent_history(table_round_outputs)
    user_note_history = format_user_note_history(table_round_outputs)
    user = (
        "Below is the original dialogue history from all speaking agents. Treat it as the primary harvest evidence with the highest priority:\n\n"
        f"{speaking_history}\n\n"
        "Below are the discussion questions for all tables, only for locating the dialogue source:\n\n"
        f"{table_context_text}\n\n"
        "Below is tablememory for all tables, carrying each table's accumulated rounds:\n\n"
        f"{tablememory_text}\n\n"
        "Below are user-marked notes from each round. Use them to calibrate the insights, tensions, and opportunity signals the user cared about:\n\n"
        f"{user_note_history}\n\n"
        "Prefer returning JSON with fields design_insights, user_needs, reframed_design_problem, next_design_directions, and display_markdown.\n"
        "design_insights must contain exactly three items. Each item must contain user_need, reframed_design_problem, and design_direction.\n"
        "display_markdown must stay under 1200 English words, be directly user-facing, and strictly use this format:\n"
        "Design Insights:\n"
        "### Insight 1\n"
        "1. User need: ...\n"
        "2. Reframed design problem: ...\n"
        "3. Up to three next design directions: ...\n\n"
        "### Insight 2\n"
        "1. User need: ...\n"
        "2. Reframed design problem: ...\n"
        "3. Up to three next design directions: ...\n\n"
        "### Insight 3\n"
        "1. User need: ...\n"
        "2. Reframed design problem: ...\n"
        "3. Up to three next design directions: ...\n"
        "If JSON cannot be produced, directly output natural Markdown in the same structure."
    )
    return system, user


def _round_focus(round_index: int) -> str:
    if round_index <= 0:
        return "Divergent Observation"
    if round_index == 1:
        return "Connections And Tensions"
    return "Problem Reframing"
