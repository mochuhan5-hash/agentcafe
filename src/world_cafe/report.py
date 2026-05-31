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
        "## Tables",
        "",
    ]
    for table_id, memory in sorted(state.get("table_memories", {}).items()):
        lines.extend(
            [
                f"### {table_id}",
                "",
                f"**Question:** {memory['question']}",
                "",
                f"**Host:** {memory['host_id']}",
                "",
                memory.get("living_summary") or "",
                "",
                "**Key Insights**",
                "",
                *_bullet_lines(memory.get("key_insights", [])),
                "",
                "**Open Questions**",
                "",
                *_bullet_lines(memory.get("open_questions", [])),
                "",
                "**Tensions**",
                "",
                *_bullet_lines(memory.get("tensions", [])),
                "",
            ]
        )
    lines.extend(["## Rotation History", ""])
    for record in state.get("rotation_history", []):
        lines.extend(
            [
                f"- after round {record['after_round_index'] + 1}: {record['assignments']}",
            ]
        )
    lines.extend(["", "## Trace Summary", ""])
    for event in state.get("trace", []):
        lines.append(f"- {event['timestamp']} [{event['stage']}] {event['message']}")
    return "\n".join(lines).strip() + "\n"


def state_to_jsonable(state: WorldCafeState) -> dict[str, Any]:
    return json.loads(json.dumps(state, ensure_ascii=False))


def _bullet_lines(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- 暂无"]
