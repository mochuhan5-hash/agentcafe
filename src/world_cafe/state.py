from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict


Stage = Literal[
    "setup",
    "round_started",
    "table_discussion",
    "round_collected",
    "rotation",
    "harvest",
    "done",
]


class AgentProfile(TypedDict):
    id: str
    name: str
    role: str
    skills: list[str]
    style: str


class AgentContribution(TypedDict):
    agent_id: str
    agent_name: str
    content: str
    turn_index: int
    cycle_index: int


class TableMemory(TypedDict):
    table_id: str
    question: str
    host_id: str
    living_summary: str
    key_insights: list[str]
    open_questions: list[str]
    tensions: list[str]
    rounds: list[dict[str, Any]]


class TableRoundOutput(TypedDict):
    table_id: str
    question: str
    round_index: int
    host_id: str
    agent_ids: list[str]
    contributions: list[AgentContribution]
    synthesis: str
    key_insights: list[str]
    open_questions: list[str]
    tensions: list[str]


class TraceEvent(TypedDict):
    timestamp: str
    stage: str
    message: str
    metadata: dict[str, Any]


class WorldCafeState(TypedDict, total=False):
    run_id: str
    stage: Stage
    table_questions: dict[str, str]
    background_context: str
    background_filename: str
    table_count: int
    seats_per_table: int
    speeches_per_agent: int
    max_rounds: int
    round_index: int
    agent_profiles: list[AgentProfile]
    assignments: dict[str, list[str]]
    hosts: dict[str, str]
    table_memories: dict[str, TableMemory]
    table_round_outputs: Annotated[list[TableRoundOutput], operator.add]
    round_summaries: Annotated[list[dict[str, Any]], operator.add]
    rotation_history: Annotated[list[dict[str, Any]], operator.add]
    harvest: dict[str, Any]
    trace: Annotated[list[TraceEvent], operator.add]
    warnings: Annotated[list[str], operator.add]
