from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from world_cafe.facilitator import facilitate_request
from world_cafe.graph import build_world_cafe_graph, create_initial_state
from world_cafe.llm import AnthropicCafeLLM
from world_cafe.profiles import build_default_agent_profiles, load_agent_profiles
from world_cafe.report import state_to_jsonable, write_outputs
from world_cafe.state import AgentProfile, WorldCafeState


load_dotenv()

STATIC_DIR = Path(__file__).with_name("static")


class FacilitateBody(BaseModel):
    request: str = Field(min_length=1)
    table_count: int = Field(default=4, ge=1, le=8)
    background_context: str = ""
    background_filename: str = ""


class TableQuestionBody(BaseModel):
    table_id: str
    question: str = Field(min_length=1)


class RunCreateBody(BaseModel):
    tables: list[TableQuestionBody] = Field(min_length=1, max_length=8)
    rounds: int = Field(default=3, ge=1, le=6)
    speakers_per_table: int = Field(default=3, ge=1, le=8)
    speeches_per_agent: int = Field(default=3, ge=1, le=8)
    host_assignments: dict[str, str] | None = None
    speaker_assignments: dict[str, list[str]] | None = None
    agents_file: str | None = None
    background_context: str = ""
    background_filename: str = ""


@dataclass
class RunSession:
    run_id: str
    state: WorldCafeState
    status: str = "pending"
    events: list[dict[str, Any]] = field(default_factory=list)
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)
    task: asyncio.Task | None = None
    final_state: WorldCafeState | None = None
    pause_requested: bool = False
    pause_active: bool = False
    pause_gate: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self) -> None:
        self.pause_gate.set()

    async def publish(self, event: dict[str, Any]) -> None:
        self.events.append(event)
        await self.queue.put(event)

    async def request_pause(self) -> None:
        if self.status not in {"pending", "running"}:
            return
        self.pause_requested = True
        self.pause_active = False
        self.pause_gate.clear()
        await self.publish(
            {
                "type": "pause_changed",
                "run_id": self.run_id,
                "status": "pause_requested",
            }
        )

    async def resume(self) -> None:
        if self.status not in {"pending", "running"}:
            return
        self.pause_requested = False
        self.pause_active = False
        self.pause_gate.set()
        await self.publish(
            {
                "type": "pause_changed",
                "run_id": self.run_id,
                "status": "running",
            }
        )

    async def wait_if_paused(self, _run_id: str) -> None:
        if not self.pause_requested:
            return
        if not self.pause_active:
            self.pause_active = True
            await self.publish(
                {
                    "type": "pause_changed",
                    "run_id": self.run_id,
                    "status": "paused",
                }
            )
        await self.pause_gate.wait()


app = FastAPI(title="Agent Cafe", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
RUNS: dict[str, RunSession] = {}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/config")
async def config() -> dict[str, Any]:
    return {
        "token_configured": bool(os.getenv("ANTHROPIC_AUTH_TOKEN")),
        "base_url": os.getenv("ANTHROPIC_BASE_URL", "http://143.198.222.179:8317"),
        "model": os.getenv("ANTHROPIC_MODEL", "gpt-5.5"),
        "default_rounds": int(os.getenv("WORLD_CAFE_ROUNDS", "3")),
        "default_table_count": int(os.getenv("WORLD_CAFE_TABLES", "4")),
        "default_speakers_per_table": int(os.getenv("WORLD_CAFE_SPEAKERS_PER_TABLE", "3")),
        "default_speeches_per_agent": int(os.getenv("WORLD_CAFE_SPEECHES_PER_AGENT", "3")),
    }


@app.get("/api/agents")
async def agents(count: int = 32, agents_file: str | None = None) -> dict[str, Any]:
    return {"agents": _load_agents_for_count(count, agents_file)}


@app.post("/api/facilitate")
async def facilitate(body: FacilitateBody) -> dict[str, Any]:
    try:
        llm = _build_llm(temperature=0.25, max_tokens=1200)
        return await facilitate_request(
            llm,
            body.request,
            table_count=body.table_count,
            background_context=body.background_context,
            background_filename=body.background_filename,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"facilitation failed: {exc}") from exc


@app.post("/api/runs")
async def create_run(body: RunCreateBody, background_tasks: BackgroundTasks) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    questions = {table.table_id: table.question for table in body.tables}
    table_count = len(body.tables)
    requested_count = table_count * (body.speakers_per_table + 1)
    agents = _load_agents_for_count(requested_count, body.agents_file)
    hosts, assignments = _build_requested_assignments(
        tables=body.tables,
        agents=agents,
        speakers_per_table=body.speakers_per_table,
        host_assignments=body.host_assignments,
        speaker_assignments=body.speaker_assignments,
    )
    try:
        state = create_initial_state(
            questions=questions,
            agents=agents,
            rounds=body.rounds,
            table_count=table_count,
            seats_per_table=body.speakers_per_table + 1,
            speeches_per_agent=body.speeches_per_agent,
            background_context=body.background_context,
            background_filename=body.background_filename,
            assignments=assignments,
            hosts=hosts,
            run_id=run_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session = RunSession(run_id=run_id, state=state)
    RUNS[run_id] = session
    background_tasks.add_task(_ensure_run_started, run_id)
    return _run_snapshot(session)


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    session = _get_session(run_id)
    return _run_snapshot(session)


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: str) -> StreamingResponse:
    session = _get_session(run_id)
    await _ensure_run_started(run_id)
    return StreamingResponse(_event_stream(session), media_type="text/event-stream")


@app.post("/api/runs/{run_id}/pause")
async def pause_run(run_id: str) -> dict[str, Any]:
    session = _get_session(run_id)
    await session.request_pause()
    return _run_snapshot(session)


@app.post("/api/runs/{run_id}/resume")
async def resume_run(run_id: str) -> dict[str, Any]:
    session = _get_session(run_id)
    await session.resume()
    return _run_snapshot(session)


async def _ensure_run_started(run_id: str) -> None:
    session = _get_session(run_id)
    if session.task is None:
        session.task = asyncio.create_task(_run_graph(session))


async def _run_graph(session: RunSession) -> None:
    session.status = "running"
    await session.publish({"type": "run_started", "run_id": session.run_id})
    try:
        llm = _build_llm(temperature=0.7, max_tokens=1600)
        graph = build_world_cafe_graph(llm, pause_check=session.wait_if_paused)
        final_state: WorldCafeState | None = None
        async for stream_type, data in _stream_graph(graph, session.state):
            if stream_type == "custom":
                await session.publish({"type": "trace", **data})
            elif stream_type == "values":
                final_state = data
        if final_state is None:
            raise RuntimeError("graph completed without a final state")
        session.final_state = final_state
        session.status = "done"
        report_path, trace_path = write_outputs(final_state)
        await session.publish(
            {
                "type": "run_complete",
                "run_id": session.run_id,
                "harvest": final_state.get("harvest", {}),
                "final_state": state_to_jsonable(final_state),
                "report_path": str(Path(report_path).resolve()),
                "trace_path": str(Path(trace_path).resolve()),
            }
        )
    except Exception as exc:
        session.status = "error"
        message = str(exc) or repr(exc)
        await session.publish({"type": "error", "message": message})
    finally:
        await session.queue.put({"type": "stream_closed"})


async def _stream_graph(graph: Any, state: WorldCafeState) -> AsyncIterator[tuple[str, Any]]:
    config = {"configurable": {"thread_id": state["run_id"]}}
    async for chunk in graph.astream(
        state,
        config=config,
        stream_mode=["custom", "values"],
        version="v2",
    ):
        if isinstance(chunk, dict) and "type" in chunk:
            yield chunk["type"], chunk["data"]
        elif isinstance(chunk, tuple) and len(chunk) == 2:
            yield chunk[0], chunk[1]


async def _event_stream(session: RunSession) -> AsyncIterator[str]:
    for event in session.events:
        yield _sse(event)
    while True:
        event = await session.queue.get()
        if event.get("type") == "stream_closed":
            yield _sse(event)
            break
        yield _sse(event)


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _run_snapshot(session: RunSession) -> dict[str, Any]:
    profiles = {agent["id"]: agent for agent in session.state["agent_profiles"]}
    return {
        "run_id": session.run_id,
        "status": session.status,
        "rounds": session.state["max_rounds"],
        "table_count": session.state["table_count"],
        "speakers_per_table": max(session.state["seats_per_table"] - 1, 1),
        "speeches_per_agent": session.state.get("speeches_per_agent", 3),
        "pause_requested": session.pause_requested,
        "pause_active": session.pause_active,
        "table_questions": session.state["table_questions"],
        "assignments": session.state["assignments"],
        "hosts": session.state["hosts"],
        "agent_profiles": profiles,
        "final_state": state_to_jsonable(session.final_state) if session.final_state else None,
    }


def _load_agents(path: str | None) -> list[AgentProfile] | None:
    if not path:
        default_path = Path("config/agents.yaml")
        if default_path.exists():
            return load_agent_profiles(default_path)
        return None
    return load_agent_profiles(path)


def _load_agents_for_count(count: int, path: str | None = None) -> list[AgentProfile]:
    loaded = _load_agents(path) or []
    profiles = list(loaded)
    existing_ids = {agent["id"] for agent in profiles}
    target_count = max(count, len(profiles), 1)
    for default_agent in build_default_agent_profiles(target_count + len(profiles)):
        if len(profiles) >= target_count:
            break
        if default_agent["id"] in existing_ids:
            continue
        profiles.append(default_agent)
        existing_ids.add(default_agent["id"])
    return profiles


def _build_requested_assignments(
    *,
    tables: list[TableQuestionBody],
    agents: list[AgentProfile],
    speakers_per_table: int,
    host_assignments: dict[str, str] | None,
    speaker_assignments: dict[str, list[str]] | None,
) -> tuple[dict[str, str], dict[str, list[str]]]:
    agent_ids = [agent["id"] for agent in agents]
    table_ids = [table.table_id for table in tables]
    hosts: dict[str, str] = {}
    assignments: dict[str, list[str]] = {}
    for index, table_id in enumerate(table_ids):
        default_host_index = len(table_ids) * speakers_per_table + index
        host_id = (host_assignments or {}).get(table_id) or agent_ids[default_host_index % len(agent_ids)]
        if host_id not in agent_ids:
            raise HTTPException(status_code=400, detail=f"unknown host id for {table_id}: {host_id}")
        speakers = list((speaker_assignments or {}).get(table_id, []))
        if not speakers:
            start = index * speakers_per_table
            speakers = [
                agent_ids[position % len(agent_ids)]
                for position in range(start, start + speakers_per_table)
            ]
        speakers = [agent_id for agent_id in dict.fromkeys(speakers) if agent_id != host_id]
        if not speakers:
            raise HTTPException(status_code=400, detail=f"{table_id} must have at least one speaking agent")
        unknown = [agent_id for agent_id in speakers if agent_id not in agent_ids]
        if unknown:
            raise HTTPException(status_code=400, detail=f"unknown speaker ids for {table_id}: {', '.join(unknown)}")
        hosts[table_id] = host_id
        assignments[table_id] = speakers
    return hosts, assignments


def _build_llm(*, temperature: float, max_tokens: int) -> AnthropicCafeLLM:
    return AnthropicCafeLLM.from_env(temperature=temperature, max_tokens=max_tokens)


def _get_session(run_id: str) -> RunSession:
    session = RUNS.get(run_id)
    if session is None:
        raise HTTPException(status_code=404, detail="run not found")
    return session


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Agent Cafe web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run("world_cafe.web:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
