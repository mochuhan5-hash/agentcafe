from __future__ import annotations

import json
import re
from typing import Any


def extract_section(text: str, heading: str) -> str:
    marker = f"## {heading}".lower()
    lines = text.splitlines()
    start: int | None = None
    end = len(lines)
    for index, line in enumerate(lines):
        if line.strip().lower() == marker:
            start = index + 1
            continue
        if start is not None and line.startswith("## "):
            end = index
            break
    if start is None:
        return ""
    return "\n".join(lines[start:end]).strip()


def extract_bullets(section: str) -> list[str]:
    bullets: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            bullets.append(stripped[2:].strip())
    return bullets


def unique_append(existing: list[str], additions: list[str], limit: int = 20) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in [*existing, *additions]:
        normalized = " ".join(item.split()).lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def loads_jsonish(content: str) -> Any:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if match is None:
            raise
        return json.loads(match.group(0))


def loads_jsonish_object(content: str) -> dict[str, Any]:
    data = loads_jsonish(content)
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data
