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
from world_cafe.llm import OpenAICafeLLM, base_url_from_env, configured_auth_token_count, model_from_env
from world_cafe.profiles import build_default_agent_profiles, load_agent_profiles
from world_cafe.report import state_to_jsonable, write_outputs
from world_cafe.state import AgentProfile, UserNote, WorldCafeState


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
    parent_question: str | None = None
    expert_skill: str | None = None
    expert_rationale: str | None = None
    lens: str | None = None
    guiding_question: str | None = None
    why_this_matters: str | None = None
    evidence_basis: list[str] | None = None
    avoid_solution_bias: str | None = None
    round_subquestions: dict[str, list[str]] | None = None
    agent_system_prompt: str | None = None


class RunCreateBody(BaseModel):
    tables: list[TableQuestionBody] = Field(min_length=1, max_length=8)
    rounds: int = Field(default=3, ge=1, le=8)
    speakers_per_table: int = Field(default=3, ge=1, le=8)
    speeches_per_agent: int = Field(default=3, ge=1, le=8)
    host_assignments: dict[str, str] | None = None
    speaker_assignments: dict[str, list[str]] | None = None
    agents_file: str | None = None
    background_context: str = ""
    background_filename: str = ""


class UserNoteBody(BaseModel):
    id: str = ""
    text: str = ""
    table_id: str = ""
    round_index: int | None = None
    speaker_name: str = ""
    speaker_id: str = ""
    speech_id: str = ""
    speech_target_id: str = ""
    created_at: str = ""


class NoteCheckpointContinueBody(BaseModel):
    checkpoint_id: str = Field(min_length=1)
    table_id: str = Field(min_length=1)
    round_index: int = Field(ge=0)
    notes: list[UserNoteBody] = Field(default_factory=list)
    action: str = "switch_table"


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
    note_checkpoints: dict[str, asyncio.Future[list[UserNote]]] = field(default_factory=dict)
    note_checkpoint_meta: dict[str, dict[str, Any]] = field(default_factory=dict)
    submitted_notes: dict[str, list[UserNote]] = field(default_factory=dict)

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

    async def wait_for_notes(self, _run_id: str, table_id: str, round_index: int) -> list[UserNote]:
        checkpoint_id = f"{table_id}:r{round_index + 1}:{uuid.uuid4().hex[:8]}"
        future: asyncio.Future[list[UserNote]] = asyncio.get_running_loop().create_future()
        metadata = {
            "checkpoint_id": checkpoint_id,
            "run_id": self.run_id,
            "table_id": table_id,
            "round_index": round_index,
            "continue_action": "switch_table",
            "checkpoint_reason": "host_memory_before_table_switch",
        }
        self.note_checkpoints[checkpoint_id] = future
        self.note_checkpoint_meta[checkpoint_id] = metadata
        await self.publish(
            {
                "type": "note_checkpoint",
                "status": "waiting_for_notes",
                **metadata,
            }
        )
        try:
            notes = await future
            self.submitted_notes[_note_key(table_id, round_index)] = notes
            await self.publish(
                {
                    "type": "note_checkpoint",
                    "status": "notes_submitted",
                    "continue_action": "switch_table",
                    "note_count": len(notes),
                    **metadata,
                }
            )
            return notes
        finally:
            self.note_checkpoints.pop(checkpoint_id, None)
            self.note_checkpoint_meta.pop(checkpoint_id, None)

    async def submit_notes(self, checkpoint_id: str, notes: list[UserNote]) -> bool:
        future = self.note_checkpoints.get(checkpoint_id)
        if future is None or future.done():
            return False
        future.set_result(notes)
        return True


app = FastAPI(title="Agent Cafe", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
RUNS: dict[str, RunSession] = {}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/config")
async def config() -> dict[str, Any]:
    token_count = configured_auth_token_count()
    return {
        "token_configured": token_count > 0,
        "token_count": token_count,
        "base_url": base_url_from_env(),
        "model": model_from_env(),
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
        timeout = _facilitation_timeout()
        llm = _build_harvest_llm(temperature=0.25, max_tokens=500, timeout=timeout)
        return await asyncio.wait_for(
            facilitate_request(
                llm,
                body.request,
                table_count=body.table_count,
                background_context=body.background_context,
                background_filename=body.background_filename,
            ),
            timeout=timeout + 5.0,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=f"facilitation timed out while waiting for the model gateway: {exc}",
        ) from exc
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
            table_specs=_table_specs_from_request(body.tables),
            table_question_plan={"tables": [_table_spec_from_body(table) for table in body.tables]},
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


@app.post("/api/runs/{run_id}/note-checkpoint/continue")
async def continue_note_checkpoint(run_id: str, body: NoteCheckpointContinueBody) -> dict[str, Any]:
    session = _get_session(run_id)
    metadata = session.note_checkpoint_meta.get(body.checkpoint_id)
    if metadata is None:
        raise HTTPException(status_code=409, detail="note checkpoint is no longer active")
    if metadata["table_id"] != body.table_id or metadata["round_index"] != body.round_index:
        raise HTTPException(status_code=400, detail="note checkpoint table/round mismatch")
    notes = _normalize_user_notes(body)
    accepted = await session.submit_notes(body.checkpoint_id, notes)
    if not accepted:
        raise HTTPException(status_code=409, detail="note checkpoint is no longer accepting notes")
    return {
        "run_id": run_id,
        "checkpoint_id": body.checkpoint_id,
        "table_id": body.table_id,
        "round_index": body.round_index,
        "status": "notes_submitted",
        "action": body.action or "switch_table",
        "note_count": len(notes),
    }


async def _ensure_run_started(run_id: str) -> None:
    session = _get_session(run_id)
    if session.task is None:
        session.task = asyncio.create_task(_run_graph(session))


async def _run_graph(session: RunSession) -> None:
    session.status = "running"
    await session.publish({"type": "run_started", "run_id": session.run_id})
    try:
        llm = _build_llm(temperature=0.7, max_tokens=1600)
        graph = build_world_cafe_graph(
            llm,
            pause_check=session.wait_if_paused,
            note_checkpoint=session.wait_for_notes,
        )
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
        "pending_note_checkpoints": list(session.note_checkpoint_meta.values()),
        "table_questions": session.state["table_questions"],
        "table_specs": session.state.get("table_specs", {}),
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


def _note_key(table_id: str, round_index: int) -> str:
    return f"{table_id}:{round_index}"


def _normalize_user_notes(body: NoteCheckpointContinueBody) -> list[UserNote]:
    notes: list[UserNote] = []
    for note in body.notes:
        text = note.text.strip()
        if not text:
            continue
        note_table_id = note.table_id or body.table_id
        note_round_index = body.round_index if note.round_index is None else note.round_index
        if note_table_id != body.table_id or note_round_index != body.round_index:
            continue
        notes.append(
            {
                "id": note.id,
                "text": text,
                "table_id": body.table_id,
                "round_index": body.round_index,
                "speaker_name": note.speaker_name,
                "speaker_id": note.speaker_id,
                "speech_id": note.speech_id,
                "speech_target_id": note.speech_target_id,
                "created_at": note.created_at,
            }
        )
    return notes


def _table_specs_from_request(tables: list[TableQuestionBody]) -> dict[str, dict[str, Any]]:
    return {table.table_id: _table_spec_from_body(table) for table in tables}


def _table_spec_from_body(table: TableQuestionBody) -> dict[str, Any]:
    return {
        "table_id": table.table_id,
        "parent_question": table.parent_question or "",
        "question": table.question,
        "guiding_question": table.guiding_question or table.question,
        "expert_skill": table.expert_skill or "mixed",
        "expert_rationale": table.expert_rationale or "",
        "lens": table.lens or "reframing",
        "why_this_matters": table.why_this_matters or "",
        "evidence_basis": table.evidence_basis or [],
        "avoid_solution_bias": table.avoid_solution_bias or "",
        "round_subquestions": table.round_subquestions or {},
        "agent_system_prompt": table.agent_system_prompt or "",
    }


def _facilitation_timeout() -> float:
    return float(os.getenv("WORLD_CAFE_FACILITATION_TIMEOUT", os.getenv("WORLD_CAFE_LLM_TIMEOUT", "180")))


def _build_llm(*, temperature: float, max_tokens: int, timeout: float | None = None) -> OpenAICafeLLM:
    return OpenAICafeLLM.from_env(temperature=temperature, max_tokens=max_tokens, timeout=timeout)


def _build_harvest_llm(*, temperature: float, max_tokens: int, timeout: float | None = None) -> OpenAICafeLLM:
    """Use HARVEST_* env vars if set, otherwise fall back to default."""
    base_url = os.getenv("HARVEST_BASE_URL")
    api_key = os.getenv("HARVEST_API_KEY")
    if base_url and api_key:
        model = os.getenv("HARVEST_MODEL") or model_from_env()
        return OpenAICafeLLM(
            auth_token=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout if timeout is not None else float(os.getenv("WORLD_CAFE_LLM_TIMEOUT", "180")),
            concurrency=1,
        )
    return _build_llm(temperature=temperature, max_tokens=max_tokens, timeout=timeout)


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
