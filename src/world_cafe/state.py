from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict


TABLEMEMORY_USAGE_DESCRIPTION = (
    "既有 formatmemory 是本桌过去轮次的累计记忆，只用于识别延续、变化和重复。"
    "本轮输出的 formatmemory 只能新增 round_index = 当前轮次 的一条记录，不要改写过去轮次。"
)


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


class UserNote(TypedDict, total=False):
    id: str
    text: str
    table_id: str
    round_index: int
    speaker_name: str
    speaker_id: str
    speech_id: str
    speech_target_id: str
    highlight_count: int
    created_at: str


class TableSpec(TypedDict, total=False):
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
    agent_system_prompt: str


class CarryOverPacket(TypedDict, total=False):
    agent_id: str
    agent: dict[str, Any]
    from_table: str
    to_table: str
    after_round: int
    agent_generated_memory: dict[str, Any] | str


class TableMemory(TypedDict, total=False):
    table_id: str
    question: str
    host_id: str
    tablememory_usage_description: str
    formatmemory: list[dict[str, Any]]
    next_round_question_seeds: list[str]


class TableRoundOutput(TypedDict):
    table_id: str
    question: str
    table_spec: TableSpec
    round_index: int
    host_id: str
    agent_ids: list[str]
    contributions: list[AgentContribution]
    host_opening: str
    host_record_display: str
    synthesis: str
    table_memory_update: dict[str, Any]
    carry_over_packets: list[CarryOverPacket]
    user_notes: list[UserNote]


class TraceEvent(TypedDict):
    timestamp: str
    stage: str
    message: str
    metadata: dict[str, Any]


class WorldCafeState(TypedDict, total=False):
    run_id: str
    stage: Stage
    table_questions: dict[str, str]
    table_specs: dict[str, TableSpec]
    table_question_plan: dict[str, Any]
    expert_skill_routes: dict[str, Any]
    background_context: str
    source_context: str
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
    agent_pockets: dict[str, CarryOverPacket]
    pocket_history: Annotated[list[dict[str, Any]], operator.add]
    host_openings: Annotated[list[dict[str, Any]], operator.add]
    question_seed_history: Annotated[list[dict[str, Any]], operator.add]
    table_round_outputs: Annotated[list[TableRoundOutput], operator.add]
    round_summaries: Annotated[list[dict[str, Any]], operator.add]
    rotation_history: Annotated[list[dict[str, Any]], operator.add]
    harvest: dict[str, Any]
    trace: Annotated[list[TraceEvent], operator.add]
    warnings: Annotated[list[str], operator.add]
