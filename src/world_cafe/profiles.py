from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from world_cafe.state import AgentProfile


def build_default_agent_profiles(count: int = 16) -> list[AgentProfile]:
    expert_profiles: list[AgentProfile] = [
        {
            "id": "agent_01",
            "name": "Prof.Lou",
            "role": "Lou Yongqi Perspective Agent",
            "skills": ["design-driven innovation", "social innovation and sustainable design", "design education", "service and systems design", "urban-rural interaction design"],
            "style": (
                "Participates from Lou Yongqi's perspective: focuses on design-driven innovation, complex sociotechnical systems, "
                "communities as innovation frontiers, and how economies and education for repairing the planet can activate human goodwill and potential."
            ),
        },
        {
            "id": "agent_02",
            "name": "Prof. Wang Meng",
            "role": "Wang Meng Perspective Agent",
            "skills": ["design and AI", "knowledge-augmented LLMs", "multimodal knowledge graphs", "intelligent interaction design"],
            "style": (
                "Participates from Wang Meng's perspective: restrained, counterexample-driven, and scenario-specific, "
                "with a strength in translating KG/LLM engineering capabilities back into design contexts and deployable systems."
            ),
        },
        {
            "id": "agent_03",
            "name": "Prof. Liu Long",
            "role": "Liu Long Perspective Agent",
            "skills": ["human factors engineering", "inclusive design", "medical-device usability", "user research", "co-design"],
            "style": (
                "Participates from Liu Long's perspective: examines people, machines, environments, and software as an interaction system, "
                "with attention to marginal equality, fair value trade-offs, and grounded user research."
            ),
        },
        {
            "id": "agent_04",
            "name": "Prof. Wang Shouzhi",
            "role": "Wang Shouzhi Perspective Agent",
            "skills": ["design history", "design theory", "design education", "modern art history", "painting", "housing design"],
            "style": (
                "Participates from Wang Shouzhi's perspective: speaks through design history, context, service to people, and problem-solving, "
                "often starting with a story before making a judgment."
            ),
        },
    ]
    styles = [
        "Starts with a clear hypothesis, then turns it into discussable questions.",
        "Focuses on users, stakeholders, and details from real situations.",
        "Good at systems decomposition and structured synthesis.",
        "Good at raising counterexamples, boundary conditions, and risks.",
        "Practice-oriented and tends to translate ideas into action.",
        "Research- and evidence-oriented, with attention to evidence quality.",
        "Creatively associative and good at cross-domain analogies.",
        "Focused on ethics, fairness, and long-term impact.",
        "Focused on product strategy and value propositions.",
        "Focused on service journeys and touchpoint design.",
        "Focused on data, metrics, and evaluation.",
        "Focused on organizational collaboration and resource allocation.",
        "Focused on cultural context and local knowledge.",
        "Focused on technical implementation and system architecture.",
        "Focused on business sustainability and operating models.",
        "Critically synthetic and good at resolving divergence.",
    ]
    profiles: list[AgentProfile] = []
    for index in range(count):
        if index < len(expert_profiles):
            profiles.append(expert_profiles[index])
            continue
        agent_number = index + 1
        profiles.append(
            {
                "id": f"agent_{agent_number:02d}",
                "name": f"Agent {agent_number:02d}",
                "role": "placeholder",
                "skills": ["to be specified"],
                "style": styles[index % len(styles)],
            }
        )
    return profiles


def load_agent_profiles(path: str | Path) -> list[AgentProfile]:
    data = _load_yaml(path)
    raw_agents = data.get("agents", data if isinstance(data, list) else [])
    if not isinstance(raw_agents, list):
        raise ValueError("agents file must contain an 'agents' list")

    profiles: list[AgentProfile] = []
    for index, raw_agent in enumerate(raw_agents, start=1):
        if not isinstance(raw_agent, dict):
            raise ValueError(f"agent #{index} must be an object")
        agent_id = str(raw_agent.get("id") or f"agent_{index:02d}")
        skills = raw_agent.get("skills") or []
        if isinstance(skills, str):
            skills = [skills]
        profiles.append(
            {
                "id": agent_id,
                "name": str(raw_agent.get("name") or agent_id),
                "role": str(raw_agent.get("role") or "participant"),
                "skills": [str(skill) for skill in skills],
                "style": str(raw_agent.get("style") or ""),
            }
        )
    return profiles


def load_questions(path: str | Path) -> dict[str, str]:
    data = _load_yaml(path)
    raw_tables: Any = data.get("tables", data)
    if isinstance(raw_tables, list):
        return {f"table_{index:02d}": str(question) for index, question in enumerate(raw_tables, start=1)}
    if isinstance(raw_tables, dict):
        return {str(table_id): str(question) for table_id, question in raw_tables.items()}
    raise ValueError("questions file must be a list or a mapping under 'tables'")


def normalize_questions(questions: list[str] | dict[str, str], table_count: int = 4) -> dict[str, str]:
    if isinstance(questions, dict):
        normalized = {str(table_id): str(question) for table_id, question in questions.items()}
    else:
        normalized = {
            f"table_{index:02d}": str(question)
            for index, question in enumerate(questions, start=1)
        }
    if len(normalized) != table_count:
        raise ValueError(f"expected exactly {table_count} table questions, got {len(normalized)}")
    return dict(sorted(normalized.items()))


def _load_yaml(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}
