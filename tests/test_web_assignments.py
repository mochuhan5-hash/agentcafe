from pathlib import Path
import asyncio

import pytest
from fastapi import BackgroundTasks

from world_cafe.profiles import build_default_agent_profiles
from world_cafe.web import (
    RUNS,
    NoteCheckpointContinueBody,
    RunCreateBody,
    TableQuestionBody,
    UserNoteBody,
    _build_requested_assignments,
    continue_note_checkpoint,
    create_run,
    pause_run,
    resume_run,
)


def test_default_web_assignments_keep_first_four_agents_as_speakers() -> None:
    tables = [
        TableQuestionBody(table_id=f"table_{index:02d}", question=f"q{index}")
        for index in range(1, 5)
    ]

    hosts, assignments = _build_requested_assignments(
        tables=tables,
        agents=build_default_agent_profiles(16),
        speakers_per_table=3,
        host_assignments=None,
        speaker_assignments=None,
    )

    assert assignments["table_01"] == ["agent_01", "agent_02", "agent_03"]
    assert assignments["table_02"][0] == "agent_04"
    assert hosts["table_01"] == "agent_13"
    assert "agent_01" not in hosts.values()


@pytest.mark.asyncio
async def test_create_run_preserves_background_for_discussion_prompts() -> None:
    body = RunCreateBody(
        tables=[TableQuestionBody(table_id="table_01", question="如何设计共创流程？")],
        rounds=1,
        speakers_per_table=1,
        background_context="# 项目背景\n需要服务老龄社区。",
        background_filename="brief.md",
    )

    snapshot = await create_run(body, BackgroundTasks())

    try:
        state = RUNS[snapshot["run_id"]].state
        assert state["background_context"] == "# 项目背景\n需要服务老龄社区。"
        assert state["background_filename"] == "brief.md"
    finally:
        RUNS.pop(snapshot["run_id"], None)


def test_static_app_sends_uploaded_background_to_facilitate_and_run() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "src/world_cafe/static/index.html").read_text(encoding="utf-8")
    js = (root / "src/world_cafe/static/app.js").read_text(encoding="utf-8")

    assert 'id="backgroundFile"' in html
    assert "background_context: backgroundContext" in js
    assert "background_filename: backgroundFilename" in js
    assert "backgroundFileInput.addEventListener" in js


def test_create_run_accepts_speeches_per_agent() -> None:
    body = RunCreateBody(
        tables=[TableQuestionBody(table_id="table_01", question="如何设计共创流程？")],
        rounds=1,
        speakers_per_table=1,
        speeches_per_agent=4,
    )

    assert body.speeches_per_agent == 4


def test_static_app_exposes_speech_count_pause_and_notebook_controls() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "src/world_cafe/static/index.html").read_text(encoding="utf-8")
    js = (root / "src/world_cafe/static/app.js").read_text(encoding="utf-8")
    css = (root / "src/world_cafe/static/styles.css").read_text(encoding="utf-8")

    assert 'id="speechesPerAgent"' in html
    assert 'id="pauseBtn"' in html
    assert 'id="notebookList"' in html
    assert "设计机会洞察" in html
    assert html.count("写下一个设计机会") == 4
    assert "/static/app.js?v=" in html
    assert "/static/styles.css?v=" in html
    assert "speeches_per_agent: getSpeechesPerAgent()" in js
    assert "/pause" in js
    assert "/resume" in js
    assert "window.getSelection" in js
    assert "pendingNoteSelection" in js
    assert "noteCheckpointPanel" in js
    assert "isNoteTakingActive" in js
    assert "/note-checkpoint/continue" in js
    assert 'action: "switch_table"' in js
    assert "换桌" in js
    assert "table_id: entry.tableId" in js
    assert "round_index: Number(entry.roundIndex)" in js
    assert "const tableId = speech.dataset.tableId" in js
    assert "extractContents" in js
    assert "speakerName" in js
    assert 'id="noteCheckpointPanel"' in html
    assert 'id="continueNotesBtn"' in html
    assert "完成本桌笔记后换桌" in html
    assert "点击“换桌”后桌长才会生成本轮记忆" in html
    assert "user-note-highlight" in css
    assert "note-checkpoint-panel" in css
    assert "background: #ffe66f !important" in css
    assert "notebook-entry" in css
    assert ".round-list" in css
    assert "overflow-y: auto" in css
    assert "overscroll-behavior: contain" in css
    assert "scrollbar-gutter: stable" in css
    assert "scrollTableToBottom" in js
    assert "renderHostMemoryTooltip" in js
    assert "renderMemoryRound" in js
    assert "重复主题" in js
    assert "少数启发" in js
    assert "未解张力" in js
    assert ".memory-round" in css
    assert ".memory-list" in css


@pytest.mark.asyncio
async def test_pause_and_resume_update_run_snapshot_without_losing_context() -> None:
    body = RunCreateBody(
        tables=[TableQuestionBody(table_id="table_01", question="如何继续讨论？")],
        rounds=1,
        speakers_per_table=1,
    )

    snapshot = await create_run(body, BackgroundTasks())
    run_id = snapshot["run_id"]

    try:
        paused = await pause_run(run_id)
        assert paused["pause_requested"] is True
        assert paused["table_questions"] == snapshot["table_questions"]

        resumed = await resume_run(run_id)
        assert resumed["pause_requested"] is False
        assert resumed["pause_active"] is False
        assert resumed["table_questions"] == snapshot["table_questions"]
    finally:
        RUNS.pop(run_id, None)


@pytest.mark.asyncio
async def test_note_checkpoint_continue_endpoint_releases_waiting_session() -> None:
    body = RunCreateBody(
        tables=[TableQuestionBody(table_id="table_01", question="如何保留用户笔记？")],
        rounds=1,
        speakers_per_table=1,
    )

    snapshot = await create_run(body, BackgroundTasks())
    run_id = snapshot["run_id"]
    session = RUNS[run_id]
    waiter = asyncio.create_task(session.wait_for_notes(run_id, "table_01", 0))

    try:
        for _ in range(20):
            if session.note_checkpoint_meta:
                break
            await asyncio.sleep(0)
        assert session.note_checkpoint_meta
        checkpoint_id = next(iter(session.note_checkpoint_meta))

        result = await continue_note_checkpoint(
            run_id,
            NoteCheckpointContinueBody(
                checkpoint_id=checkpoint_id,
                table_id="table_01",
                round_index=0,
                notes=[
                    UserNoteBody(
                        id="note-1",
                        text="用户显式标记的设计机会。",
                        table_id="table_01",
                        round_index=0,
                        speaker_name="Agent One",
                        speaker_id="agent_01",
                        speech_id="speech-1",
                        speech_target_id="mark-1",
                        created_at="10:00",
                    ),
                    UserNoteBody(
                        id="note-other-table",
                        text="不应混入其它桌。",
                        table_id="table_02",
                        round_index=0,
                    ),
                ],
            ),
        )
        notes = await asyncio.wait_for(waiter, timeout=1)

        assert result["status"] == "notes_submitted"
        assert result["action"] == "switch_table"
        assert result["note_count"] == 1
        assert notes[0]["text"] == "用户显式标记的设计机会。"
        assert session.submitted_notes["table_01:0"][0]["speaker_id"] == "agent_01"
        assert checkpoint_id not in session.note_checkpoint_meta
    finally:
        if not waiter.done():
            waiter.cancel()
        RUNS.pop(run_id, None)
