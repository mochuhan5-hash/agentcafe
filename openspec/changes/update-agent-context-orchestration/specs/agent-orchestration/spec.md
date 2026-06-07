## ADDED Requirements

### Requirement: Source Context As Shared Discussion Evidence
The system SHALL preserve uploaded source context as shared evidence for table discussion rather than replacing it with a facilitator summary.

#### Scenario: Source context enters table discussion
- **WHEN** a user submits a request with an uploaded task/source file
- **THEN** the facilitator uses the source context to configure table questions
- **AND** table hosts and speaking agents can receive source context as evidence for the current table discussion

#### Scenario: Source context is not carried as rotation memory
- **WHEN** a speaking agent rotates to a new table
- **THEN** the agent carries only its `carry_over_packet`
- **AND** it MUST NOT carry the previous table's complete source context, transcript, or table memory as migrant memory

### Requirement: Expert-Skill Facilitator Routing
The system SHALL require the facilitator to route each design task through available expert skills before generating table question configurations.

#### Scenario: Facilitator selects expert views
- **WHEN** a user submits a design task and optional source context
- **THEN** the facilitator identifies relevant expert skills from `lou-yongqi`, `wang-meng`, `liu-long`, and `wang-shouzhi`
- **AND** each generated table configuration includes the selected `expert_skill` or `mixed` plus an `expert_rationale`

#### Scenario: Four-table expert coverage
- **WHEN** the run uses four tables and the task is broad enough for multiple perspectives
- **THEN** the facilitator considers assigning one table question configuration to each of the four expert skills
- **AND** the facilitator performs final deduplication, complementarity checks, and World Cafe quality calibration

#### Scenario: Facilitator calibrates World Cafe quality
- **WHEN** expert skills contribute table question directions
- **THEN** the facilitator verifies that questions are evidence-supported, open-ended, generative, non-leading, and suitable for cross-table pollination
- **AND** the facilitator MUST NOT turn expert outputs into direct design solutions

### Requirement: Table Question Plan And Table Specs
The system SHALL represent facilitator output as a `table_question_plan` and per-table `table_specs`.

#### Scenario: Table question plan is generated
- **WHEN** facilitation completes
- **THEN** the output includes a `context_reading` with user needs, pain points, design tensions, weak signals, and possible reframes
- **AND** the output includes table configurations derived from source context and expert-skill routing

#### Scenario: Table specs include operational fields
- **WHEN** a table is configured
- **THEN** its `table_spec` includes `table_id`, `expert_skill`, `expert_rationale`, `lens`, `guiding_question`, `why_this_matters`, `evidence_basis`, `avoid_solution_bias`, and `round_subquestions`

#### Scenario: Backward-compatible table questions
- **WHEN** existing UI or graph code requires `table_questions`
- **THEN** the system can derive each table question from `table_specs[table_id].guiding_question`

### Requirement: LLM-Generated Table Memory Templates
The system SHALL treat `table_memory` as table-level intrinsic memory maintained by the table host with LLM-generated update templates.

#### Scenario: Host updates evolving table memory
- **WHEN** a table round ends
- **THEN** the table host generates or updates a host memory update instruction and dynamic table memory template
- **AND** the host records table-level patterns, minority views, unresolved tensions, weak signals, pattern deltas, low-value archive candidates, and next-round question seeds according to the dynamic template

#### Scenario: Host memory has fixed shell and dynamic internals
- **WHEN** `table_memory` is stored
- **THEN** it includes fixed shell fields for `table_id`, `round`, `guiding_question`, and source anchors
- **AND** its internal memory dimensions can be generated dynamically by the LLM for the table context

#### Scenario: Host generates round-specific subquestions
- **WHEN** a new round starts after a table has prior memory
- **THEN** the table host generates subquestions from the previous `table_memory`
- **AND** Round 1 emphasizes divergent observation, Round 2 emphasizes connections and tensions, and Round 3 emphasizes problem reframing

### Requirement: Table Host Process Role
The system SHALL define table hosts as neutral memory maintainers, process facilitators, and local pattern recognizers rather than ordinary speakers.

#### Scenario: Host remains neutral
- **WHEN** the host records or opens a round
- **THEN** it preserves repeated themes, minority views, unresolved tensions, and unfinished questions
- **AND** it MUST NOT declare winners, force consensus, or promote a design solution

#### Scenario: Host handles stalled or drifting discussion
- **WHEN** discussion stalls or drifts from the guiding question
- **THEN** the host may provide a non-leading clarification, example, or process cue
- **AND** the cue returns attention to the current table task

### Requirement: Internal Memory And Visible Output Separation
The system SHALL treat prompt and structured-memory strategies as internal memory and process-management mechanisms, not as rigid visible-output templates.

#### Scenario: Speaking output remains conversational
- **WHEN** a speaking agent receives `table_memory` or `carry_over_packet`
- **THEN** the agent uses that memory only as context reference
- **AND** its visible contribution remains natural conversational text rather than JSON, schema fields, or mechanical packet recitation

#### Scenario: Host record hides internal memory schema
- **WHEN** a table host updates `table_memory`
- **THEN** the system stores the structured internal memory for later rounds
- **AND** the user-visible host record is rendered as natural Markdown that does not expose `host_memory_update_instruction`, `llm_generated_table_memory_template`, or other internal schema fields

#### Scenario: Harvest separates analysis from display
- **WHEN** global harvest produces structured analysis
- **THEN** the system can store JSON-like Pattern Channel, Weak Signal Channel, tensions, and opportunity hypotheses internally
- **AND** the displayed harvest is natural readable Markdown rather than raw internal JSON

### Requirement: LLM-Generated Carry-Over Packets
The system SHALL treat `carry_over_packet` as agent-level migrant memory generated through LLM-generated templates rather than fixed hand-written memory fields.

#### Scenario: Speaker carries personal migrant memory
- **WHEN** a speaking agent rotates from one table to another
- **THEN** the system provides a fixed route shell containing `agent_id`, `from_table`, `to_table`, `after_round`, and `current_table_task_anchor`
- **AND** the speaking agent generates personal memory and bridge intent using an LLM-generated memory template

#### Scenario: Packet uses next-table task anchor
- **WHEN** a carry-over packet is generated
- **THEN** `current_table_task_anchor` is based on the destination table's `table_spec`
- **AND** it MUST NOT use a fixed global initial task as the primary speaking anchor

#### Scenario: Packet differs from table memory
- **WHEN** a carry-over packet is stored
- **THEN** it represents the moving agent's personal migrant memory
- **AND** it MUST NOT copy the full `table_memory`, previous transcript, or source context

### Requirement: Rotation Routes Agents And Packets
The system SHALL keep `rotate_agents` as routing infrastructure for speaking agents and generated packets.

#### Scenario: Rotation routes but does not interpret packets
- **WHEN** `rotate_agents` prepares the next round assignment
- **THEN** it routes speakers and their generated packets to the next table
- **AND** it MUST NOT generate, summarize, or reinterpret packet contents

#### Scenario: Hosts remain fixed
- **WHEN** a rotation occurs
- **THEN** table hosts remain assigned to their original tables
- **AND** only non-host speaking agents move between tables

### Requirement: Dual-Channel Global Harvest
The system SHALL separate high-frequency patterns from low-frequency weak signals during global harvest.

#### Scenario: Harvest distinguishes signal types
- **WHEN** all rounds complete
- **THEN** global harvest outputs a Pattern Channel for repeated cross-table themes
- **AND** outputs a Weak Signal Channel for rare but promising minority insights
- **AND** identifies cross-table tensions, opportunity hypotheses, reframed questions, and next learning experiments

#### Scenario: Harvest does not flatten disagreement
- **WHEN** multiple table memories contain contested or minority views
- **THEN** global harvest preserves those tensions as design-relevant material
- **AND** it MUST NOT collapse them into a single consensus summary

### Requirement: Visible Design Opportunity Emphasis
The system SHALL emphasize design-opportunity language in every user-visible agent output.

#### Scenario: Agent output contains design opportunity language
- **WHEN** facilitator, table host, speaking agent, or global harvest visible output contains design opportunity terms, opportunity hypotheses, or equivalent opportunity language
- **THEN** the relevant phrase or sentence is bolded in the displayed Markdown

#### Scenario: Internal memory is not over-emphasized
- **WHEN** internal JSON memory fields contain design opportunity language
- **THEN** the system does not need to bold the stored internal JSON
- **AND** bolding is applied only when that content is transformed into user-visible output
