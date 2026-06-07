## ADDED Requirements

### Requirement: Agent Role Avatar Status Panel
The frontend SHALL show an avatar status panel for each class of agent involved in the World Cafe workflow.

#### Scenario: Default avatar panel is visible
- **WHEN** the app loads
- **THEN** the UI shows avatars for Facilitator, Table Hosts, Speaking Agents, Rotation, and Global Harvest
- **AND** each avatar has a readable label and initial idle status

#### Scenario: Role avatars are operational not decorative
- **WHEN** an avatar is displayed
- **THEN** it represents the current process role state
- **AND** it MUST NOT require external image assets to communicate status

### Requirement: Hover And Focus Status Cards
The frontend SHALL reveal latest agent-role state details when an avatar is hovered or focused.

#### Scenario: Hover reveals latest status
- **WHEN** the user hovers an avatar
- **THEN** the UI shows that role's latest status update, including stage, table or round details when available, and a concise message

#### Scenario: Keyboard focus reveals latest status
- **WHEN** the user focuses an avatar with keyboard navigation
- **THEN** the same latest status information is visible
- **AND** the avatar has an accessible label describing the role and status

### Requirement: Status Updates From Stream Events
The frontend SHALL update agent-role avatar states using existing run stream events.

#### Scenario: Facilitator status updates
- **WHEN** facilitation starts, completes, or a run starts
- **THEN** the Facilitator avatar reflects the current question-setting or run-setup state

#### Scenario: Host status updates
- **WHEN** a table discussion starts or a host record event arrives
- **THEN** the Table Hosts avatar reflects the latest table, round, host, and memory-update state

#### Scenario: Speaking status updates
- **WHEN** a speaking contribution event arrives
- **THEN** the Speaking Agents avatar reflects the latest speaker, table, round, cycle, and turn details

#### Scenario: Rotation and harvest status updates
- **WHEN** rotation or harvest events arrive
- **THEN** the Rotation or Global Harvest avatar reflects the latest process state

### Requirement: Responsive Non-Disruptive Display
The frontend SHALL display role avatars without disrupting existing discussion, notebook, or harvest layouts.

#### Scenario: Desktop toolbar layout
- **WHEN** the viewport has enough horizontal space
- **THEN** the avatar panel appears in the discussion toolbar alongside phase tracking and pause controls
- **AND** it does not obscure the tables grid

#### Scenario: Narrow viewport layout
- **WHEN** the viewport is narrow
- **THEN** the avatar panel wraps or stacks without overlapping toolbar controls, notebook content, or table content

### Requirement: Reset Between Runs
The frontend SHALL reset agent-role avatar states when a new run begins.

#### Scenario: New run clears prior role states
- **WHEN** the user starts a new run
- **THEN** host, speaking, rotation, and harvest avatars return to their idle or waiting states until new stream events arrive
