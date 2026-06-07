from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from world_cafe.formatting import emphasize_design_opportunities
from world_cafe.llm import CafeLLM
from world_cafe.parsing import extract_bullets, extract_section, loads_jsonish_object, unique_append
from world_cafe.profiles import build_default_agent_profiles, normalize_questions
from world_cafe.prompts import (
    carry_over_packet_prompt,
    contribution_prompt,
    global_harvest_prompt,
    host_closing_prompt,
    host_opening_prompt,
    host_synthesis_prompt,
    parent_question_from_spec,
)
from world_cafe.rotation import build_initial_assignments, rotate_non_hosts
from world_cafe.state import (
    AgentProfile,
    CarryOverPacket,
    TableMemory,
    TableRoundOutput,
    TableSpec,
    UserNote,
    WorldCafeState,
)
from world_cafe.trace import emit_stream_event, make_event


def create_initial_state(
    *,
    questions: list[str] | dict[str, str],
    agents: list[AgentProfile] | None = None,
    rounds: int = 3,
    table_count: int = 4,
    seats_per_table: int = 4,
    speeches_per_agent: int = 3,
    background_context: str = "",
    background_filename: str = "",
    table_specs: dict[str, TableSpec] | None = None,
    table_question_plan: dict[str, Any] | None = None,
    expert_skill_routes: dict[str, Any] | None = None,
    assignments: dict[str, list[str]] | None = None,
    hosts: dict[str, str] | None = None,
    run_id: str | None = None,
) -> WorldCafeState:
    table_questions = normalize_questions(questions, table_count=table_count)
    normalized_table_specs = _normalize_table_specs(table_questions, table_specs)
    if rounds < 1:
        raise ValueError("rounds must be at least 1")
    if seats_per_table < 2:
        raise ValueError("seats_per_table must be at least 2")
    if speeches_per_agent < 1:
        raise ValueError("speeches_per_agent must be at least 1")
    table_ids = sorted(table_questions)
    required_agents = table_count * seats_per_table
    referenced_ids = set()
    if assignments:
        referenced_ids.update(agent_id for table_agents in assignments.values() for agent_id in table_agents)
    if hosts:
        referenced_ids.update(hosts.values())
    agent_profiles = _ensure_agent_profiles(agents, required_agents, referenced_ids)

    if assignments is None or hosts is None:
        assignments, hosts = build_initial_assignments(
            agent_ids=[agent["id"] for agent in agent_profiles],
            table_ids=table_ids,
            seats_per_table=seats_per_table,
        )
    else:
        assignments, hosts = _normalize_initial_assignments(
            assignments=assignments,
            hosts=hosts,
            table_ids=table_ids,
            valid_agent_ids={agent["id"] for agent in agent_profiles},
        )
    table_memories = {
        table_id: _empty_table_memory(table_id, question, hosts[table_id])
        for table_id, question in table_questions.items()
    }
    return {
        "run_id": run_id or str(uuid.uuid4()),
        "stage": "setup",
        "table_questions": table_questions,
        "table_specs": normalized_table_specs,
        "table_question_plan": table_question_plan or {"tables": list(normalized_table_specs.values())},
        "expert_skill_routes": expert_skill_routes or {},
        "background_context": background_context,
        "source_context": background_context,
        "background_filename": background_filename,
        "table_count": table_count,
        "seats_per_table": seats_per_table,
        "speeches_per_agent": speeches_per_agent,
        "max_rounds": rounds,
        "round_index": 0,
        "agent_profiles": agent_profiles,
        "assignments": assignments,
        "hosts": hosts,
        "table_memories": table_memories,
        "agent_pockets": {},
        "pocket_history": [],
        "host_openings": [],
        "question_seed_history": [],
        "table_round_outputs": [],
        "round_summaries": [],
        "rotation_history": [],
        "trace": [],
        "warnings": [],
    }


PauseCheck = Callable[[str], Awaitable[None]]
NoteCheckpoint = Callable[[str, str, int], Awaitable[list[UserNote]]]


async def _no_pause_check(_run_id: str) -> None:
    return None


async def _no_note_checkpoint(_run_id: str, _table_id: str, _round_index: int) -> list[UserNote]:
    return []


def build_world_cafe_graph(
    llm: CafeLLM,
    pause_check: PauseCheck | None = None,
    note_checkpoint: NoteCheckpoint | None = None,
):
    pause_check = pause_check or _no_pause_check
    note_checkpoint = note_checkpoint or _no_note_checkpoint
    builder = StateGraph(WorldCafeState)
    builder.add_node("setup", _setup)
    builder.add_node("begin_round", _begin_round)
    builder.add_node("table_discussion", _make_table_discussion_node(llm, pause_check, note_checkpoint))
    builder.add_node("collect_round", _collect_round)
    builder.add_node("rotate_agents", _rotate_agents)
    builder.add_node("global_harvest", _make_global_harvest_node(llm))

    builder.add_edge(START, "setup")
    builder.add_edge("setup", "begin_round")
    builder.add_conditional_edges("begin_round", _dispatch_tables, ["table_discussion"])
    builder.add_edge("table_discussion", "collect_round")
    builder.add_conditional_edges(
        "collect_round",
        _route_after_collect,
        {
            "rotate_agents": "rotate_agents",
            "global_harvest": "global_harvest",
        },
    )
    builder.add_edge("rotate_agents", "begin_round")
    builder.add_edge("global_harvest", END)
    return builder.compile()


def _setup(state: WorldCafeState) -> dict[str, Any]:
    event = make_event(
        "setup",
        "initialized world cafe",
        run_id=state["run_id"],
        tables=sorted(state["table_questions"]),
        max_rounds=state["max_rounds"],
        background_filename=state.get("background_filename", ""),
        has_background=bool(state.get("background_context", "").strip()),
    )
    emit_stream_event(event)
    return {"stage": "setup", "trace": [event]}


def _begin_round(state: WorldCafeState) -> dict[str, Any]:
    event = make_event(
        "round_started",
        f"round {state['round_index'] + 1} started",
        round_index=state["round_index"],
        assignments=state["assignments"],
    )
    emit_stream_event(event)
    return {"stage": "round_started", "trace": [event]}


def _dispatch_tables(state: WorldCafeState) -> list[Send]:
    sends: list[Send] = []
    next_table_by_agent = _next_table_by_agent(state) if state["round_index"] + 1 < state["max_rounds"] else {}
    for table_id in sorted(state["table_questions"]):
        sends.append(
            Send(
                "table_discussion",
                {
                    "run_id": state["run_id"],
                    "round_index": state["round_index"],
                    "table_id": table_id,
                    "question": state["table_questions"][table_id],
                    "table_spec": state.get("table_specs", {}).get(table_id, {}),
                    "all_table_questions": state["table_questions"],
                    "agent_profiles": state["agent_profiles"],
                    "agent_ids": state["assignments"][table_id],
                    "host_id": state["hosts"][table_id],
                    "memory": state["table_memories"][table_id],
                    "agent_pockets": state.get("agent_pockets", {}),
                    "next_table_by_agent": next_table_by_agent,
                    "speeches_per_agent": state.get("speeches_per_agent", 3),
                    "background_context": state.get("source_context") or state.get("background_context", ""),
                },
            )
        )
    return sends


def _make_table_discussion_node(llm: CafeLLM, pause_check: PauseCheck, note_checkpoint: NoteCheckpoint):
    async def table_discussion(task: dict[str, Any]) -> dict[str, Any]:
        table_id = task["table_id"]
        round_index = task["round_index"]
        start_event = make_event(
            "table_discussion",
            f"{table_id} discussion started",
            table_id=table_id,
            round_index=round_index,
            agent_ids=task["agent_ids"],
            host_id=task["host_id"],
            participant_ids=[agent_id for agent_id in task["agent_ids"] if agent_id != task["host_id"]],
        )
        emit_stream_event(start_event)

        profile_by_id = {profile["id"]: profile for profile in task["agent_profiles"]}
        table_agents = [profile_by_id[agent_id] for agent_id in task["agent_ids"]]
        participants = [agent for agent in table_agents if agent["id"] != task["host_id"]]
        memory: TableMemory = task["memory"]
        table_spec: TableSpec = task.get("table_spec") or _default_table_spec(table_id, task["question"])
        background_context = str(task.get("background_context", ""))
        speeches_per_agent = int(task.get("speeches_per_agent", 3))
        contributions: list[dict[str, Any]] = []
        contribution_events: list[dict[str, Any]] = []
        conversation: list[str] = []
        host = profile_by_id[task["host_id"]]

        await pause_check(task["run_id"])
        opening_system, opening_user = host_opening_prompt(
            question=task["question"],
            parent_question=parent_question_from_spec(task["question"], table_spec),
            memory=memory,
            background_context=background_context,
        )
        raw_host_opening = await llm.agenerate(opening_system, opening_user)
        opening_seeds = extract_bullets(extract_section(raw_host_opening, "question_seeds"))
        host_opening = _host_opening_display(raw_host_opening)
        opening_event = make_event(
            "host_opening",
            f"{table_id} host opened round {round_index + 1}",
            table_id=table_id,
            round_index=round_index,
            host_id=task["host_id"],
            host_name=host["name"],
            content=host_opening,
            memory_snapshot=_host_memory_snapshot(memory),
            question_seeds=opening_seeds,
        )
        emit_stream_event(opening_event)

        async def ask_agent(agent: AgentProfile, turn_index: int, cycle_index: int) -> dict[str, Any]:
            system, user = contribution_prompt(
                table_id=table_id,
                question=task["question"],
                round_index=round_index,
                agent=agent,
                table_agents=table_agents,
                memory=memory,
                table_spec=table_spec,
                carry_over_packet=(task.get("agent_pockets") or {}).get(agent["id"]),
                conversation=conversation,
                background_context=background_context,
                turn_index=turn_index,
                cycle_index=cycle_index,
            )
            content = emphasize_design_opportunities(await llm.agenerate(system, user))
            return {
                "agent_id": agent["id"],
                "agent_name": agent["name"],
                "content": content,
                "turn_index": turn_index,
                "cycle_index": cycle_index,
            }

        for cycle_index in range(speeches_per_agent):
            for agent in participants:
                await pause_check(task["run_id"])
                turn_index = len(contributions)
                try:
                    contribution = await ask_agent(agent, turn_index, cycle_index)
                except Exception as exc:
                    error_message = str(exc) or repr(exc)
                    contribution = {
                        "agent_id": agent["id"],
                        "agent_name": agent["name"],
                        "content": (
                            f"（{agent['name']} 本次发言生成失败，系统已跳过这次发言并继续下一位。"
                            f"错误：{error_message[:180]}）"
                        ),
                        "turn_index": turn_index,
                        "cycle_index": cycle_index,
                        "generation_error": error_message,
                    }
                contributions.append(contribution)
                conversation.append(
                    f"{contribution['agent_name']}：{contribution['content']}"
                )
                event = make_event(
                    "agent_contribution",
                    f"{contribution['agent_name']} contributed at {table_id}",
                    table_id=table_id,
                    round_index=round_index,
                    agent_id=contribution["agent_id"],
                    agent_name=contribution["agent_name"],
                    content=contribution["content"],
                    turn_index=contribution["turn_index"],
                    cycle_index=contribution["cycle_index"],
                    has_background_context=bool(background_context.strip()),
                    background_context_chars=len(background_context.strip()),
                    memory_snapshot=_speaker_memory_snapshot(
                        agent=agent,
                        carry_over_packet=(task.get("agent_pockets") or {}).get(agent["id"]),
                    ),
                    generation_error=contribution.get("generation_error"),
                )
                contribution_events.append(event)
                emit_stream_event(event)

        await pause_check(task["run_id"])
        user_notes = await note_checkpoint(task["run_id"], table_id, round_index)
        await pause_check(task["run_id"])
        synthesis_inputs = [
            f"### {item['agent_name']} ({item['agent_id']})\n{item['content']}"
            for item in contributions
        ]
        system, user = host_synthesis_prompt(
            table_id=table_id,
            question=task["question"],
            round_index=round_index,
            host=host,
            memory=memory,
            table_spec=table_spec,
            contributions=synthesis_inputs,
            background_context=background_context,
            user_notes=user_notes,
        )
        try:
            synthesis = await llm.agenerate(system, user)
        except Exception as exc:
            synthesis = _fallback_host_synthesis(contributions, str(exc) or repr(exc))
        table_memory_update = _parse_host_memory_update(synthesis)
        closing_system, closing_user = host_closing_prompt(
            table_id=table_id,
            question=task["question"],
            round_index=round_index,
            host=host,
            memory=memory,
            table_spec=table_spec,
            memory_update=table_memory_update,
            contributions=synthesis_inputs,
            user_notes=user_notes,
        )
        try:
            host_record_display = _format_host_closing_display(
                await llm.agenerate(closing_system, closing_user),
                table_memory_update,
                synthesis,
            )
        except Exception:
            host_record_display = _format_host_record_display(table_memory_update, synthesis)
        host_event = make_event(
            "host_record",
            f"{table_id} host record updated",
            table_id=table_id,
            round_index=round_index,
            host_id=task["host_id"],
            host_name=host["name"],
            content=host_record_display,
            memory_snapshot=_host_memory_snapshot(memory, table_memory_update),
            key_insights=_string_list(table_memory_update.get("key_insights")),
            open_questions=_string_list(table_memory_update.get("open_questions")),
            tensions=_string_list(table_memory_update.get("tensions")),
        )
        emit_stream_event(host_event)

        carry_over_packets = await _generate_carry_over_packets(
            llm=llm,
            participants=participants,
            contributions=contributions,
            table_id=table_id,
            round_index=round_index,
            memory_update=table_memory_update,
            fallback_memory=memory,
            next_table_by_agent=task.get("next_table_by_agent", {}),
            all_table_questions=task.get("all_table_questions", {}),
        )
        output: TableRoundOutput = {
            "table_id": table_id,
            "question": task["question"],
            "table_spec": table_spec,
            "round_index": round_index,
            "host_id": task["host_id"],
            "agent_ids": task["agent_ids"],
            "contributions": contributions,
            "host_opening": host_opening,
            "host_record_display": host_record_display,
            "synthesis": synthesis,
            "key_insights": _string_list(table_memory_update.get("key_insights")),
            "open_questions": _string_list(table_memory_update.get("open_questions")),
            "tensions": _string_list(table_memory_update.get("tensions")),
            "table_memory_update": table_memory_update,
            "carry_over_packets": carry_over_packets,
            "user_notes": user_notes,
        }
        await pause_check(task["run_id"])
        done_event = make_event(
            "table_discussion",
            f"{table_id} discussion completed",
            table_id=table_id,
            round_index=round_index,
            contribution_count=len(contributions),
            speeches_per_agent=speeches_per_agent,
        )
        emit_stream_event(done_event)
        return {
            "table_round_outputs": [output],
            "trace": [start_event, opening_event, *contribution_events, host_event, done_event],
        }

    return table_discussion


def _collect_round(state: WorldCafeState) -> dict[str, Any]:
    round_index = state["round_index"]
    outputs = [
        output for output in state["table_round_outputs"] if output["round_index"] == round_index
    ]
    updated_memories = dict(state["table_memories"])
    next_agent_pockets = dict(state.get("agent_pockets", {}))
    pocket_records: list[dict[str, Any]] = []
    host_openings: list[dict[str, Any]] = []
    question_seed_records: list[dict[str, Any]] = []
    table_summaries: dict[str, str] = {}
    for output in outputs:
        memory = dict(updated_memories[output["table_id"]])
        memory_update = dict(output.get("table_memory_update", {}))
        formatmemory_record = _normalize_formatmemory_record(
            memory_update.get("formatmemory") or memory_update,
            table_id=output["table_id"],
            question=output["question"],
            round_index=output["round_index"],
        )
        memory_update["formatmemory"] = formatmemory_record
        synthesis_summary = str(
            memory_update.get("synthesis")
            or _formatmemory_summary(formatmemory_record)
            or extract_section(output["synthesis"], "synthesis")
            or output["synthesis"]
        )
        memory["living_summary"] = synthesis_summary
        memory["key_insights"] = unique_append(memory["key_insights"], output["key_insights"])
        memory["open_questions"] = unique_append(memory["open_questions"], output["open_questions"])
        memory["tensions"] = unique_append(memory["tensions"], output["tensions"])
        memory["stable_patterns"] = unique_append(
            _string_list(memory.get("stable_patterns")),
            _string_list(memory_update.get("stable_patterns")),
        )
        memory["incomplete_or_weak_patterns"] = unique_append(
            _string_list(memory.get("incomplete_or_weak_patterns")),
            _string_list(memory_update.get("incomplete_or_weak_patterns")),
        )
        memory["contested_points"] = unique_append(
            _string_list(memory.get("contested_points")),
            _string_list(memory_update.get("contested_points")),
        )
        memory["blind_spots_or_ambiguities"] = unique_append(
            _string_list(memory.get("blind_spots_or_ambiguities")),
            _string_list(memory_update.get("blind_spots_or_ambiguities")),
        )
        memory["source_context_anchor"] = _string_list(memory_update.get("source_context_anchor"))
        memory["cumulative_pattern_evolution"] = str(
            memory_update.get("cumulative_pattern_evolution")
            or memory.get("cumulative_pattern_evolution")
            or ""
        )
        memory["recurring_patterns_across_rounds"] = unique_append(
            _string_list(memory.get("recurring_patterns_across_rounds")),
            _string_list(memory_update.get("recurring_patterns_across_rounds")),
        )
        memory["emerging_or_fading_signals"] = unique_append(
            _string_list(memory.get("emerging_or_fading_signals")),
            _string_list(memory_update.get("emerging_or_fading_signals")),
        )
        memory["unresolved_tensions_over_time"] = unique_append(
            _string_list(memory.get("unresolved_tensions_over_time")),
            _string_list(memory_update.get("unresolved_tensions_over_time")),
        )
        memory["round_pattern_delta"] = str(memory_update.get("round_pattern_delta") or "")
        memory["next_round_question_seeds"] = _string_list(memory_update.get("next_round_question_seeds"))
        memory["formatmemory"] = [
            *_formatmemory_list(memory.get("formatmemory")),
            formatmemory_record,
        ]
        memory["rounds"] = [
            *memory["rounds"],
            {
                "round_index": output["round_index"],
                "agent_ids": output["agent_ids"],
                "host_opening": output.get("host_opening", ""),
                "synthesis": output["synthesis"],
                "key_insights": output["key_insights"],
                "open_questions": output["open_questions"],
                "tensions": output["tensions"],
                "table_memory_update": memory_update,
                "carry_over_packets": output.get("carry_over_packets", []),
                "user_notes": output.get("user_notes", []),
            },
        ]
        updated_memories[output["table_id"]] = memory
        table_summaries[output["table_id"]] = synthesis_summary
        host_openings.append(
            {
                "table_id": output["table_id"],
                "round_index": output["round_index"],
                "host_opening": output.get("host_opening", ""),
            }
        )
        question_seed_records.append(
            {
                "table_id": output["table_id"],
                "round_index": output["round_index"],
                "question_seeds": memory["next_round_question_seeds"],
            }
        )
        for packet in output.get("carry_over_packets", []):
            agent_id = packet.get("agent_id")
            if not agent_id:
                continue
            next_agent_pockets[str(agent_id)] = packet
            pocket_records.append(dict(packet))

    event = make_event(
        "round_collected",
        f"round {round_index + 1} collected",
        round_index=round_index,
        table_count=len(outputs),
    )
    emit_stream_event(event)
    return {
        "stage": "round_collected",
        "table_memories": updated_memories,
        "agent_pockets": next_agent_pockets,
        "pocket_history": pocket_records,
        "host_openings": host_openings,
        "question_seed_history": question_seed_records,
        "round_summaries": [
            {
                "round_index": round_index,
                "tables": table_summaries,
            }
        ],
        "trace": [event],
    }


def _route_after_collect(state: WorldCafeState) -> Literal["rotate_agents", "global_harvest"]:
    if state["round_index"] + 1 < state["max_rounds"]:
        return "rotate_agents"
    return "global_harvest"


def _rotate_agents(state: WorldCafeState) -> dict[str, Any]:
    next_assignments = rotate_non_hosts(state["assignments"], state["hosts"])
    next_round = state["round_index"] + 1
    packet_routes = {
        packet.get("agent_id"): {
            "from_table": packet.get("from_table"),
            "to_table": packet.get("to_table"),
            "after_round": packet.get("after_round"),
        }
        for packet in state.get("agent_pockets", {}).values()
        if packet.get("agent_id")
    }
    rotation_record = {
        "after_round_index": state["round_index"],
        "next_round_index": next_round,
        "assignments": next_assignments,
        "packet_routes": packet_routes,
    }
    event = make_event(
        "rotation",
        f"agents rotated for round {next_round + 1}",
        **rotation_record,
    )
    emit_stream_event(event)
    return {
        "stage": "rotation",
        "assignments": next_assignments,
        "round_index": next_round,
        "rotation_history": [rotation_record],
        "trace": [event],
    }


def _make_global_harvest_node(llm: CafeLLM):
    async def global_harvest(state: WorldCafeState) -> dict[str, Any]:
        start_event = make_event("harvest", "global harvest started", round_count=state["max_rounds"])
        emit_stream_event(start_event)
        system, user = global_harvest_prompt(state["table_memories"], state["round_summaries"])
        content = await llm.agenerate(system, user)
        structured_harvest = _parse_structured_harvest(content)
        harvest = {
            "content": _harvest_display_content(content, structured_harvest),
            "raw_content": content,
            "structured_harvest": structured_harvest,
            "table_memories": state["table_memories"],
            "round_summaries": state["round_summaries"],
            "rotation_history": state["rotation_history"],
        }
        done_event = make_event("done", "world cafe completed", run_id=state["run_id"])
        emit_stream_event(done_event)
        return {
            "stage": "done",
            "harvest": harvest,
            "trace": [start_event, done_event],
        }

    return global_harvest


def _parse_structured_harvest(content: str) -> dict[str, Any]:
    try:
        data = loads_jsonish_object(content)
    except Exception:
        return {
            "pattern_channel": extract_bullets(extract_section(content, "Shared Patterns")),
            "weak_signal_channel": extract_bullets(extract_section(content, "Weak Signals")),
            "cross_table_tensions": extract_bullets(extract_section(content, "Cross-table Tensions")),
            "opportunity_hypotheses": [],
            "reframed_design_questions": extract_bullets(extract_section(content, "Reframed Questions")),
            "next_learning_experiments": extract_bullets(extract_section(content, "Next Experiments")),
        }
    return {
        "pattern_channel": data.get("pattern_channel") or data.get("shared_patterns") or data.get("cross_table_patterns") or [],
        "weak_signal_channel": data.get("weak_signal_channel") or data.get("weak_signals") or data.get("rare_but_promising_signals") or [],
        "cross_table_tensions": data.get("cross_table_tensions") or data.get("tensions") or data.get("unresolved_system_tensions") or [],
        "opportunity_hypotheses": data.get("opportunity_hypotheses") or data.get("opportunities") or [],
        "reframed_design_questions": data.get("reframed_design_questions") or data.get("reframed_questions") or [],
        "next_learning_experiments": data.get("next_learning_experiments") or data.get("next_experiments") or [],
        "display_markdown": str(data.get("display_markdown") or data.get("markdown") or ""),
    }


def _harvest_display_content(content: str, structured_harvest: dict[str, Any]) -> str:
    display = str(structured_harvest.get("display_markdown") or "").strip()
    if display:
        return emphasize_design_opportunities(display)
    try:
        loads_jsonish_object(content)
    except Exception:
        return emphasize_design_opportunities(content)
    if not _has_harvest_content(structured_harvest):
        return emphasize_design_opportunities(content)
    return emphasize_design_opportunities(_format_structured_harvest_markdown(structured_harvest))


def _has_harvest_content(harvest: dict[str, Any]) -> bool:
    keys = (
        "pattern_channel",
        "weak_signal_channel",
        "cross_table_tensions",
        "opportunity_hypotheses",
        "reframed_design_questions",
        "next_learning_experiments",
    )
    return any(bool(harvest.get(key)) for key in keys)


def _format_structured_harvest_markdown(harvest: dict[str, Any]) -> str:
    return "\n\n".join(
        [
            "## Shared Patterns\n" + _markdown_items(harvest.get("pattern_channel")),
            "## Weak Signals\n" + _markdown_items(harvest.get("weak_signal_channel")),
            "## Cross-table Tensions\n" + _markdown_items(harvest.get("cross_table_tensions")),
            "## Reframed Questions\n" + _markdown_items(harvest.get("reframed_design_questions")),
            "## Next Experiments\n" + _markdown_items(harvest.get("next_learning_experiments")),
        ]
    )


def _markdown_items(value: object) -> str:
    if not value:
        return "- 暂无"
    if isinstance(value, list):
        return "\n".join(f"- {_compact_item(item)}" for item in value)
    return f"- {_compact_item(value)}"


def _compact_item(value: object) -> str:
    if isinstance(value, dict):
        preferred_keys = (
            "pattern",
            "signal",
            "tension",
            "hypothesis",
            "experiment",
            "question",
            "possible_reframe",
        )
        for key in preferred_keys:
            if value.get(key):
                return str(value[key])
        return str(value)
    return str(value)


def _host_opening_display(raw_opening: str) -> str:
    opening = extract_section(raw_opening, "opening") or raw_opening
    return emphasize_design_opportunities(opening.strip())


def _limit_visible_text(text: str, limit: int) -> str:
    normalized = str(text or "").strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip()


def _host_memory_snapshot(memory: TableMemory, update: dict[str, Any] | None = None) -> dict[str, Any]:
    update = update or {}
    current = _normalize_formatmemory_record(
        update.get("formatmemory") or update or (memory.get("formatmemory") or [{}])[-1],
        table_id=str(memory.get("table_id") or ""),
        question=str(memory.get("question") or ""),
        round_index=None,
    )
    rounds = memory.get("rounds", [])
    recent_rounds = []
    for item in rounds[-3:]:
        round_update = item.get("table_memory_update") or {}
        record = _normalize_formatmemory_record(
            round_update.get("formatmemory") or round_update,
            table_id=str(memory.get("table_id") or ""),
            question=str(memory.get("question") or ""),
            round_index=item.get("round_index"),
        )
        recent_rounds.append(
            {
                "round": int(item.get("round_index", 0)) + 1,
                "synthesis": _limit_visible_text(_formatmemory_summary(record), 160),
                "repeated_themes": _string_list(record.get("repeated_themes"))[:3],
                "minority_inspiring_views": _string_list(record.get("minority_inspiring_views"))[:3],
                "unresolved_tensions": _string_list(record.get("unresolved_tensions"))[:3],
            }
        )
    key_insights = unique_append(
        _string_list(current.get("repeated_themes")),
        _string_list(current.get("minority_inspiring_views")),
    )
    return {
        "kind": "table_host",
        "living_summary": _limit_visible_text(
            str(update.get("synthesis") or _formatmemory_summary(current) or memory.get("living_summary") or "暂无。"),
            180,
        ),
        "formatmemory": current,
        "key_insights": key_insights[:4],
        "open_questions": (
            _string_list(update.get("next_round_question_seeds"))
            or _string_list(memory.get("next_round_question_seeds"))
        )[:4],
        "tensions": _string_list(current.get("unresolved_tensions"))[:4],
        "stable_patterns": _string_list(current.get("repeated_themes"))[:4],
        "incomplete_or_weak_patterns": _string_list(current.get("minority_inspiring_views"))[:4],
        "recurring_patterns_across_rounds": _string_list(current.get("repeated_themes"))[:4],
        "emerging_or_fading_signals": _string_list(current.get("minority_inspiring_views"))[:4],
        "unresolved_tensions_over_time": _string_list(current.get("unresolved_tensions"))[:4],
        "round_pattern_delta": _limit_visible_text(_formatmemory_summary(current), 180),
        "next_round_question_seeds": (
            _string_list(update.get("next_round_question_seeds"))
            or _string_list(memory.get("next_round_question_seeds"))
        )[:4],
        "recent_rounds": recent_rounds,
    }


def _speaker_memory_snapshot(
    *,
    agent: AgentProfile,
    carry_over_packet: CarryOverPacket | dict[str, Any] | None,
) -> dict[str, Any]:
    packet = dict(carry_over_packet or {})
    agent_memory = packet.get("agent_generated_memory")
    return {
        "kind": "speaking_agent",
        "bridge_intent": _limit_visible_text(_bridge_intent_from_memory(agent_memory) or "暂无迁移记忆。", 180),
        "agent_generated_memory": _compact_memory_value(agent_memory),
    }


def _compact_memory_value(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): _limit_visible_text(str(item), 160)
            for key, item in list(value.items())[:6]
            if item not in (None, "")
        }
    if isinstance(value, list):
        return [_limit_visible_text(str(item), 120) for item in value[:6]]
    if isinstance(value, str):
        return _limit_visible_text(value, 180)
    return ""


def _format_host_record_display(memory_update: dict[str, Any], fallback: str) -> str:
    formatmemory = _normalize_formatmemory_record(memory_update.get("formatmemory") or memory_update)
    if _has_formatmemory_content(formatmemory):
        sections: list[str] = []
        repeated = _natural_list(formatmemory.get("repeated_themes"))
        if repeated:
            sections.append("## 重复主题\n" + _markdown_items(repeated))
        minority = _natural_list(formatmemory.get("minority_inspiring_views"))
        if minority:
            sections.append("## 少数启发\n" + _markdown_items(minority))
        tensions = _natural_list(formatmemory.get("unresolved_tensions"))
        if tensions:
            sections.append("## 未解张力\n" + _markdown_items(tensions))
        seeds = _natural_list(memory_update.get("next_round_question_seeds"))
        if seeds:
            sections.append("## 带走\n" + _markdown_items(seeds))
        display = "\n\n".join(sections).strip()
        if display:
            return emphasize_design_opportunities(display)

    sections: list[str] = []
    key_insights = _natural_list(memory_update.get("key_insights"))
    if key_insights:
        sections.append("## 洞察关键词\n" + _markdown_items(key_insights))

    stable_patterns = _natural_list(memory_update.get("stable_patterns"))
    if stable_patterns:
        sections.append("## 暂时成形\n" + _markdown_items(stable_patterns))

    weak_patterns = _natural_list(memory_update.get("incomplete_or_weak_patterns"))
    if weak_patterns:
        sections.append("## 仍不完善\n" + _markdown_items(weak_patterns))

    contested_points = _natural_list(memory_update.get("contested_points"))
    if contested_points:
        sections.append("## 冲突观点\n" + _markdown_items(contested_points))

    tensions = _natural_list(memory_update.get("tensions"))
    if tensions:
        sections.append("## 张力关键词\n" + _markdown_items(tensions))

    blind_spots = _natural_list(memory_update.get("blind_spots_or_ambiguities"))
    if blind_spots:
        sections.append("## 盲点/模糊处\n" + _markdown_items(blind_spots))

    cumulative_evolution = _natural_text(memory_update.get("cumulative_pattern_evolution"))
    if cumulative_evolution:
        sections.append("## 跨轮演化\n" + cumulative_evolution)

    recurring_patterns = _natural_list(memory_update.get("recurring_patterns_across_rounds"))
    if recurring_patterns:
        sections.append("## 跨轮重复模式\n" + _markdown_items(recurring_patterns))

    emerging_signals = _natural_list(memory_update.get("emerging_or_fading_signals"))
    if emerging_signals:
        sections.append("## 变化中的信号\n" + _markdown_items(emerging_signals))

    unresolved_over_time = _natural_list(memory_update.get("unresolved_tensions_over_time"))
    if unresolved_over_time:
        sections.append("## 持续未解张力\n" + _markdown_items(unresolved_over_time))

    pattern_delta = _natural_text(memory_update.get("round_pattern_delta"))
    if pattern_delta:
        sections.append("## 本轮差异\n" + pattern_delta)

    open_questions = _natural_list(memory_update.get("open_questions"))
    if open_questions:
        sections.append("## 未完成问题\n" + _markdown_items(open_questions))

    synthesis = _natural_text(memory_update.get("synthesis"))
    if not synthesis:
        synthesis = _natural_text(extract_section(fallback, "synthesis"))
    if not sections and not synthesis and not _looks_structured(fallback):
        synthesis = _natural_text(fallback)
    if not sections and synthesis:
        sections.append(synthesis)

    display = "\n\n".join(sections).strip() or "桌长已更新本桌记忆：本轮讨论先保留为内部结构化记录，下一轮将继续围绕这些线索追问。"
    return emphasize_design_opportunities(display)


def _format_host_closing_display(content: str, memory_update: dict[str, Any], fallback: str) -> str:
    text = str(content or "").strip()
    internal_tokens = (
        "formatmemory",
        "repeated_themes",
        "minority_inspiring_views",
        "unresolved_tensions",
        "host_memory_update_instruction",
        "llm_generated_table_memory_template",
        "host_generated_table_memory",
        "source_context_anchor",
        "stable_patterns",
        "incomplete_or_weak_patterns",
        "contested_points",
        "blind_spots_or_ambiguities",
    )
    if not text or _looks_structured(text) or any(token in text for token in internal_tokens):
        return _format_host_record_display(memory_update, fallback)
    return emphasize_design_opportunities(text)


def _natural_list(value: object) -> list[str]:
    return [item for item in (_natural_text(item) for item in _string_list(value)) if item]


def _natural_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return ""
    text = str(value).strip()
    if not text or _looks_structured(text):
        return ""
    blocked_tokens = (
        "formatmemory",
        "repeated_themes",
        "minority_inspiring_views",
        "unresolved_tensions",
        "host_memory_update_instruction",
        "llm_generated_table_memory_template",
        "host_generated_table_memory",
        "source_context_anchor",
        "cumulative_pattern_evolution",
        "recurring_patterns_across_rounds",
        "emerging_or_fading_signals",
        "unresolved_tensions_over_time",
        "round_pattern_delta",
        "next_round_question_seeds",
        "key_insights",
        "open_questions",
        "tensions",
        "stable_patterns",
        "incomplete_or_weak_patterns",
        "contested_points",
        "blind_spots_or_ambiguities",
    )
    for token in blocked_tokens:
        text = text.replace(token, "")
    return text.strip(" \n\r\t:：,，")


def _looks_structured(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.startswith(("{", "[")):
        return True
    return any(f'"{token}"' in stripped for token in (
        "formatmemory",
        "repeated_themes",
        "minority_inspiring_views",
        "unresolved_tensions",
        "synthesis",
        "host_memory_update_instruction",
        "llm_generated_table_memory_template",
        "host_generated_table_memory",
    ))

def _empty_table_memory(table_id: str, question: str, host_id: str) -> TableMemory:
    return {
        "table_id": table_id,
        "question": question,
        "host_id": host_id,
        "living_summary": "",
        "key_insights": [],
        "open_questions": [],
        "tensions": [],
        "stable_patterns": [],
        "incomplete_or_weak_patterns": [],
        "contested_points": [],
        "blind_spots_or_ambiguities": [],
        "formatmemory": [],
        "rounds": [],
        "cumulative_pattern_evolution": "",
        "recurring_patterns_across_rounds": [],
        "emerging_or_fading_signals": [],
        "unresolved_tensions_over_time": [],
    }


def _normalize_table_specs(
    table_questions: dict[str, str],
    table_specs: dict[str, TableSpec] | None,
) -> dict[str, TableSpec]:
    normalized: dict[str, TableSpec] = {}
    for table_id, question in table_questions.items():
        raw = dict((table_specs or {}).get(table_id, {}))
        spec = _default_table_spec(table_id, question)
        spec.update({key: value for key, value in raw.items() if value not in (None, "")})
        spec["table_id"] = table_id
        spec["question"] = question
        spec["guiding_question"] = str(spec.get("guiding_question") or question)
        spec["round_subquestions"] = _round_subquestions(spec.get("round_subquestions"))
        normalized[table_id] = spec
    return normalized


def _default_table_spec(table_id: str, question: str) -> TableSpec:
    return {
        "table_id": table_id,
        "question": question,
        "expert_skill": "mixed",
        "expert_rationale": "默认混合专家视角；facilitator 未提供具体 expert-skill routing。",
        "lens": "reframing",
        "guiding_question": question,
        "why_this_matters": "该问题用于启动开放、可迁移的 World Cafe 小桌讨论。",
        "evidence_basis": [],
        "avoid_solution_bias": "不要直接提出解决方案，优先探索问题条件、张力和重构方向。",
        "round_subquestions": {
            "round_1": ["本桌问题中有哪些值得先观察的真实现象？"],
            "round_2": ["上一轮观察之间出现了哪些连接、分歧或张力？"],
            "round_3": ["这些张力是否提示我们需要重构原问题？"],
        },
    }


def _round_subquestions(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        value = {}
    return {
        "round_1": _string_list(value.get("round_1")) or ["本桌问题中有哪些值得先观察的真实现象？"],
        "round_2": _string_list(value.get("round_2")) or ["上一轮观察之间出现了哪些连接、分歧或张力？"],
        "round_3": _string_list(value.get("round_3")) or ["这些张力是否提示我们需要重构原问题？"],
    }


def _next_table_by_agent(state: WorldCafeState) -> dict[str, str]:
    next_assignments = rotate_non_hosts(state["assignments"], state["hosts"])
    result: dict[str, str] = {}
    for table_id, agent_ids in next_assignments.items():
        host_id = state["hosts"][table_id]
        for agent_id in agent_ids:
            if agent_id != host_id:
                result[agent_id] = table_id
    return result


def _normalize_formatmemory_record(
    value: object,
    *,
    table_id: str = "",
    question: str = "",
    round_index: object = None,
) -> dict[str, Any]:
    if isinstance(value, list):
        value = value[-1] if value else {}
    if not isinstance(value, dict):
        value = {}
    raw = value.get("formatmemory")
    if isinstance(raw, list):
        raw = raw[-1] if raw else {}
    if isinstance(raw, dict):
        source = {**value, **raw}
    else:
        source = value
    stored_round = source.get("round_index", round_index)
    if isinstance(stored_round, int) and stored_round == round_index:
        stored_round = stored_round + 1
    return {
        "table_id": str(source.get("table_id") or table_id or "").strip(),
        "table_question": str(
            source.get("table_question")
            or source.get("question")
            or question
            or ""
        ).strip(),
        "round_index": stored_round,
        "repeated_themes": _string_list(
            source.get("repeated_themes")
            or source.get("table_question_recurring_themes")
            or source.get("stable_patterns")
            or source.get("recurring_patterns_across_rounds")
            or source.get("key_insights")
        ),
        "minority_inspiring_views": _string_list(
            source.get("minority_inspiring_views")
            or source.get("minority_views")
            or source.get("minority_but_inspiring_views")
            or source.get("incomplete_or_weak_patterns")
            or source.get("emerging_or_fading_signals")
        ),
        "unresolved_tensions": _string_list(
            source.get("unresolved_tensions")
            or source.get("unresolved_tensions_over_time")
            or source.get("tensions")
        ),
    }


def _formatmemory_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _has_formatmemory_content(record: dict[str, Any]) -> bool:
    return bool(
        record.get("repeated_themes")
        or record.get("minority_inspiring_views")
        or record.get("unresolved_tensions")
    )


def _formatmemory_summary(record: dict[str, Any]) -> str:
    parts: list[str] = []
    repeated = _string_list(record.get("repeated_themes"))
    minority = _string_list(record.get("minority_inspiring_views"))
    tensions = _string_list(record.get("unresolved_tensions"))
    if repeated:
        parts.append("重复主题：" + "；".join(repeated[:3]))
    if minority:
        parts.append("少数启发：" + "；".join(minority[:3]))
    if tensions:
        parts.append("未解张力：" + "；".join(tensions[:3]))
    return " | ".join(parts)


def _parse_host_memory_update(content: str) -> dict[str, Any]:
    try:
        data = loads_jsonish_object(content)
    except Exception:
        data = {}
    if data:
        record = _normalize_formatmemory_record(data.get("formatmemory") or data)
        synthesis = str(data.get("synthesis") or _formatmemory_summary(record) or "")
        key_insights = unique_append(
            _string_list(record.get("repeated_themes")),
            _string_list(record.get("minority_inspiring_views")),
        )
        next_round_question_seeds = _string_list(data.get("next_round_question_seeds") or data.get("open_questions"))
        return {
            "synthesis": synthesis,
            "formatmemory": record,
            "key_insights": key_insights,
            "stable_patterns": _string_list(record.get("repeated_themes")),
            "incomplete_or_weak_patterns": _string_list(record.get("minority_inspiring_views")),
            "contested_points": [],
            "open_questions": next_round_question_seeds,
            "tensions": _string_list(record.get("unresolved_tensions")),
            "blind_spots_or_ambiguities": [],
            "source_context_anchor": _string_list(data.get("source_context_anchor")),
            "cumulative_pattern_evolution": synthesis,
            "recurring_patterns_across_rounds": _string_list(record.get("repeated_themes")),
            "emerging_or_fading_signals": _string_list(record.get("minority_inspiring_views")),
            "unresolved_tensions_over_time": _string_list(record.get("unresolved_tensions")),
            "round_pattern_delta": synthesis,
            "next_round_question_seeds": next_round_question_seeds,
        }
    synthesis = extract_section(content, "synthesis") or content
    key_insights = extract_bullets(extract_section(content, "key_insights"))
    open_questions = extract_bullets(extract_section(content, "open_questions"))
    tensions = extract_bullets(extract_section(content, "tensions"))
    record = {
        "table_question": "",
        "round_index": None,
        "repeated_themes": key_insights,
        "minority_inspiring_views": [],
        "unresolved_tensions": tensions,
    }
    return {
        "synthesis": _formatmemory_summary(record) or synthesis,
        "formatmemory": record,
        "key_insights": key_insights,
        "stable_patterns": key_insights,
        "incomplete_or_weak_patterns": [],
        "contested_points": [],
        "open_questions": open_questions,
        "tensions": tensions,
        "blind_spots_or_ambiguities": open_questions,
        "source_context_anchor": [],
        "cumulative_pattern_evolution": _formatmemory_summary(record) or synthesis,
        "recurring_patterns_across_rounds": key_insights,
        "emerging_or_fading_signals": [],
        "unresolved_tensions_over_time": tensions,
        "round_pattern_delta": _formatmemory_summary(record) or synthesis,
        "next_round_question_seeds": open_questions[:3],
    }


def _fallback_host_synthesis(contributions: list[dict[str, Any]], error_message: str) -> str:
    snippets = [str(item.get("content") or "").strip() for item in contributions if str(item.get("content") or "").strip()]
    first_snippet = snippets[0][:160] if snippets else "本轮没有可用发言。"
    return json.dumps(
        {
            "formatmemory": {
                "table_question": "",
                "round_index": None,
                "repeated_themes": [first_snippet],
                "minority_inspiring_views": [],
                "unresolved_tensions": [f"桌长 formatmemory 生成失败：{error_message[:160]}"],
            },
            "next_round_question_seeds": ["下一轮需要回到本桌问题，继续确认哪些观点可被证据支持。"],
        },
        ensure_ascii=False,
    )


def _fallback_agent_packet_content(
    *,
    agent: AgentProfile,
    agent_contributions: list[str],
    error_message: str,
) -> str:
    personal_takeaway = next((item.strip() for item in agent_contributions if item.strip()), "")
    if not personal_takeaway:
        personal_takeaway = f"{agent['name']} 本轮没有形成可用发言。"
    return json.dumps(
        {
            "agent": {
                "id": agent["id"],
                "name": agent["name"],
                "role": agent.get("role", ""),
                "skills": agent.get("skills", []),
            },
            "agent_generated_memory": {
                "skill_lens": "、".join(agent.get("skills", [])) or agent.get("role", ""),
                "personal_insight": personal_takeaway[:220],
                "carry_forward_question": "这个个人洞见在下一桌任务里是否仍然成立？",
            },
            "generation_error": error_message[:160],
        },
        ensure_ascii=False,
    )


async def _generate_carry_over_packets(
    *,
    llm: CafeLLM,
    participants: list[AgentProfile],
    contributions: list[dict[str, Any]],
    table_id: str,
    round_index: int,
    memory_update: dict[str, Any],
    fallback_memory: TableMemory,
    next_table_by_agent: dict[str, str],
    all_table_questions: dict[str, str],
) -> list[CarryOverPacket]:
    if not next_table_by_agent:
        return []
    contributions_by_agent = _contributions_by_agent(contributions)
    packets: list[CarryOverPacket] = []
    for agent in participants:
        to_table = next_table_by_agent.get(agent["id"])
        if not to_table:
            continue
        to_question = all_table_questions.get(to_table) or to_table
        system, user = carry_over_packet_prompt(
            agent=agent,
            from_table=table_id,
            to_table=to_table,
            after_round=round_index,
            from_memory=fallback_memory,
            to_question=to_question,
            agent_contributions=contributions_by_agent.get(agent["id"], []),
        )
        generation_error: str | None = None
        try:
            content = await llm.agenerate(system, user)
        except Exception as exc:
            generation_error = str(exc) or repr(exc)
            content = _fallback_agent_packet_content(
                agent=agent,
                agent_contributions=contributions_by_agent.get(agent["id"], []),
                error_message=generation_error,
            )
        packet = _parse_packet_response(
            content=content,
            agent_id=agent["id"],
            from_table=table_id,
            to_table=to_table,
            after_round=round_index,
        )
        if generation_error:
            packet["generation_error"] = generation_error
        packets.append(packet)
    return packets


def _parse_packet_response(
    *,
    content: str,
    agent_id: str,
    from_table: str,
    to_table: str,
    after_round: int,
) -> CarryOverPacket:
    try:
        data = loads_jsonish_object(content)
    except Exception:
        data = {
            "agent_generated_memory": {
                "personal_insight": content,
                "carry_forward_question": "这个个人洞见在下一桌任务里是否仍然成立？",
            },
            "bridge_intent": "把上一桌个人洞见带到下一桌任务中测试。",
        }
    agent = data.get("agent") if isinstance(data.get("agent"), dict) else {}
    agent_memory = data.get("agent_generated_memory") or {}
    return {
        "agent_id": agent_id,
        "agent": {
            "id": str(agent.get("id") or agent_id),
            "name": str(agent.get("name") or agent_id),
            "role": str(agent.get("role") or ""),
            "skills": _string_list(agent.get("skills")),
        },
        "from_table": from_table,
        "to_table": to_table,
        "after_round": after_round,
        "agent_generated_memory": agent_memory,
    }


def _bridge_intent_from_memory(agent_memory: object) -> str:
    if isinstance(agent_memory, dict):
        question = str(agent_memory.get("carry_forward_question") or "").strip()
        insight = str(
            agent_memory.get("personal_insight")
            or agent_memory.get("personal_takeaway")
            or ""
        ).strip()
        if question:
            return f"带着个人洞察进入下一桌，测试：{question}"
        if insight:
            return f"带着这个个人洞察进入下一桌继续测试：{insight[:80]}"
    if isinstance(agent_memory, str) and agent_memory.strip():
        return f"带着这个个人洞察进入下一桌继续测试：{agent_memory.strip()[:80]}"
    return ""


def _contributions_by_agent(contributions: list[dict[str, Any]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in contributions:
        result.setdefault(str(item.get("agent_id")), []).append(str(item.get("content") or ""))
    return result


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dict_or_empty(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _ensure_agent_profiles(
    agents: list[AgentProfile] | None,
    required_count: int,
    referenced_ids: set[str],
) -> list[AgentProfile]:
    agent_profiles = list(agents or build_default_agent_profiles(required_count))
    existing_ids = {agent["id"] for agent in agent_profiles}
    target_count = max(required_count, len(agent_profiles), _largest_default_agent_index(referenced_ids))
    for default_agent in build_default_agent_profiles(target_count + len(agent_profiles)):
        if len(agent_profiles) >= target_count and referenced_ids.issubset(existing_ids):
            break
        if default_agent["id"] in existing_ids:
            continue
        agent_profiles.append(default_agent)
        existing_ids.add(default_agent["id"])
    missing = referenced_ids.difference(existing_ids)
    if missing:
        raise ValueError(f"unknown agent ids in assignments: {', '.join(sorted(missing))}")
    return agent_profiles


def _largest_default_agent_index(agent_ids: set[str]) -> int:
    largest = 0
    for agent_id in agent_ids:
        prefix, _, suffix = agent_id.partition("_")
        if prefix == "agent" and suffix.isdigit():
            largest = max(largest, int(suffix))
    return largest


def _normalize_initial_assignments(
    *,
    assignments: dict[str, list[str]],
    hosts: dict[str, str],
    table_ids: list[str],
    valid_agent_ids: set[str],
) -> tuple[dict[str, list[str]], dict[str, str]]:
    normalized_assignments: dict[str, list[str]] = {}
    normalized_hosts: dict[str, str] = {}
    for table_id in table_ids:
        host_id = hosts.get(table_id)
        if not host_id:
            raise ValueError(f"missing host for {table_id}")
        if host_id not in valid_agent_ids:
            raise ValueError(f"unknown host id for {table_id}: {host_id}")
        speakers = [agent_id for agent_id in assignments.get(table_id, []) if agent_id != host_id]
        if not speakers:
            raise ValueError(f"{table_id} must have at least one speaking agent")
        unknown = [agent_id for agent_id in speakers if agent_id not in valid_agent_ids]
        if unknown:
            raise ValueError(f"unknown speaker ids for {table_id}: {', '.join(unknown)}")
        deduped_speakers = list(dict.fromkeys(speakers))
        normalized_hosts[table_id] = host_id
        normalized_assignments[table_id] = [host_id, *deduped_speakers]
    return normalized_assignments, normalized_hosts
