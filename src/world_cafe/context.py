from __future__ import annotations

import json
from typing import Any, Literal

from world_cafe.state import TABLEMEMORY_USAGE_DESCRIPTION, CarryOverPacket, TableMemory, TableSpec, UserNote


MemoryView = Literal[
    "speaker",
    "host_opening",
    "host_synthesis",
    "host_closing",
    "packet",
    "harvest",
    "full",
]


def format_table_memory(memory: TableMemory, *, view: MemoryView = "host_synthesis") -> str:
    """Render table memory as a task-specific context view."""
    if view == "full":
        return _format_full_memory(memory)
    if view == "speaker":
        return _format_speaker_memory(memory)
    if view == "host_opening":
        return _format_host_opening_memory(memory)
    if view == "host_closing":
        return _format_host_closing_memory(memory)
    if view == "packet":
        return _format_packet_source_memory(memory)
    if view == "harvest":
        return _format_harvest_memory(memory)
    return _format_host_synthesis_memory(memory)


def format_table_spec(table_spec: TableSpec | dict[str, Any]) -> str:
    if not table_spec:
        return "None yet."
    return _compact_json(table_spec)


def parent_question_from_spec(question: str, table_spec: TableSpec | dict[str, Any] | None) -> str:
    if isinstance(table_spec, dict):
        parent = str(
            table_spec.get("parent_question")
            or table_spec.get("main_question")
            or table_spec.get("user_question")
            or ""
        ).strip()
        if parent:
            return parent
    return question


def format_carry_over_packet(packet: CarryOverPacket | dict[str, Any] | None) -> str:
    if not packet:
        return "暂无。"
    agent_memory = packet.get("agent_generated_memory")
    if isinstance(agent_memory, dict):
        insight = str(agent_memory.get("personal_insight") or "").strip()
    elif isinstance(agent_memory, str):
        insight = agent_memory.strip()
    else:
        insight = ""
    return f"personal_insight: {insight}" if insight else "暂无。"


def format_background(background_context: str) -> str:
    context = background_context.strip()
    if not context:
        return "None yet."
    max_chars = 12000
    if len(context) > max_chars:
        context = f"{context[:max_chars]}\n\n[Background material is too long and has been truncated to the first {max_chars} characters.]"
    return context


def format_user_notes(notes: list[UserNote] | list[dict[str, Any]] | None) -> str:
    if not notes:
        return "No user-marked notes submitted for this table/round."
    lines: list[str] = []
    for index, note in enumerate(notes[:24], start=1):
        text = str(note.get("text") or "").strip()
        if not text:
            continue
        if len(text) > 500:
            text = f"{text[:500].rstrip()}..."
        speaker = note.get("speaker_name") or note.get("speakerName") or note.get("speaker_id") or "unknown speaker"
        speech_id = note.get("speech_id") or note.get("speechId") or ""
        lines.append(f"{index}. [{speaker}; speech={speech_id}] {text}")
    return "\n".join(lines) or "No usable user-marked notes submitted for this table/round."


def format_closing_context(memory_update: dict[str, Any]) -> str:
    record = _formatmemory_from_update(memory_update)
    lines: list[str] = []
    for key, label in (
        ("repeated_themes", "Recurring themes"),
        ("minority_inspiring_views", "Minority but inspiring views"),
        ("unresolved_tensions", "Unresolved tensions"),
    ):
        items = _items(record.get(key), limit=5)
        if items:
            lines.append(f"{label}:")
            lines.extend(f"- {item}" for item in items)
    seeds = _items(memory_update.get("next_round_question_seeds") or memory_update.get("open_questions"), limit=3)
    if seeds:
        lines.append("Question seeds to carry forward:")
        lines.extend(f"- {item}" for item in seeds)
    return "\n".join(lines) or "This round's internal memory did not yield visible closing-note cues."


def _format_speaker_memory(memory: TableMemory) -> str:
    lines = [
        _line("桌子问题", memory.get("question")),
        _block("所有轮次 formatmemory", _formatmemory_digest(memory, limit=99), limit=99),
        _block("下一轮问题种子", memory.get("next_round_question_seeds"), limit=4),
    ]
    return _join(lines)


def _format_host_opening_memory(memory: TableMemory) -> str:
    lines = [
        _line("桌子问题", memory.get("question")),
        _block("所有轮次 formatmemory", _formatmemory_digest(memory, limit=99), limit=99),
        _block("下一轮问题种子", memory.get("next_round_question_seeds"), limit=4),
    ]
    return _join(lines)


def _format_host_synthesis_memory(memory: TableMemory) -> str:
    lines = [
        _line("tablememory 使用说明", _tablememory_usage_description(memory)),
        _line("桌子问题", memory.get("question")),
        _block("已完成轮次 formatmemory", _formatmemory_digest(memory, limit=4), limit=4),
        _block("下一轮问题种子", memory.get("next_round_question_seeds"), limit=4),
    ]
    return _join(lines)


def _format_host_closing_memory(memory: TableMemory) -> str:
    lines = [
        _line("桌子问题", memory.get("question")),
        _block("最近 formatmemory", _formatmemory_digest(memory, limit=1), limit=1),
        _block("下一轮问题种子", memory.get("next_round_question_seeds"), limit=3),
    ]
    return _join(lines)


def _format_packet_source_memory(memory: TableMemory) -> str:
    lines = [
        _line("来源桌问题", memory.get("question")),
        _block("来源桌最近 formatmemory", _formatmemory_digest(memory, limit=1), limit=1),
    ]
    return _join(lines)


def _format_harvest_memory(memory: TableMemory) -> str:
    lines = [
        _line("桌子问题", memory.get("question")),
        _block("formatmemory", _formatmemory_digest(memory, limit=4), limit=4),
        _block("Question seeds", memory.get("next_round_question_seeds"), limit=3),
    ]
    return _join(lines)


def _format_full_memory(memory: TableMemory) -> str:
    lines = [
        _line("桌子问题", memory.get("question")),
        _block("formatmemory", _formatmemory_digest(memory, limit=6), limit=6),
        _block("Next-round question seeds", memory.get("next_round_question_seeds"), limit=8),
    ]
    return _join(lines)


def _tablememory_usage_description(memory: TableMemory) -> str:
    return str(memory.get("tablememory_usage_description") or TABLEMEMORY_USAGE_DESCRIPTION)


def _formatmemory_digest(memory: TableMemory, *, limit: int, compact: bool = False) -> list[str]:
    records = memory.get("formatmemory") or []
    normalized = [_formatmemory_from_update({"formatmemory": item}) for item in records]
    normalized = [item for item in normalized if _has_formatmemory_content(item)]
    lines: list[str] = []
    for index, item in enumerate(normalized[-limit:], start=max(1, len(normalized) - limit + 1)):
        round_no = item.get("round_index") or index
        repeated = _inline_list(item.get("repeated_themes"))
        minority = _inline_list(item.get("minority_inspiring_views"))
        tensions = _inline_list(item.get("unresolved_tensions"))
        if compact:
            parts = [part for part in (repeated, minority, tensions) if part]
            lines.append(f"Round {round_no}: {' | '.join(parts) or 'None yet'}")
            continue
        parts = [f"Round {round_no}"]
        if repeated:
            parts.append(f"Recurring themes: {repeated}")
        if minority:
            parts.append(f"Minority signals: {minority}")
        if tensions:
            parts.append(f"Unresolved tensions: {tensions}")
        lines.append(" | ".join(parts))
    return lines


def _formatmemory_from_update(update: dict[str, Any]) -> dict[str, Any]:
    raw = update.get("formatmemory") if isinstance(update, dict) else {}
    if isinstance(raw, list):
        raw = raw[-1] if raw else {}
    if not isinstance(raw, dict):
        raw = {}
    source = raw or update
    return {
        "table_question": str(
            source.get("table_question")
            or source.get("question")
            or update.get("question")
            or ""
        ).strip(),
        "round_index": source.get("round_index") or update.get("round_index"),
        "repeated_themes": _items(
            source.get("repeated_themes"),
            limit=8,
        ),
        "minority_inspiring_views": _items(
            source.get("minority_inspiring_views")
            or source.get("minority_views")
            or source.get("minority_but_inspiring_views"),
            limit=8,
        ),
        "unresolved_tensions": _items(
            source.get("unresolved_tensions"),
            limit=8,
        ),
    }


def _has_formatmemory_content(record: dict[str, Any]) -> bool:
    return bool(
        record.get("table_question")
        or record.get("repeated_themes")
        or record.get("minority_inspiring_views")
        or record.get("unresolved_tensions")
    )


def _bridge_intent_from_memory(agent_memory: object) -> str:
    if isinstance(agent_memory, dict):
        insight = str(
            agent_memory.get("personal_insight")
            or agent_memory.get("personal_takeaway")
            or ""
        ).strip()
        if insight:
            return f"Carry this personal insight to the next table: {insight[:80]}"
    if isinstance(agent_memory, str) and agent_memory.strip():
        return f"Carry this personal insight to the next table: {agent_memory.strip()[:80]}"
    return ""


def _line(label: str, value: object) -> str:
    text = _text(value)
    return f"{label}: {text}" if text else ""


def _block(label: str, value: object, *, limit: int) -> str:
    items = _items(value, limit=limit)
    if not items:
        return ""
    return f"{label}:\n" + "\n".join(f"- {item}" for item in items)


def _items(value: object, *, limit: int) -> list[str]:
    if value in ("", None, [], {}):
        return []
    if isinstance(value, dict):
        items = [f"{key}: {item}" for key, item in value.items() if item not in (None, "", [], {})]
    elif isinstance(value, list):
        items = [str(item) for item in value]
    else:
        items = [str(value)]
    return [item.strip() for item in items if item and item.strip()][:limit]


def _inline_list(value: object, *, limit: int = 3) -> str:
    return "; ".join(_items(value, limit=limit))


def _text(value: object) -> str:
    if value in ("", None, [], {}):
        return ""
    if isinstance(value, str):
        return value.strip()
    return _compact_json(value)


def _join(lines: list[str]) -> str:
    visible = [line for line in lines if line.strip()]
    return "\n".join(visible) if visible else "None yet."


def _route_line(packet: CarryOverPacket | dict[str, Any]) -> str:
    agent_id = str(packet.get("agent_id") or "unknown agent")
    from_table = str(packet.get("from_table") or "?")
    to_table = str(packet.get("to_table") or "?")
    after_round = packet.get("after_round")
    round_text = f" after round {int(after_round) + 1}" if isinstance(after_round, int) else ""
    return f"{agent_id}: {from_table} -> {to_table}{round_text}"


def _anchor_text(anchor: object) -> str:
    if not isinstance(anchor, dict):
        return _text(anchor)
    parts = [
        str(anchor.get("table_id") or "").strip(),
        str(anchor.get("guiding_question") or anchor.get("question") or "").strip(),
        str(anchor.get("lens") or "").strip(),
        str(anchor.get("expert_skill") or "").strip(),
    ]
    text = " | ".join(part for part in parts if part)
    return text or _compact_json(anchor)


def _compact_json(value: Any) -> str:
    if value in ("", None, [], {}):
        return "None yet"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)
