from __future__ import annotations


def build_initial_assignments(
    *,
    agent_ids: list[str],
    table_ids: list[str],
    seats_per_table: int,
) -> tuple[dict[str, list[str]], dict[str, str]]:
    needed = len(table_ids) * seats_per_table
    if len(agent_ids) < needed:
        raise ValueError(f"need at least {needed} agents, got {len(agent_ids)}")

    assignments: dict[str, list[str]] = {}
    hosts: dict[str, str] = {}
    cursor = 0
    for table_id in table_ids:
        table_agents = agent_ids[cursor : cursor + seats_per_table]
        cursor += seats_per_table
        assignments[table_id] = table_agents
        hosts[table_id] = table_agents[0]
    return assignments, hosts


def rotate_non_hosts(
    assignments: dict[str, list[str]],
    hosts: dict[str, str],
) -> dict[str, list[str]]:
    table_ids = sorted(assignments)
    outgoing: dict[str, list[str]] = {}
    for table_id in table_ids:
        host_id = hosts[table_id]
        outgoing[table_id] = [agent_id for agent_id in assignments[table_id] if agent_id != host_id]

    rotated: dict[str, list[str]] = {}
    for index, table_id in enumerate(table_ids):
        source_table = table_ids[index - 1]
        rotated[table_id] = [hosts[table_id], *outgoing[source_table]]
    return rotated
