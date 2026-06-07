from __future__ import annotations

import json
from typing import Any, Literal

from world_cafe.state import CarryOverPacket, TableMemory, TableSpec, UserNote


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
        return "暂无。"
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
    agent = packet.get("agent") if isinstance(packet.get("agent"), dict) else {}
    agent_id = str(agent.get("id") or packet.get("agent_id") or "unknown agent")
    agent_name = str(agent.get("name") or agent_id)
    skills = agent.get("skills") if isinstance(agent.get("skills"), list) else []
    skill_text = "、".join(str(skill) for skill in skills if str(skill).strip()) or "未填写"
    route = _route_line(packet)
    lines = [
        f"迁移路径：{route}",
        f"agent：{agent_name} ({agent_id}) | skills: {skill_text}",
        _block("个人迁移洞察", packet.get("agent_generated_memory"), limit=4),
        _line("迁移意图", _bridge_intent_from_memory(packet.get("agent_generated_memory"))),
    ]
    return _join(lines)


def format_background(background_context: str) -> str:
    context = background_context.strip()
    if not context:
        return "暂无。"
    max_chars = 12000
    if len(context) > max_chars:
        context = f"{context[:max_chars]}\n\n[背景材料过长，已截断到前 {max_chars} 字符。]"
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
        ("repeated_themes", "重复主题"),
        ("minority_inspiring_views", "少数但有启发的观点"),
        ("unresolved_tensions", "未解决张力"),
    ):
        items = _items(record.get(key), limit=5)
        if items:
            lines.append(f"{label}：")
            lines.extend(f"- {item}" for item in items)
    seeds = _items(memory_update.get("next_round_question_seeds") or memory_update.get("open_questions"), limit=3)
    if seeds:
        lines.append("可带走的问题种子：")
        lines.extend(f"- {item}" for item in seeds)
    return "\n".join(lines) or "本轮内在记忆没有提取到可见结束语线索。"


def _format_speaker_memory(memory: TableMemory) -> str:
    lines = [
        _line("桌子问题", memory.get("question")),
        _line("活记忆摘要", memory.get("living_summary")),
        _block("最近 formatmemory", _formatmemory_digest(memory, limit=2, compact=True), limit=2),
        _block("下一轮问题种子", memory.get("next_round_question_seeds"), limit=2),
    ]
    return _join(lines)


def _format_host_opening_memory(memory: TableMemory) -> str:
    lines = [
        _line("桌子问题", memory.get("question")),
        _line("活记忆摘要", memory.get("living_summary")),
        _block("已记录 formatmemory", _formatmemory_digest(memory, limit=3), limit=3),
        _block("下一轮问题种子", memory.get("next_round_question_seeds"), limit=4),
    ]
    return _join(lines)


def _format_host_synthesis_memory(memory: TableMemory) -> str:
    lines = [
        _line("桌子问题", memory.get("question")),
        _line("活记忆摘要", memory.get("living_summary")),
        _block("已完成轮次 formatmemory", _formatmemory_digest(memory, limit=4), limit=4),
        _block("下一轮问题种子", memory.get("next_round_question_seeds"), limit=4),
    ]
    return _join(lines)


def _format_host_closing_memory(memory: TableMemory) -> str:
    lines = [
        _line("桌子问题", memory.get("question")),
        _line("活记忆摘要", memory.get("living_summary")),
        _block("最近 formatmemory", _formatmemory_digest(memory, limit=1), limit=1),
        _block("下一轮问题种子", memory.get("next_round_question_seeds"), limit=3),
    ]
    return _join(lines)


def _format_packet_source_memory(memory: TableMemory) -> str:
    lines = [
        _line("来源桌问题", memory.get("question")),
        _line("来源桌活记忆摘要", memory.get("living_summary")),
        _block("来源桌最近 formatmemory", _formatmemory_digest(memory, limit=1), limit=1),
    ]
    return _join(lines)


def _format_harvest_memory(memory: TableMemory) -> str:
    lines = [
        _line("桌子问题", memory.get("question")),
        _line("活记忆摘要", memory.get("living_summary")),
        _block("formatmemory", _formatmemory_digest(memory, limit=4), limit=4),
        _block("问题种子", memory.get("next_round_question_seeds"), limit=3),
    ]
    return _join(lines)


def _format_full_memory(memory: TableMemory) -> str:
    lines = [
        _line("桌子问题", memory.get("question")),
        _line("活记忆摘要", memory.get("living_summary")),
        _block("formatmemory", _formatmemory_digest(memory, limit=6), limit=6),
        _block("下一轮问题种子", memory.get("next_round_question_seeds"), limit=8),
    ]
    return _join(lines)


def _formatmemory_digest(memory: TableMemory, *, limit: int, compact: bool = False) -> list[str]:
    records = memory.get("formatmemory") or []
    if not records:
        records = [
            (item.get("table_memory_update") or {}).get("formatmemory") or item.get("formatmemory") or {}
            for item in memory.get("rounds", [])
        ]
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
            lines.append(f"Round {round_no}: {' | '.join(parts) or '暂无'}")
            continue
        parts = [f"Round {round_no}"]
        if repeated:
            parts.append(f"重复主题: {repeated}")
        if minority:
            parts.append(f"少数启发: {minority}")
        if tensions:
            parts.append(f"未解张力: {tensions}")
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
            source.get("repeated_themes")
            or source.get("table_question_recurring_themes")
            or update.get("stable_patterns")
            or update.get("recurring_patterns_across_rounds")
            or update.get("key_insights"),
            limit=8,
        ),
        "minority_inspiring_views": _items(
            source.get("minority_inspiring_views")
            or source.get("minority_views")
            or source.get("minority_but_inspiring_views")
            or update.get("incomplete_or_weak_patterns")
            or update.get("emerging_or_fading_signals"),
            limit=8,
        ),
        "unresolved_tensions": _items(
            source.get("unresolved_tensions")
            or update.get("unresolved_tensions_over_time")
            or update.get("tensions"),
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
        question = str(agent_memory.get("carry_forward_question") or "").strip()
        insight = str(
            agent_memory.get("personal_insight")
            or agent_memory.get("personal_takeaway")
            or ""
        ).strip()
        if question:
            return f"带到下一桌测试：{question}"
        if insight:
            return f"带到下一桌测试这条个人洞察：{insight[:80]}"
    if isinstance(agent_memory, str) and agent_memory.strip():
        return f"带到下一桌测试这条个人洞察：{agent_memory.strip()[:80]}"
    return ""


def _round_digest(memory: TableMemory, *, limit: int, compact: bool = False) -> list[str]:
    rounds = memory.get("rounds", [])
    if not rounds:
        return []
    lines: list[str] = []
    for item in rounds[-limit:]:
        round_no = int(item.get("round_index", 0)) + 1
        update = item.get("table_memory_update") or {}
        synthesis = str(update.get("synthesis") or item.get("synthesis") or "").strip()
        delta = str(update.get("round_pattern_delta") or "").strip()
        if compact:
            parts = [part for part in (synthesis, delta) if part]
            lines.append(f"Round {round_no}: {' | '.join(parts) or '暂无摘要'}")
            continue
        parts = [f"Round {round_no}: {synthesis or '暂无摘要'}"]
        for label, value in (
            ("累计演化", update.get("cumulative_pattern_evolution")),
            ("本轮位置/变化", delta),
            ("洞察", item.get("key_insights")),
            ("张力", item.get("tensions")),
            ("开放问题", item.get("open_questions")),
            ("成形", update.get("stable_patterns")),
            ("不完善", update.get("incomplete_or_weak_patterns")),
            ("冲突", update.get("contested_points")),
            ("盲点", update.get("blind_spots_or_ambiguities")),
        ):
            text = _inline_list(value) if isinstance(value, list) else str(value or "").strip()
            if text:
                parts.append(f"{label}: {text}")
        lines.append(" | ".join(parts))
    return lines


def _line(label: str, value: object) -> str:
    text = _text(value)
    return f"{label}：{text}" if text else ""


def _block(label: str, value: object, *, limit: int) -> str:
    items = _items(value, limit=limit)
    if not items:
        return ""
    return f"{label}：\n" + "\n".join(f"- {item}" for item in items)


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
    return "；".join(_items(value, limit=limit))


def _text(value: object) -> str:
    if value in ("", None, [], {}):
        return ""
    if isinstance(value, str):
        return value.strip()
    return _compact_json(value)


def _join(lines: list[str]) -> str:
    visible = [line for line in lines if line.strip()]
    return "\n".join(visible) if visible else "暂无。"


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
        return "暂无"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)
