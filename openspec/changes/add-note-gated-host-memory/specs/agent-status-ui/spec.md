## ADDED Requirements

### Requirement: Note Checkpoint UI
The frontend SHALL guide the user through a system-driven table-switch note checkpoint after each table finishes speaking turns and before host memory synthesis.

#### Scenario: Checkpoint prompt appears
- **WHEN** the backend emits a note checkpoint event for a table and round
- **THEN** the UI shows that the table is paused for note completion
- **AND** the UI identifies the table and round being checkpointed
- **AND** the UI instructs the user to finish design insight / design opportunity notes before clicking “换桌”
- **AND** the UI explains that table host memory synthesis starts only after “换桌”

#### Scenario: Notes are submitted with context
- **WHEN** the user clicks “换桌” from a note checkpoint
- **THEN** the UI submits notebook entries relevant to the checkpoint
- **AND** each submitted note includes its text, table id, round index, source speaker, source speech id when available, and timestamp
- **AND** the submitted request includes a table-switch action

#### Scenario: Switch table with no notes
- **WHEN** the user chooses to switch table without adding notes
- **THEN** the UI submits an empty note list for the checkpoint
- **AND** the run resumes to table host synthesis

#### Scenario: Manual annotation remains available
- **WHEN** the run is not at a system note checkpoint
- **THEN** the existing manual pause/resume annotation flow remains available
- **AND** notebook entries continue to render and jump to highlighted source text
