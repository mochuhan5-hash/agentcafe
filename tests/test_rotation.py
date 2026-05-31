from world_cafe.rotation import build_initial_assignments, rotate_non_hosts


def test_rotate_non_hosts_keeps_hosts_and_moves_other_agents() -> None:
    agent_ids = [f"agent_{index:02d}" for index in range(1, 17)]
    table_ids = [f"table_{index:02d}" for index in range(1, 5)]
    assignments, hosts = build_initial_assignments(
        agent_ids=agent_ids,
        table_ids=table_ids,
        seats_per_table=4,
    )

    rotated = rotate_non_hosts(assignments, hosts)

    assert rotated["table_01"][0] == hosts["table_01"]
    assert rotated["table_02"][0] == hosts["table_02"]
    assert rotated["table_01"][1:] == assignments["table_04"][1:]
    assert rotated["table_02"][1:] == assignments["table_01"][1:]
    assert sorted(agent for agents in rotated.values() for agent in agents) == sorted(agent_ids)
