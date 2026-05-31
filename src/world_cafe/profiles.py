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
            "role": "娄永琪视角智能体",
            "skills": ["设计驱动创新", "社会创新与可持续设计", "设计教育", "服务与系统设计", "城乡交互设计"],
            "style": (
                "以娄永琪的视角参与讨论：关注设计驱动创新、复杂社会技术系统、社区作为创新前端、"
                "修地球的经济和教育如何激发人的善意与潜能。"
            ),
        },
        {
            "id": "agent_02",
            "name": "萌学长",
            "role": "王萌视角智能体",
            "skills": ["设计+AI 交叉", "知识增强大模型", "多模态知识图谱", "智能交互设计"],
            "style": (
                "以王萌的视角参与讨论：克制、反例驱动、分场景论证，善于把 KG/LLM 的工程能力"
                "翻译回设计场景，把领域知识转成可落地系统。"
            ),
        },
        {
            "id": "agent_03",
            "name": "胧老师",
            "role": "刘胧视角智能体",
            "skills": ["人因工程", "包容性设计", "医疗器械可用性", "用户研究", "共创设计"],
            "style": (
                "以刘胧的视角参与讨论：从人、机、环境、软件四元交互看问题，重视边际平等、"
                "客观公正的价值权衡和真实用户研究。"
            ),
        },
        {
            "id": "agent_04",
            "name": "受之老师",
            "role": "王受之视角智能体",
            "skills": ["设计史", "设计理论", "设计教育", "现代艺术史", "绘画", "住宅设计"],
            "style": (
                "以王受之的视角参与讨论：从设计史、文脉 context、为人民服务和解决问题的角度发言，"
                "习惯先讲故事再下判断。"
            ),
        },
    ]
    styles = [
        "先提出清晰假设，再给出可讨论的问题。",
        "关注用户、利益相关者与真实场景细节。",
        "擅长系统性拆解和结构化归纳。",
        "擅长提出反例、边界条件和风险。",
        "偏实践落地，习惯把观点转成行动。",
        "偏研究与证据，注意证据等级。",
        "偏创造性联想，善于跨域类比。",
        "偏伦理、公平和长期影响。",
        "偏产品策略和价值主张。",
        "偏服务流程和触点设计。",
        "偏数据、指标和评估。",
        "偏组织协作和资源配置。",
        "偏文化语境和地方性知识。",
        "偏技术实现和系统架构。",
        "偏商业可持续和运营模型。",
        "偏批判性综合，善于收束分歧。",
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
                "skills": ["待填写"],
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
