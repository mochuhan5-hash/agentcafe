# Change: Add Note-Gated Table Host Memory

## Why

User-marked notes currently live in the frontend notebook only. They are useful as explicit design insight / design opportunity records, but table hosts do not receive them when generating table-level intrinsic memory.

This misses an important World Cafe interaction: after a small-table discussion, participants often mark, cluster, or harvest important traces before the host turns conversation into reusable memory. The system should pause after table discussion, let the user finish notes, then synthesize host memory using those notes as the highest-priority evidence.

## What Changes

- Add a per-table, per-round note checkpoint after speaking-agent discussion and before table host memory synthesis.
- Let the frontend show a clear pause state: “complete notes, then continue.”
- Let the frontend submit notebook notes to the backend with table/round/speech metadata.
- Store submitted notes in the run session and route relevant notes into `host_synthesis_prompt`.
- Update table host synthesis so user-marked design notes have the highest priority, followed by host historical memory and current conversation.
- Keep non-web/dry-run flows non-blocking by using an empty-note fallback when no note gate is configured.
- Generate host closing remarks only after note-informed memory synthesis completes.

## Impact

- Affected specs: `agent-orchestration`, `agent-status-ui`
- Affected code:
  - `src/world_cafe/state.py`
  - `src/world_cafe/graph.py`
  - `src/world_cafe/prompts.py`
  - `src/world_cafe/web.py`
  - `src/world_cafe/static/app.js`
  - `src/world_cafe/static/index.html`
  - `src/world_cafe/static/styles.css`
  - tests under `tests/`

## Compatibility

- Existing dry-run, CLI, and tests should continue without manual note input.
- Existing notebook selection/highlight behavior remains, but notes become backend-visible when submitted at a checkpoint.
- Existing pause/resume controls should remain usable, but the note checkpoint is a distinct system-driven pause with an explicit “continue after notes” action.
