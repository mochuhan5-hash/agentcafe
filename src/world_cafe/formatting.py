from __future__ import annotations

import re


DESIGN_OPPORTUNITY_TERMS = (
    "design opportunity",
    "new design opportunity",
    "opportunity hypothesis",
    "opportunity signal",
    "potential opportunity",
    "opportunity",
    "opportunities",
)

_TERM_PATTERN = re.compile(
    "|".join(re.escape(term) for term in DESIGN_OPPORTUNITY_TERMS),
    flags=re.IGNORECASE,
)
_SENTENCE_PATTERN = re.compile(
    r"([^。！？!?；;\n]*(?:"
    + "|".join(re.escape(term) for term in DESIGN_OPPORTUNITY_TERMS)
    + r")[^。！？!?；;\n]*(?:[。！？!?；;]|$))",
    flags=re.IGNORECASE,
)


def emphasize_design_opportunities(text: str) -> str:
    """Bold visible sentences that explicitly mention design opportunities."""
    if not text or not _TERM_PATTERN.search(text):
        return text
    blocks = text.split("```")
    for index in range(0, len(blocks), 2):
        blocks[index] = "\n".join(_emphasize_line(line) for line in blocks[index].splitlines())
    return "```".join(blocks)


def _emphasize_line(line: str) -> str:
    if not _TERM_PATTERN.search(line) or "**" in line:
        return line
    if line.lstrip().startswith("#"):
        return line
    match = re.match(r"^(\s*(?:[-*]\s+|\d+\.\s+)?)", line)
    prefix = match.group(1) if match else ""
    body = line[len(prefix) :]
    return prefix + _SENTENCE_PATTERN.sub(_bold_match, body)


def _bold_match(match: re.Match[str]) -> str:
    sentence = match.group(1)
    leading = sentence[: len(sentence) - len(sentence.lstrip())]
    trailing = sentence[len(sentence.rstrip()) :]
    core = sentence.strip()
    if not core:
        return sentence
    return f"{leading}**{core}**{trailing}"
