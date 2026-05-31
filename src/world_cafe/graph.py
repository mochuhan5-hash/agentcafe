from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from world_cafe.llm import CafeLLM
from world_cafe.parsing import extract_bullets, extract_section, unique_append
from world_cafe.profiles import build_default_agent_profiles, normalize_questions
from world_cafe.prompts import contribution_prompt, global_harvest_prompt, host_synthesis_prompt
from world_cafe.rotation import build_initial_assignments, rotate_non_hosts
from world_cafe.state import AgentProfile, TableMemory, TableRoundOutput, WorldCafeState
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
    assignments: dict[str, list[str]] | None = None,
    hosts: dict[str, str] | None = None,
    run_id: str | None = None,
) -> WorldCafeState:
    table_questions = normalize_questions(questions, table_count=table_count)
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
        "background_context": background_context,
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
        "table_round_outputs": [],
        "round_summaries": [],
        "rotation_history": [],
        "trace": [],
        "warnings": [],
    }


PauseCheck = Callable[[str], Awaitable[None]]


async def _no_pause_check(_run_id: str) -> None:
    return None


def build_world_cafe_graph(llm: CafeLLM, pause_check: PauseCheck | None = None):
    pause_check = pause_check or _no_pause_check
    builder = StateGraph(WorldCafeState)
    builder.add_node("setup", _setup)
    builder.add_node("begin_round", _begin_round)
    builder.add_node("table_discussion", _make_table_discussion_node(llm, pause_check))
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
    for table_id in sorted(state["table_questions"]):
        sends.append(
            Send(
                "table_discussion",
                {
                    "run_id": state["run_id"],
                    "round_index": state["round_index"],
                    "table_id": table_id,
                    "question": state["table_questions"][table_id],
                    "agent_profiles": state["agent_profiles"],
                    "agent_ids": state["assignments"][table_id],
                    "host_id": state["hosts"][table_id],
                    "memory": state["table_memories"][table_id],
                    "speeches_per_agent": state.get("speeches_per_agent", 3),
                    "background_context": state.get("background_context", ""),
                },
            )
        )
    return sends


def _make_table_discussion_node(llm: CafeLLM, pause_check: PauseCheck):
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
        background_context = str(task.get("background_context", ""))
        speeches_per_agent = int(task.get("speeches_per_agent", 3))
        contributions: list[dict[str, Any]] = []
        contribution_events: list[dict[str, Any]] = []
        conversation: list[str] = []

        async def ask_agent(agent: AgentProfile, turn_index: int, cycle_index: int) -> dict[str, Any]:
            system, user = contribution_prompt(
                table_id=table_id,
                question=task["question"],
                round_index=round_index,
                agent=agent,
                table_agents=table_agents,
                memory=memory,
                conversation=conversation,
                background_context=background_context,
                turn_index=turn_index,
                cycle_index=cycle_index,
            )
            content = await llm.agenerate(system, user)
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
                contribution = await ask_agent(agent, turn_index, cycle_index)
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
                )
                contribution_events.append(event)
                emit_stream_event(event)

        host = profile_by_id[task["host_id"]]
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
            contributions=synthesis_inputs,
            background_context=background_context,
        )
        synthesis = await llm.agenerate(system, user)
        output: TableRoundOutput = {
            "table_id": table_id,
            "question": task["question"],
            "round_index": round_index,
            "host_id": task["host_id"],
            "agent_ids": task["agent_ids"],
            "contributions": contributions,
            "synthesis": synthesis,
            "key_insights": extract_bullets(extract_section(synthesis, "key_insights")),
            "open_questions": extract_bullets(extract_section(synthesis, "open_questions")),
            "tensions": extract_bullets(extract_section(synthesis, "tensions")),
        }
        host_event = make_event(
            "host_record",
            f"{table_id} host record updated",
            table_id=table_id,
            round_index=round_index,
            host_id=task["host_id"],
            host_name=host["name"],
            content=synthesis,
            key_insights=output["key_insights"],
            open_questions=output["open_questions"],
            tensions=output["tensions"],
        )
        emit_stream_event(host_event)
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
            "trace": [start_event, *contribution_events, host_event, done_event],
        }

    return table_discussion


def _collect_round(state: WorldCafeState) -> dict[str, Any]:
    round_index = state["round_index"]
    outputs = [
        output for output in state["table_round_outputs"] if output["round_index"] == round_index
    ]
    updated_memories = dict(state["table_memories"])
    table_summaries: dict[str, str] = {}
    for output in outputs:
        memory = dict(updated_memories[output["table_id"]])
        synthesis_summary = extract_section(output["synthesis"], "synthesis") or output["synthesis"]
        memory["living_summary"] = synthesis_summary
        memory["key_insights"] = unique_append(memory["key_insights"], output["key_insights"])
        memory["open_questions"] = unique_append(memory["open_questions"], output["open_questions"])
        memory["tensions"] = unique_append(memory["tensions"], output["tensions"])
        memory["rounds"] = [
            *memory["rounds"],
            {
                "round_index": output["round_index"],
                "agent_ids": output["agent_ids"],
                "synthesis": output["synthesis"],
                "key_insights": output["key_insights"],
                "open_questions": output["open_questions"],
                "tensions": output["tensions"],
            },
        ]
        updated_memories[output["table_id"]] = memory
        table_summaries[output["table_id"]] = synthesis_summary

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
    rotation_record = {
        "after_round_index": state["round_index"],
        "next_round_index": next_round,
        "assignments": next_assignments,
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
        harvest = {
            "content": content,
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

def _empty_table_memory(table_id: str, question: str, host_id: str) -> TableMemory:
    return {
        "table_id": table_id,
        "question": question,
        "host_id": host_id,
        "living_summary": "",
        "key_insights": [],
        "open_questions": [],
        "tensions": [],
        "rounds": [],
    }


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
