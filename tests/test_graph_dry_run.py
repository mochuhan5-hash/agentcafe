import pytest

from world_cafe.graph import build_world_cafe_graph, create_initial_state
from world_cafe.llm import DryRunCafeLLM
from world_cafe.prompts import contribution_prompt, global_harvest_prompt


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
    assert "Shared Patterns" in final_state["harvest"]["content"]
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
async def test_model_outputs_are_preserved_when_prompt_limits_are_exceeded() -> None:
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
    assert len(final_state["harvest"]["content"]) == 600


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
        "living_summary": "",
        "key_insights": [],
        "open_questions": [],
        "tensions": [],
        "rounds": [],
    }

    _, contribution_user = contribution_prompt(
        table_id="table_01",
        question="q1",
        round_index=0,
        agent=agent,
        table_agents=[agent],
        memory=memory,
        conversation=[],
        background_context="",
        turn_index=0,
        cycle_index=0,
    )
    _, harvest_user = global_harvest_prompt({"table_01": memory}, [])

    assert "300字以内" in contribution_user
    assert "500字以内" in harvest_user


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
