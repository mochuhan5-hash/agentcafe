from __future__ import annotations


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
