from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from world_cafe.state import WorldCafeState


def write_outputs(state: WorldCafeState, output_dir: str | Path = "runs") -> tuple[Path, Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = state["run_id"]
    report_path = out_dir / f"{run_id}.md"
    trace_path = out_dir / f"{run_id}.trace.json"
    report_path.write_text(render_markdown_report(state), encoding="utf-8")
    trace_path.write_text(
        json.dumps(state.get("trace", []), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report_path, trace_path


def render_markdown_report(state: WorldCafeState) -> str:
    lines: list[str] = [
        f"# World Cafe Harvest: {state['run_id']}",
        "",
        "## Background",
        "",
        state.get("background_filename") or "No background file.",
        "",
        "## Global Harvest",
        "",
        state.get("harvest", {}).get("content", "No harvest generated."),
        "",
        "## Table Round Transcripts",
        "",
    ]
    outputs = sorted(
        state.get("table_round_outputs", []),
        key=lambda o: (o.get("table_id", ""), o.get("round_index", 0)),
    )
    for output in outputs:
        table_id = output.get("table_id", "")
        round_idx = int(output.get("round_index", 0)) + 1
        question = output.get("question", "")
        lines.extend([f"### {table_id} · Round {round_idx}", "", f"**Table question:** {question}", ""])
        for c in output.get("contributions", []):
            name = c.get("agent_name", "")
            content = str(c.get("content") or "").strip()
            lines.append(f"- **{name}**：{content}")
        # User notes
        notes = output.get("user_notes") or []
        if notes:
            lines.extend(["", "**User notes:**", ""])
            for note in notes:
                text = str(note.get("text") or "").strip()
                speaker = note.get("speaker_name") or note.get("speaker_id") or ""
                if text:
                    lines.append(f"- [{speaker}] {text}")
        lines.append("")
    # Table Memory summary
    lines.extend(["## Table Memory (Final Accumulated)", ""])
    for table_id, memory in sorted(state.get("table_memories", {}).items()):
        lines.extend([f"### {table_id}", "", f"**Question:** {memory.get('question', '')}", ""])
        for record in memory.get("formatmemory", []):
            round_no = record.get("round_index", "?")
            lines.append(f"**Round {round_no}:**")
            lines.extend([f"- Recurring theme: {t}" for t in record.get("repeated_themes", [])])
            lines.extend([f"- Minority signal: {t}" for t in record.get("minority_inspiring_views", [])])
            lines.extend([f"- Unresolved tension: {t}" for t in record.get("unresolved_tensions", [])])
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def state_to_jsonable(state: WorldCafeState) -> dict[str, Any]:
    return json.loads(json.dumps(state, ensure_ascii=False))


def _bullet_lines(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- None yet"]
