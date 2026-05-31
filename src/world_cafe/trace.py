from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from world_cafe.state import TraceEvent


def make_event(stage: str, message: str, **metadata: Any) -> TraceEvent:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "message": message,
        "metadata": metadata,
    }


def emit_stream_event(event: TraceEvent) -> None:
    try:
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
        writer(event)
    except Exception:
        return
