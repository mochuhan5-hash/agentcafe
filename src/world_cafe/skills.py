"""Skill loader: reads local expert skill packs for facilitator injection."""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict

SKILLS_DIR = Path(__file__).with_name("skills")

# Map skill names used by the facilitator to directory names
SKILL_DIRS: dict[str, str] = {
    "louyongqi": "lou-yongqi-perspective",
    "wangmeng": "wang-meng",
    "wangshouzhi": "wang-shouzhi-perspective",
    "liulong": "liu-long-perspective",
}

SKILL_DISPLAY_NAMES: dict[str, str] = {
    "louyongqi": "Lou Yongqi",
    "wangmeng": "Wang Meng",
    "wangshouzhi": "Wang Shouzhi",
    "liulong": "Liu Long",
}


class SkillInfo(TypedDict):
    name: str
    display_name: str
    fields: list[str]
    description: str


def get_skill_dir(skill_name: str) -> Path | None:
    dirname = SKILL_DIRS.get(skill_name)
    if not dirname:
        return None
    path = SKILLS_DIR / dirname
    return path if path.is_dir() else None


def load_persona(skill_name: str) -> str:
    """Load the full persona.md content for a given skill."""
    skill_dir = get_skill_dir(skill_name)
    if not skill_dir:
        return ""
    persona_path = skill_dir / "persona.md"
    if not persona_path.exists():
        return ""
    return persona_path.read_text(encoding="utf-8")


def load_skill_summary(skill_name: str) -> str:
    """Load the SKILL.md description for routing display."""
    skill_dir = get_skill_dir(skill_name)
    if not skill_dir:
        return ""
    skill_path = skill_dir / "SKILL.md"
    if not skill_path.exists():
        return ""
    return skill_path.read_text(encoding="utf-8")


def all_skill_briefs() -> str:
    """Return a compact summary of all available skills for the routing LLM."""
    lines: list[str] = []
    for key, dirname in SKILL_DIRS.items():
        path = SKILLS_DIR / dirname / "SKILL.md"
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        # Extract frontmatter fields
        display = SKILL_DISPLAY_NAMES.get(key, key)
        # Get the description line from frontmatter
        desc_lines: list[str] = []
        in_desc = False
        for line in content.split("\n"):
            if line.startswith("description:"):
                in_desc = True
                rest = line[len("description:"):].strip()
                if rest:
                    desc_lines.append(rest)
                continue
            if in_desc:
                if line.startswith("  ") or line.startswith("\t"):
                    desc_lines.append(line.strip())
                else:
                    break
        desc = " ".join(desc_lines)[:200] if desc_lines else ""
        lines.append(f"- {key} ({display}): {desc}")
    return "\n".join(lines)
