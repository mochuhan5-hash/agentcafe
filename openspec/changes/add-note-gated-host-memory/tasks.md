## 1. Backend Note Checkpoint

- [x] 1.1 Add a `UserNote` state/session shape with table id, round index, text, source speaker, source speech id, and timestamp.
- [x] 1.2 Add a note checkpoint callback to the graph after table speaking contributions and before host synthesis.
- [x] 1.3 Keep dry-run/CLI behavior non-blocking with an empty-note callback.
- [x] 1.4 Add backend endpoints for submitting notes and continuing a note checkpoint.
- [x] 1.5 Store notes by run/table/round and return them to the waiting graph checkpoint.

## 2. Host Memory Context

- [x] 2.1 Pass relevant user notes into `host_synthesis_prompt`.
- [x] 2.2 Update the host synthesis prompt priority order: user-marked design notes first, host historical memory second, current conversation third.
- [x] 2.3 Ensure host closing remarks are generated from note-informed memory updates.
- [x] 2.4 Preserve internal/visible separation: notes inform memory but are not mechanically copied into closing remarks.

## 3. Frontend Interaction

- [x] 3.1 Show a system-driven “complete notes” pause after each table discussion finishes speaking turns.
- [x] 3.2 Enable the user to submit current notebook entries for the active table/round.
- [x] 3.3 Add a “continue after notes” action that submits notes and releases the backend checkpoint.
- [x] 3.4 Keep manual pause/resume for ad hoc annotation.

## 4. Verification

- [x] 4.1 Add tests for note checkpoint events and backend note submission.
- [x] 4.2 Add tests that host synthesis receives note context.
- [x] 4.3 Run Python tests.
- [x] 4.4 Run frontend syntax checks.
- [x] 4.5 Validate OpenSpec change strictly.
