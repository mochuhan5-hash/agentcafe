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
    assert "设计洞察" in final_state["harvest"]["content"]
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
                "text": "边缘用户在夜间流程里反复卡住，可能是一个设计机会。",
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
    assert "边缘用户在夜间流程里反复卡住" in captured_host_prompts[0]
    output = final_state["table_round_outputs"][0]
    assert output["user_notes"][0]["text"].startswith("边缘用户")
    memory_round = final_state["table_memories"]["table_01"]["rounds"][0]
    assert memory_round["user_notes"][0]["speaker_id"] == "agent_01"


@pytest.mark.asyncio
async def test_single_speaker_failure_does_not_stop_discussion() -> None:
    class FlakySpeakerLLM(DryRunCafeLLM):
        def __init__(self) -> None:
            self.speaker_calls = 0

        async def agenerate(self, system: str, user: str) -> str:
            if "现在轮到你发言" in user:
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
            if "全局 harvest" in system:
                return "全" * 600
            if "桌长" in system:
                return (
                    "## synthesis\n摘要\n\n"
                    "## key_insights\n- 洞察\n\n"
                    "## open_questions\n- 问题\n\n"
                    "## tensions\n- 张力"
                )
            return "发" * 350

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
    assert harvest_content.startswith("设计洞察")
    assert "3、不超过三个后续的设计方向" in harvest_content


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
        background_context="# 背景\n这是一段项目材料。",
    )
    graph = build_world_cafe_graph(DryRunCafeLLM())

    final_state = await graph.ainvoke(state)

    contribution = next(event for event in final_state["trace"] if event["stage"] == "agent_contribution")
    assert contribution["metadata"]["has_background_context"] is True
    assert contribution["metadata"]["background_context_chars"] == len("# 背景\n这是一段项目材料。")


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
        "living_summary": "table_01 累积了所有轮讨论的活记忆。",
        "key_insights": [],
        "open_questions": [],
        "tensions": [],
        "formatmemory": [
            {
                "round_index": 1,
                "repeated_themes": ["跨轮重复主题"],
                "minority_inspiring_views": ["少数启发观点"],
                "unresolved_tensions": ["持续张力"],
            }
        ],
        "next_round_question_seeds": ["后续追问种子"],
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
            "parent_question": "用户大问题",
            "lens": "reframing",
            "guiding_question": "q1",
        },
        conversation=[],
        background_context="背景上下文",
        turn_index=0,
        cycle_index=0,
    )
    _, host_opening_user = host_opening_prompt(
        question="q1",
        parent_question="用户大问题",
        memory=memory,
        background_context="背景上下文",
    )
    _, host_synthesis_user = host_synthesis_prompt(
        table_id="table_01",
        question="q1",
        round_index=1,
        host=agent,
        memory=memory,
        table_spec={
            "parent_question": "用户大问题",
            "lens": "reframing",
            "guiding_question": "q1",
        },
        contributions=["本轮发言"],
        background_context="背景上下文",
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
                    "content": "这是 speaking agent 的原始历史发言。",
                    "turn_index": 0,
                    "cycle_index": 0,
                }
            ],
            "user_notes": [
                {
                    "text": "用户标记的本轮关键笔记。",
                    "speaker_name": "A",
                    "speaker_id": "agent_01",
                    "speech_id": "speech_01",
                }
            ],
        }
    ]
    _, harvest_user = global_harvest_prompt({"table_01": memory}, speaking_history)

    assert "100字以内" in contribution_user
    assert "背景材料" in contribution_user
    assert "背景上下文" in contribution_user
    assert "用户原始大问题：用户大问题" in contribution_user
    assert "本桌 table_spec" in contribution_user
    assert "reframing" in contribution_user
    assert "用户原始大问题：用户大问题" in host_opening_user
    assert "只提出2-3个可直接开启讨论的简短开放问句" in host_opening_user
    assert "【开场白，说明本轮讨论的关注点（10字以内）】" in host_opening_user
    assert "- 【问题一（一句话引导，不要提供过多信息）】" in host_opening_user
    assert "background_context" in host_opening_user
    assert "桌长画像" not in host_opening_user
    assert "table_spec：" not in host_opening_user
    assert '"tablememory_usage_description"' in host_synthesis_user
    assert TABLEMEMORY_USAGE_DESCRIPTION in host_synthesis_user
    assert "1200字以内" in harvest_user
    speaking_index = harvest_user.index("所有 speaking agents 的历史对话原文")
    questions_index = harvest_user.index("所有桌子的讨论问题")
    tablememory_index = harvest_user.index("所有桌子的 tablememory")
    notes_index = harvest_user.index("用户每轮标记的笔记")
    assert speaking_index < questions_index < tablememory_index < notes_index
    assert "作为 harvest 主证据（优先级最高）" in harvest_user
    assert "所有桌子的 tablememory" in harvest_user
    assert "table_01 累积了所有轮讨论的活记忆。" in harvest_user
    assert "跨轮重复主题" in harvest_user
    assert "所有 speaking agents 的历史对话原文" in harvest_user
    assert "A (agent_01)：这是 speaking agent 的原始历史发言。" in harvest_user
    assert "用户标记的本轮关键笔记。" in harvest_user
    assert "轮次摘要：" not in harvest_user
    assert "桌长记忆：" not in harvest_user
    assert "设计洞察：" in harvest_user
    assert "### 洞察 1" in harvest_user
    assert "### 洞察 2" in harvest_user
    assert "### 洞察 3" in harvest_user
    assert "1、用户主要需求的提取" in harvest_user
    assert "2、设计问题的重新界定" in harvest_user
    assert "3、不超过三个后续的设计方向" in harvest_user


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
                "expert_rationale": "人因与用户研究视角适合本桌。",
                "lens": "user_journey",
                "guiding_question": "q1",
                "round_subquestions": {"round_1": ["观察什么？"], "round_2": ["有什么张力？"]},
            },
            "table_02": {
                "table_id": "table_02",
                "expert_skill": "wang-meng",
                "expert_rationale": "AI 与知识组织视角适合本桌。",
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
                    "这里有一个设计机会：先把边缘用户的真实阻塞点听清楚。\n\n"
                    "## question_seeds\n"
                    "- 哪个边缘情境最能改变问题理解？"
                )
            if '"formatmemory"' in user:
                return """
{
  "formatmemory": {
    "table_question": "q1",
    "round_index": 1,
    "repeated_themes": ["设计机会来自边缘场景与主流旅程之间的落差。"],
    "minority_inspiring_views": ["边缘案例改变了问题边界。"],
    "unresolved_tensions": ["效率优先与包容性探索之间存在张力。"]
  },
  "next_round_question_seeds": ["如何验证这个机会假设？"]
}
"""
            if '"agent_generated_memory"' in user:
                return """
{
  "agent": {"id": "agent_02", "name": "Agent Two", "role": "participant", "skills": ["edge cases"]},
  "agent_generated_memory": {
    "skill_lens": "edge cases",
    "personal_insight": "边缘案例可能解释当前桌张力"
  }
}
"""
            if "display_markdown" in user:
                return """
{
  "pattern_channel": [],
  "weak_signal_channel": [{"signal": "边缘案例暴露设计机会", "from_table": "table_01"}],
  "cross_table_tensions": [],
  "opportunity_hypotheses": [{"hypothesis": "用边缘案例验证机会假设"}],
  "reframed_design_questions": [],
  "next_learning_experiments": [],
  "display_markdown": "设计洞察：\\n1、用户主要需求的提取：用户需要默认旅程覆盖边缘场景。\\n2、设计问题的重新界定：如何把边缘案例暴露的设计机会转化为可验证旅程。\\n3、不超过三个后续的设计方向：\\n- 重新定义默认旅程。"
}
"""
            return "我听到一个设计机会：把边缘用户的断点当成下一轮验证线索。"

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
    "repeated_themes": ["这段 JSON 少了结尾，所以不能原样暴露"]
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
  "display_markdown": "设计洞察：\\n1、用户主要需求的提取：shared need\\n2、设计问题的重新界定：How might the system keep weak signals alive?\\n3、不超过三个后续的设计方向：\\n- small probe"
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
    assert harvest["content"].startswith("设计洞察")
    assert harvest["structured_harvest"]["user_needs"] == ["shared need"]
    assert harvest["structured_harvest"]["next_design_directions"] == ["small probe"]
    assert harvest["structured_harvest"]["pattern_channel"][0]["pattern"] == "shared pattern"
    assert harvest["structured_harvest"]["weak_signal_channel"][0]["signal"] == "rare signal"


def test_json_harvest_with_unknown_fields_uses_design_insight_template() -> None:
    content = '{"summary": "模型返回了非约定字段，但仍有可读 harvest 内容。"}'
    structured = _parse_structured_harvest(content)

    display = _harvest_display_content(content, structured)

    assert display.startswith("设计洞察")
    assert "Shared Patterns" not in display
    assert "1、用户主要需求的提取：暂无" in display


def test_harvest_display_builds_three_structured_design_insights() -> None:
    content = """
{
  "design_insights": [
    {
      "user_need": "夜间服务需要更低认知负担。",
      "reframed_design_problem": "如何让夜间求助流程在压力状态下也能被理解。",
      "design_direction": "建立夜间一键求助原型并观察误触率。"
    },
    {
      "user_need": "照护者需要快速理解状态变化。",
      "reframed_design_problem": "如何把零散状态信号转成可行动提醒。",
      "design_direction": "测试照护者分级提醒看板。"
    },
    {
      "user_need": "社区志愿者需要明确介入边界。",
      "reframed_design_problem": "如何定义志愿支持与专业服务之间的交接点。",
      "design_direction": "共创一套志愿者转介脚本。"
    }
  ]
}
"""
    structured = _parse_structured_harvest(content)
    display = _harvest_display_content(content, structured)

    assert len(structured["design_insights"]) == 3
    assert display.count("### 洞察") == 3
    assert "夜间服务需要更低认知负担" in display
    assert "共创一套志愿者转介脚本" in display


def test_legacy_empty_harvest_template_is_not_displayed() -> None:
    content = """
Shared Patterns
暂无

Weak Signals
暂无

Cross-table Tensions
暂无

Reframed Questions
暂无

Next Experiments
暂无
"""
    structured = _parse_structured_harvest(content)
    display = _harvest_display_content(content, structured)

    assert display.startswith("设计洞察")
    assert "Shared Patterns" not in display
    assert "Weak Signals" not in display
    assert "3、不超过三个后续的设计方向" in display
