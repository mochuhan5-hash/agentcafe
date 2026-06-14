## ADDED Requirements

### Requirement: Note-Gated Table Host Memory
The system SHALL pause each table round after speaking-agent contributions and before table host memory synthesis so user-marked notes can enter host intrinsic memory.

#### Scenario: Host memory waits for user notes
- **WHEN** all speaking agents at a table finish their configured turns for a round
- **THEN** the system emits a note checkpoint for that table and round
- **AND** table host synthesis MUST NOT run until the checkpoint is continued

#### Scenario: User notes have highest synthesis priority
- **WHEN** table host synthesis begins after a note checkpoint
- **THEN** the host receives relevant user-marked notes for that table and round
- **AND** the host treats those notes as the highest-priority design insight / design opportunity evidence
- **AND** host historical memory is treated as the next priority
- **AND** current conversation is treated as supporting context

#### Scenario: Empty notes are allowed
- **WHEN** the checkpoint is continued without notes
- **THEN** host synthesis proceeds using host historical memory and current conversation
- **AND** the absence of notes is represented explicitly rather than blocking the run

#### Scenario: Closing follows note-informed memory
- **WHEN** note-informed host memory synthesis completes
- **THEN** the user-visible host closing remark is generated from the updated memory
- **AND** it MUST NOT mechanically copy every note or expose internal memory schema

### Requirement: Non-Interactive Note Fallback
The system SHALL keep non-web and dry-run flows non-blocking when no user note checkpoint handler is configured.

#### Scenario: Dry run proceeds without manual notes
- **WHEN** the graph runs in dry-run or CLI mode without a checkpoint handler
- **THEN** each note checkpoint resolves with an empty note list
- **AND** the graph completes normally
