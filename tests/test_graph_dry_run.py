import pytest

from world_cafe.graph import (
    _harvest_display_content,
    _parse_structured_harvest,
    build_world_cafe_graph,
    create_initial_state,
)
from world_cafe.llm import DryRunCafeLLM
from world_cafe.prompts import contribution_prompt, global_harvest_prompt, host_opening_prompt, host_synthesis_prompt
from world_cafe.state import TABLEMEMORY_USAGE_DESCRIPTION


@pytest.mark.asyncio
async def test_world_cafe_dry_run_completes_all_rounds() -> None:
    state = create_initial_state(
        questions=["q1", "q2", "q3", "q4"],
        rounds=2,
    )
    graph = build_world_cafe_graph(DryRunCafeLLM())

    final_state = await graph.ainvoke(state)

    assert final_state["stage"] == "done"
    assert len(final_state["table_round_outputs"]) == 8
    assert len(final_state["round_summaries"]) == 2
    assert len(final_state["rotation_history"]) == 1
    assert "Design Insights" in final_state["harvest"]["content"]
    assert "structured_harvest" in final_state["harvest"]
    assert "speaking_agent_history" in final_state["harvest"]
    assert "round_summaries" not in final_state["harvest"]
    for output in final_state["table_round_outputs"]:
        assert len(output["contributions"]) == 9
        assert output["host_id"] not in {item["agent_id"] for item in output["contributions"]}
        assert {item["cycle_index"] for item in output["contributions"]} == {0, 1, 2}
    for memory in final_state["table_memories"].values():
        assert len(memory["rounds"]) == 2


@pytest.mark.asyncio
async def test_discussion_uses_configured_speech_count_per_agent() -> None:
    state = create_initial_state(
        questions=["q1"],
        rounds=1,
        table_count=1,
        seats_per_table=3,
        speeches_per_agent=4,
    )
    graph = build_world_cafe_graph(DryRunCafeLLM())

    final_state = await graph.ainvoke(state)

    output = final_state["table_round_outputs"][0]
    assert len(output["contributions"]) == 8
    assert [item["turn_index"] for item in output["contributions"]] == list(range(8))
    assert {item["cycle_index"] for item in output["contributions"]} == {0, 1, 2, 3}


@pytest.mark.asyncio
async def test_note_checkpoint_notes_are_passed_to_host_synthesis() -> None:
    captured_host_prompts: list[str] = []

    class NoteAwareLLM(DryRunCafeLLM):
        async def agenerate(self, system: str, user: str) -> str:
            if "User-marked notes for this table/round" in user and '"formatmemory"' in user:
                captured_host_prompts.append(user)
            return await super().agenerate(system, user)

    async def note_checkpoint(_run_id: str, table_id: str, round_index: int):
        return [
            {
                "id": "note-1",
                "text": "Edge users repeatedly get stuck in the night flow, which may reveal a design opportunity.",
                "table_id": table_id,
                "round_index": round_index,
                "speaker_name": "Agent One",
                "speaker_id": "agent_01",
                "speech_id": "speech-1",
                "speech_target_id": "mark-1",
                "created_at": "10:00",
            }
        ]

    state = create_initial_state(
        questions=["q1"],
        rounds=1,
        table_count=1,
        seats_per_table=2,
        speeches_per_agent=1,
    )
    graph = build_world_cafe_graph(NoteAwareLLM(), note_checkpoint=note_checkpoint)

    final_state = await graph.ainvoke(state)

    assert captured_host_prompts
    assert "Edge users repeatedly get stuck" in captured_host_prompts[0]
    output = final_state["table_round_outputs"][0]
    assert output["user_notes"][0]["text"].startswith("Edge users")
    memory_round = final_state["table_memories"]["table_01"]["rounds"][0]
    assert memory_round["user_notes"][0]["speaker_id"] == "agent_01"


@pytest.mark.asyncio
async def test_single_speaker_failure_does_not_stop_discussion() -> None:
    class FlakySpeakerLLM(DryRunCafeLLM):
        def __init__(self) -> None:
            self.speaker_calls = 0

        async def agenerate(self, system: str, user: str) -> str:
            if "It is your turn" in user:
                self.speaker_calls += 1
                if self.speaker_calls == 1:
                    raise RuntimeError("temporary speaker failure")
            return await super().agenerate(system, user)

    state = create_initial_state(
        questions=["q1"],
        rounds=1,
        table_count=1,
        seats_per_table=3,
        speeches_per_agent=2,
    )
    graph = build_world_cafe_graph(FlakySpeakerLLM())

    final_state = await graph.ainvoke(state)

    output = final_state["table_round_outputs"][0]
    assert final_state["stage"] == "done"
    assert len(output["contributions"]) == 4
    assert output["contributions"][0]["generation_error"] == "temporary speaker failure"
    assert "generation_error" not in output["contributions"][1]
    assert [item["turn_index"] for item in output["contributions"]] == [0, 1, 2, 3]


@pytest.mark.asyncio
async def test_hosts_stay_put_and_speaking_agents_rotate_between_rounds() -> None:
    state = create_initial_state(
        questions={"table_01": "q1", "table_02": "q2"},
        rounds=2,
        table_count=2,
        seats_per_table=3,
        speeches_per_agent=1,
    )
    initial_assignments = {table: list(agents) for table, agents in state["assignments"].items()}
    hosts = dict(state["hosts"])
    graph = build_world_cafe_graph(DryRunCafeLLM())

    final_state = await graph.ainvoke(state)

    first_round_outputs = {
        output["table_id"]: output
        for output in final_state["table_round_outputs"]
        if output["round_index"] == 0
    }
    second_round_outputs = {
        output["table_id"]: output
        for output in final_state["table_round_outputs"]
        if output["round_index"] == 1
    }

    assert first_round_outputs["table_01"]["agent_ids"][0] == hosts["table_01"]
    assert second_round_outputs["table_01"]["agent_ids"][0] == hosts["table_01"]
    assert second_round_outputs["table_02"]["agent_ids"][0] == hosts["table_02"]
    assert second_round_outputs["table_01"]["agent_ids"][1:] == initial_assignments["table_02"][1:]
    assert second_round_outputs["table_02"]["agent_ids"][1:] == initial_assignments["table_01"][1:]
    for output in final_state["table_round_outputs"]:
        speaker_ids = {contribution["agent_id"] for contribution in output["contributions"]}
        assert output["host_id"] not in speaker_ids


@pytest.mark.asyncio
async def test_host_record_is_emitted_before_table_done_and_rotation() -> None:
    state = create_initial_state(
        questions={"table_01": "q1", "table_02": "q2"},
        rounds=2,
        table_count=2,
        seats_per_table=2,
        speeches_per_agent=1,
    )
    graph = build_world_cafe_graph(DryRunCafeLLM())

    final_state = await graph.ainvoke(state)

    first_round_trace = [
        event for event in final_state["trace"]
        if event["metadata"].get("round_index") == 0 or event["stage"] == "rotation"
    ]
    host_record_positions = [
        index for index, event in enumerate(first_round_trace)
        if event["stage"] == "host_record"
    ]
    table_done_positions = [
        index for index, event in enumerate(first_round_trace)
        if event["stage"] == "table_discussion" and "completed" in event["message"]
    ]
    rotation_position = next(
        index for index, event in enumerate(first_round_trace)
        if event["stage"] == "rotation"
    )

    assert host_record_positions
    assert table_done_positions
    assert max(host_record_positions) < rotation_position
    assert max(table_done_positions) < rotation_position


@pytest.mark.asyncio
async def test_packet_generation_failure_still_routes_speaking_agents() -> None:
    class FlakyPacketLLM(DryRunCafeLLM):
        async def agenerate(self, system: str, user: str) -> str:
            if "carry_over_packet" in system:
                raise RuntimeError("packet gateway failed")
            return await super().agenerate(system, user)

    state = create_initial_state(
        questions={"table_01": "q1", "table_02": "q2"},
        rounds=2,
        table_count=2,
        seats_per_table=2,
        speeches_per_agent=1,
    )
    graph = build_world_cafe_graph(FlakyPacketLLM())

    final_state = await graph.ainvoke(state)

    assert final_state["stage"] == "done"
    assert final_state["rotation_history"]
    assert final_state["agent_pockets"]
    packet = next(iter(final_state["agent_pockets"].values()))
    assert packet["generation_error"] == "packet gateway failed"
    assert packet["agent"]["id"]
    assert "personal_insight" in packet["agent_generated_memory"]
    assert "carry_forward_question" not in packet["agent_generated_memory"]


@pytest.mark.asyncio
async def test_harvest_output_is_formatted_when_prompt_limits_are_exceeded() -> None:
    class LongOutputLLM:
        async def agenerate(self, system: str, user: str) -> str:
            if "global harvest" in system.lower():
                return "x" * 600
            if "table host" in system.lower():
                return (
                    "## synthesis\nSummary\n\n"
                    "## key_insights\n- Insight\n\n"
                    "## open_questions\n- Question\n\n"
                    "## tensions\n- Tension"
                )
            return "x" * 350

    state = create_initial_state(
        questions=["q1"],
        rounds=1,
        table_count=1,
        seats_per_table=2,
        speeches_per_agent=1,
    )
    graph = build_world_cafe_graph(LongOutputLLM())

    final_state = await graph.ainvoke(state)

    contribution = final_state["table_round_outputs"][0]["contributions"][0]
    assert len(contribution["content"]) == 350
    harvest_content = final_state["harvest"]["content"]
    assert len(harvest_content) <= 500
    assert harvest_content.startswith("Design Insights")
    assert "3. Up to three next design directions" in harvest_content


@pytest.mark.asyncio
async def test_stream_events_include_hover_memory_snapshots() -> None:
    state = create_initial_state(
        questions=["q1"],
        rounds=1,
        table_count=1,
        seats_per_table=2,
        speeches_per_agent=1,
    )
    graph = build_world_cafe_graph(DryRunCafeLLM())

    final_state = await graph.ainvoke(state)

    host_opening = next(event for event in final_state["trace"] if event["stage"] == "host_opening")
    contribution = next(event for event in final_state["trace"] if event["stage"] == "agent_contribution")
    host_record = next(event for event in final_state["trace"] if event["stage"] == "host_record")

    assert host_opening["metadata"]["memory_snapshot"]["kind"] == "table_host"
    assert contribution["metadata"]["memory_snapshot"]["kind"] == "speaking_agent"
    assert host_record["metadata"]["memory_snapshot"]["kind"] == "table_host"
    assert TABLEMEMORY_USAGE_DESCRIPTION in host_record["metadata"]["memory_snapshot"]["tablememory_usage_description"]
    assert host_record["metadata"]["memory_snapshot"]["recent_rounds"]
    assert host_record["metadata"]["memory_snapshot"]["recent_rounds"][-1]["round"] == 1
    assert "repeated_themes" in host_record["metadata"]["memory_snapshot"]["recent_rounds"][-1]


@pytest.mark.asyncio
async def test_speaking_agent_trace_marks_background_context() -> None:
    state = create_initial_state(
        questions=["q1"],
        rounds=1,
        table_count=1,
        seats_per_table=2,
        speeches_per_agent=1,
        background_context="# Background\nThis is a piece of project material.",
    )
    graph = build_world_cafe_graph(DryRunCafeLLM())

    final_state = await graph.ainvoke(state)

    contribution = next(event for event in final_state["trace"] if event["stage"] == "agent_contribution")
    assert contribution["metadata"]["has_background_context"] is True
    assert contribution["metadata"]["background_context_chars"] == len("# Background\nThis is a piece of project material.")


def test_prompts_limit_agent_turns_and_global_harvest_length() -> None:
    agent = {
        "id": "agent_01",
        "name": "A",
        "role": "designer",
        "skills": [],
        "style": "direct",
    }
    memory = {
        "table_id": "table_01",
        "question": "q1",
        "host_id": "agent_02",
        "living_summary": "table_01 has accumulated living memory from all discussion rounds.",
        "key_insights": [],
        "open_questions": [],
        "tensions": [],
        "formatmemory": [
            {
                "round_index": 1,
                "repeated_themes": ["cross-round recurring theme"],
                "minority_inspiring_views": ["minority inspiring view"],
                "unresolved_tensions": ["persistent tension"],
            }
        ],
        "next_round_question_seeds": ["follow-up question seed"],
        "rounds": [],
    }

    _, contribution_user = contribution_prompt(
        table_id="table_01",
        question="q1",
        round_index=0,
        agent=agent,
        table_agents=[agent],
        memory=memory,
        table_spec={
            "parent_question": "User's larger question",
            "lens": "reframing",
            "guiding_question": "q1",
        },
        conversation=[],
        background_context="Background context",
        turn_index=0,
        cycle_index=0,
    )
    _, host_opening_user = host_opening_prompt(
        question="q1",
        parent_question="User's larger question",
        memory=memory,
        background_context="Background context",
    )
    _, host_synthesis_user = host_synthesis_prompt(
        table_id="table_01",
        question="q1",
        round_index=1,
        host=agent,
        memory=memory,
        table_spec={
            "parent_question": "User's larger question",
            "lens": "reframing",
            "guiding_question": "q1",
        },
        contributions=["This round's contribution"],
        background_context="Background context",
    )
    speaking_history = [
        {
            "table_id": "table_01",
            "question": "q1",
            "round_index": 0,
            "contributions": [
                {
                    "agent_id": "agent_01",
                    "agent_name": "A",
                    "content": "This is the original historical contribution from a speaking agent.",
                    "turn_index": 0,
                    "cycle_index": 0,
                }
            ],
            "user_notes": [
                {
                    "text": "A key note marked by the user this round.",
                    "speaker_name": "A",
                    "speaker_id": "agent_01",
                    "speech_id": "speech_01",
                }
            ],
        }
    ]
    _, harvest_user = global_harvest_prompt({"table_01": memory}, speaking_history)

    assert "under 100 English words" in contribution_user
    assert "Background material" in contribution_user
    assert "Background context" in contribution_user
    assert "Original user request: User's larger question" in contribution_user
    assert "Table spec" in contribution_user
    assert "reframing" in contribution_user
    assert "Original user request: User's larger question" in host_opening_user
    assert "only 2-3 brief open questions" in host_opening_user
    assert "[Opening phrase stating this round's focus in under 10 English words]" in host_opening_user
    assert "- [Question 1, one sentence, no extra setup]" in host_opening_user
    assert "background_context" in host_opening_user
    assert "Host profile" not in host_opening_user
    assert "table_spec:" not in host_opening_user
    assert '"tablememory_usage_description"' in host_synthesis_user
    assert TABLEMEMORY_USAGE_DESCRIPTION in host_synthesis_user
    assert "under 1200 English words" in harvest_user
    speaking_index = harvest_user.index("original dialogue history from all speaking agents")
    questions_index = harvest_user.index("discussion questions for all tables")
    tablememory_index = harvest_user.index("tablememory for all tables")
    notes_index = harvest_user.index("user-marked notes from each round")
    assert speaking_index < questions_index < tablememory_index < notes_index
    assert "primary harvest evidence with the highest priority" in harvest_user
    assert "tablememory for all tables" in harvest_user
    assert "table_01 has accumulated living memory" in harvest_user
    assert "cross-round recurring theme" in harvest_user
    assert "original dialogue history from all speaking agents" in harvest_user
    assert "A (agent_01): This is the original historical contribution from a speaking agent." in harvest_user
    assert "A key note marked by the user this round." in harvest_user
    assert "Round summary:" not in harvest_user
    assert "Host memory:" not in harvest_user
    assert "Design Insights:" in harvest_user
    assert "### Insight 1" in harvest_user
    assert "### Insight 2" in harvest_user
    assert "### Insight 3" in harvest_user
    assert "1. User need" in harvest_user
    assert "2. Reframed design problem" in harvest_user
    assert "3. Up to three next design directions" in harvest_user


def test_create_initial_state_fills_missing_agents_without_duplicate_ids() -> None:
    state = create_initial_state(
        questions=["q1", "q2", "q3", "q4"],
        agents=[
            {
                "id": "agent_01",
                "name": "Custom 1",
                "role": "custom",
                "skills": ["s1"],
                "style": "custom",
            }
        ],
    )

    agent_ids = [agent["id"] for agent in state["agent_profiles"][:16]]
    assert len(agent_ids) == 16
    assert len(set(agent_ids)) == 16


def test_create_initial_state_accepts_custom_tables_and_speakers() -> None:
    state = create_initial_state(
        questions={
            "table_01": "q1",
            "table_02": "q2",
            "table_03": "q3",
        },
        table_count=3,
        seats_per_table=3,
        hosts={
            "table_01": "agent_01",
            "table_02": "agent_02",
            "table_03": "agent_03",
        },
        assignments={
            "table_01": ["agent_04", "agent_05"],
            "table_02": ["agent_06", "agent_07"],
            "table_03": ["agent_08", "agent_09"],
        },
    )

    assert state["table_count"] == 3
    assert state["assignments"]["table_01"] == ["agent_01", "agent_04", "agent_05"]
    assert state["hosts"]["table_03"] == "agent_03"


@pytest.mark.asyncio
async def test_context_orchestration_generates_host_memory_and_pockets() -> None:
    state = create_initial_state(
        questions={"table_01": "q1", "table_02": "q2"},
        table_specs={
            "table_01": {
                "table_id": "table_01",
                "expert_skill": "liu-long",
                "expert_rationale": "Human factors and user research are suitable for this table.",
                "lens": "user_journey",
                "guiding_question": "q1",
                "round_subquestions": {"round_1": ["What should we observe?"], "round_2": ["What tensions appear?"]},
            },
            "table_02": {
                "table_id": "table_02",
                "expert_skill": "wang-meng",
                "expert_rationale": "AI and knowledge organization are suitable for this table.",
                "lens": "future_scenario",
                "guiding_question": "q2",
            },
        },
        rounds=2,
        table_count=2,
        seats_per_table=3,
        speeches_per_agent=1,
    )
    graph = build_world_cafe_graph(DryRunCafeLLM())

    final_state = await graph.ainvoke(state)

    assert final_state["table_specs"]["table_01"]["expert_skill"] == "liu-long"
    assert len(final_state["host_openings"]) == 4
    assert final_state["question_seed_history"]
    assert final_state["pocket_history"]
    assert final_state["agent_pockets"]
    packet = next(iter(final_state["agent_pockets"].values()))
    assert packet["from_table"] in {"table_01", "table_02"}
    assert packet["to_table"] in {"table_01", "table_02"}
    assert "current_table_task_anchor" not in packet
    assert final_state["rotation_history"][0]["packet_routes"]
    memory = final_state["table_memories"]["table_01"]
    assert "formatmemory" in memory
    assert memory["formatmemory"]
    assert memory["tablememory_usage_description"] == TABLEMEMORY_USAGE_DESCRIPTION
    assert "llm_generated_table_memory_template" not in memory
    assert "host_generated_table_memory" not in memory


@pytest.mark.asyncio
async def test_visible_outputs_are_natural_and_bold_design_opportunities() -> None:
    class OpportunityLLM(DryRunCafeLLM):
        async def agenerate(self, system: str, user: str) -> str:
            if "## opening" in user:
                return (
                    "## opening\n"
                    "There is a design opportunity here: first listen closely to real blockers for edge users.\n\n"
                    "## question_seeds\n"
                    "- Which edge situation could most change the problem understanding?"
                )
            if '"formatmemory"' in user:
                return """
{
  "formatmemory": {
    "table_question": "q1",
    "round_index": 1,
    "repeated_themes": ["Design opportunities come from the gap between edge situations and mainstream journeys."],
    "minority_inspiring_views": ["Edge cases change the problem boundary."],
    "unresolved_tensions": ["There is tension between efficiency-first delivery and inclusive exploration."]
  },
  "next_round_question_seeds": ["How should this opportunity hypothesis be validated?"]
}
"""
            if '"agent_generated_memory"' in user:
                return """
{
  "agent": {"id": "agent_02", "name": "Agent Two", "role": "participant", "skills": ["edge cases"]},
  "agent_generated_memory": {
    "skill_lens": "edge cases",
    "personal_insight": "Edge cases may explain this table's tension."
  }
}
"""
            if "display_markdown" in user:
                return """
{
  "pattern_channel": [],
  "weak_signal_channel": [{"signal": "Edge cases reveal a design opportunity", "from_table": "table_01"}],
  "cross_table_tensions": [],
  "opportunity_hypotheses": [{"hypothesis": "Use edge cases to validate the opportunity hypothesis"}],
  "reframed_design_questions": [],
  "next_learning_experiments": [],
  "display_markdown": "Design Insights:\\n### Insight 1\\n1. User need: Users need default journeys to cover edge situations.\\n2. Reframed design problem: How might design opportunities exposed by edge cases become testable journeys?\\n3. Up to three next design directions:\\n- Redefine the default journey.\\n### Insight 2\\n1. User need: Teams need clearer evidence about edge blockers.\\n2. Reframed design problem: How might evidence from edge contexts reshape mainstream service assumptions?\\n3. Up to three next design directions:\\n- Create an edge-case evidence board.\\n### Insight 3\\n1. User need: Stakeholders need shared language for risk and inclusion.\\n2. Reframed design problem: How might inclusion criteria guide practical trade-offs?\\n3. Up to three next design directions:\\n- Test an inclusion review checkpoint."
}
"""
            return "I hear a design opportunity: treat edge-user breakdowns as validation cues for the next round."

    state = create_initial_state(
        questions=["q1"],
        rounds=1,
        table_count=1,
        seats_per_table=2,
        speeches_per_agent=1,
    )
    graph = build_world_cafe_graph(OpportunityLLM())

    final_state = await graph.ainvoke(state)

    output = final_state["table_round_outputs"][0]
    assert "**" in output["host_opening"]
    assert "question_seeds" not in output["host_opening"]
    assert "**" in output["contributions"][0]["content"]
    assert "**" in output["host_record_display"]
    assert "host_memory_update_instruction" not in output["host_record_display"]
    assert "formatmemory" not in output["host_record_display"]
    host_record_events = [
        event for event in final_state["trace"]
        if event["stage"] == "host_record"
    ]
    assert host_record_events
    assert "raw_content" not in host_record_events[0]["metadata"]
    assert "host_memory_update_instruction" not in host_record_events[0]["metadata"]["content"]
    assert "formatmemory" not in host_record_events[0]["metadata"]["content"]
    assert "**" in final_state["harvest"]["content"]


@pytest.mark.asyncio
async def test_host_record_display_never_exposes_json_memory() -> None:
    class BrokenJsonHostLLM(DryRunCafeLLM):
        async def agenerate(self, system: str, user: str) -> str:
            if '"formatmemory"' in user:
                return """
{
  "formatmemory": {
    "repeated_themes": ["This JSON is missing its ending, so it must not be exposed as-is"]
"""
            return await super().agenerate(system, user)

    state = create_initial_state(
        questions=["q1"],
        rounds=1,
        table_count=1,
        seats_per_table=2,
        speeches_per_agent=1,
    )
    graph = build_world_cafe_graph(BrokenJsonHostLLM())

    final_state = await graph.ainvoke(state)

    display = final_state["table_round_outputs"][0]["host_record_display"]
    assert "{" not in display
    assert "formatmemory" not in display
    assert "repeated_themes" not in display
    assert display.strip()


@pytest.mark.asyncio
async def test_json_harvest_is_stored_as_structured_harvest() -> None:
    class JsonHarvestLLM(DryRunCafeLLM):
        async def agenerate(self, system: str, user: str) -> str:
            if "display_markdown" in user:
                return """
{
  "pattern_channel": [{"pattern": "shared pattern", "seen_in_tables": ["table_01"], "why_it_matters": "collective signal"}],
  "weak_signal_channel": [{"signal": "rare signal", "from_table": "table_01", "why_it_matters": "novel", "risk_if_ignored": "lost opportunity"}],
  "cross_table_tensions": [{"tension": "open vs focused", "tables_involved": ["table_01"], "possible_reframe": "pace the inquiry"}],
  "opportunity_hypotheses": [{"hypothesis": "testable opportunity", "based_on": ["shared pattern"], "next_learning_action": "prototype question"}],
  "user_needs": ["shared need"],
  "reframed_design_problem": "How might the system keep weak signals alive?",
  "next_design_directions": ["small probe"],
  "reframed_design_questions": ["How might the system keep weak signals alive?"],
  "next_learning_experiments": [{"experiment": "small probe", "what_to_observe": "signal quality", "why_now": "before convergence"}],
  "display_markdown": "Design Insights:\\n### Insight 1\\n1. User need: shared need\\n2. Reframed design problem: How might the system keep weak signals alive?\\n3. Up to three next design directions:\\n- small probe\\n### Insight 2\\n1. User need: shared need\\n2. Reframed design problem: How might the system keep weak signals alive?\\n3. Up to three next design directions:\\n- small probe\\n### Insight 3\\n1. User need: shared need\\n2. Reframed design problem: How might the system keep weak signals alive?\\n3. Up to three next design directions:\\n- small probe"
}
"""
            return await super().agenerate(system, user)

    state = create_initial_state(
        questions=["q1"],
        rounds=1,
        table_count=1,
        seats_per_table=2,
        speeches_per_agent=1,
    )
    graph = build_world_cafe_graph(JsonHarvestLLM())

    final_state = await graph.ainvoke(state)

    harvest = final_state["harvest"]
    assert harvest["content"].startswith("Design Insights")
    assert harvest["structured_harvest"]["user_needs"] == ["shared need"]
    assert harvest["structured_harvest"]["next_design_directions"] == ["small probe"]
    assert harvest["structured_harvest"]["pattern_channel"][0]["pattern"] == "shared pattern"
    assert harvest["structured_harvest"]["weak_signal_channel"][0]["signal"] == "rare signal"


def test_json_harvest_with_unknown_fields_uses_design_insight_template() -> None:
    content = '{"summary": "The model returned unexpected fields, but the harvest content is still readable."}'
    structured = _parse_structured_harvest(content)

    display = _harvest_display_content(content, structured)

    assert display.startswith("Design Insights")
    assert "Shared Patterns" not in display
    assert "1. User need: None yet" in display


def test_harvest_display_builds_three_structured_design_insights() -> None:
    content = """
{
  "design_insights": [
    {
      "user_need": "Night services need lower cognitive load.",
      "reframed_design_problem": "How might the night-help flow remain understandable under stress?",
      "design_direction": "Build a one-tap night-help prototype and observe false-trigger rates."
    },
    {
      "user_need": "Caregivers need to quickly understand status changes.",
      "reframed_design_problem": "How might scattered status signals become actionable alerts?",
      "design_direction": "Test a tiered caregiver alert dashboard."
    },
    {
      "user_need": "Community volunteers need clear boundaries for intervention.",
      "reframed_design_problem": "How might handoff points between volunteer support and professional services be defined?",
      "design_direction": "Co-create a volunteer referral script."
    }
  ]
}
"""
    structured = _parse_structured_harvest(content)
    display = _harvest_display_content(content, structured)

    assert len(structured["design_insights"]) == 3
    assert display.count("### Insight") == 3
    assert "Night services need lower cognitive load" in display
    assert "Co-create a volunteer referral script" in display


def test_legacy_empty_harvest_template_is_not_displayed() -> None:
    content = """
Shared Patterns
None yet

Weak Signals
None yet

Cross-table Tensions
None yet

Reframed Questions
None yet

Next Experiments
None yet
"""
    structured = _parse_structured_harvest(content)
    display = _harvest_display_content(content, structured)

    assert display.startswith("Design Insights")
    assert "Shared Patterns" not in display
    assert "Weak Signals" not in display
    assert "3. Up to three next design directions" in display
