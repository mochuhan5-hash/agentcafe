const chatLog = document.querySelector("#chatLog");
const requestForm = document.querySelector("#requestForm");
const requestInput = document.querySelector("#userRequest");
const facilitateBtn = document.querySelector("#facilitateBtn");
const startBtn = document.querySelector("#startBtn");
const questionEditor = document.querySelector("#questionEditor");
const tablesGrid = document.querySelector("#tablesGrid");
const phaseTrack = document.querySelector("#phaseTrack");
const runStatus = document.querySelector("#runStatus");
const modelBadge = document.querySelector("#modelBadge");
const roundBadge = document.querySelector("#roundBadge");
const harvestContent = document.querySelector("#harvestContent");
const traceCount = document.querySelector("#traceCount");
const tableCountInput = document.querySelector("#tableCount");
const speakersInput = document.querySelector("#speakersPerTable");
const speechesInput = document.querySelector("#speechesPerAgent");
const pauseBtn = document.querySelector("#pauseBtn");
const addNoteBtn = document.querySelector("#addNoteBtn");
const downloadActivityLogBtn = document.querySelector("#downloadActivityLogBtn");
const notebookList = document.querySelector("#notebookList");
const notebookCount = document.querySelector("#notebookCount");
const noteCheckpointPanel = document.querySelector("#noteCheckpointPanel");
const noteCheckpointTitle = document.querySelector("#noteCheckpointTitle");
const noteCheckpointDetail = document.querySelector("#noteCheckpointDetail");
const continueNotesBtn = document.querySelector("#continueNotesBtn");
const discussionPane = document.querySelector(".discussion-pane");
const discussionToolbar = document.querySelector(".discussion-toolbar");
const discussionLayout = document.querySelector(".discussion-layout");
const backgroundFileInput = document.querySelector("#backgroundFile");
const backgroundSummary = document.querySelector("#backgroundSummary");
const chooseBackgroundBtn = document.querySelector("#chooseBackgroundBtn");
const clearBackgroundBtn = document.querySelector("#clearBackgroundBtn");
const agentStatusDock = document.querySelector("#agentStatusDock");
const newOrderBtn = document.querySelector("#newOrderBtn");
const appShell = document.querySelector(".app-shell");

let facilitatedTables = [];
let lastExpertMeta = {};
let activeRun = null;
let eventSource = null;
let traceTotal = 0;
let currentRound = 0;
let maxRounds = 0;
let speechesPerAgent = 3;
let isPaused = false;
let seenEventKeys = new Set();
let notebookEntries = [];
let noteSequence = 0;
let userActivityLog = [];
let pendingNoteSelection = null;
let pendingNoteCheckpoints = [];
let activeNoteCheckpoint = null;
let availableAgents = [];
let hostAssignments = {};
let speakerAssignments = {};
let backgroundContext = "";
let backgroundFilename = "";
let currentTableAgents = {};
let agentMemorySnapshots = {};

const phaseOrder = ["facilitate", "setup", "round_started", "rotation", "harvest", "done"];
const agentRoleStatuses = {
  facilitator: {
    label: "Facilitator",
    initials: "F",
    tone: "green",
    status: "Ready",
    detail: "Waiting to frame discussion questions for each table.",
    meta: "Idle",
    time: "",
  },
  host: {
    label: "Table Host",
    initials: "H",
    tone: "amber",
    status: "Idle",
    detail: "Waiting to record and maintain table memory.",
    meta: "No active table",
    time: "",
  },
  speaker: {
    label: "Speakers",
    initials: "S",
    tone: "blue",
    status: "Idle",
    detail: "Waiting to join table discussions.",
    meta: "No active speaker",
    time: "",
  },
  rotation: {
    label: "Rotation",
    initials: "R",
    tone: "rose",
    status: "Idle",
    detail: "Waiting for participants to rotate between tables.",
    meta: "No route yet",
    time: "",
  },
  harvest: {
    label: "Harvest",
    initials: "G",
    tone: "green",
    status: "Idle",
    detail: "Waiting to synthesize cross-table patterns and design opportunities.",
    meta: "Not started",
    time: "",
  },
};

init();

tableCountInput.addEventListener("change", async () => {
  await loadAgentsForSettings();
  facilitatedTables = [];
  hideQuestionEditorView();
  questionEditor.innerHTML = "";
  startBtn.disabled = true;
});

speakersInput.addEventListener("change", async () => {
  await loadAgentsForSettings();
  if (facilitatedTables.length) {
    renderQuestionEditor(facilitatedTables, lastExpertMeta);
  }
});

backgroundFileInput.addEventListener("change", async () => {
  const file = backgroundFileInput.files?.[0];
  if (!file) {
    clearBackground();
    return;
  }
  const lowerName = file.name.toLowerCase();
  if (!lowerName.endsWith(".md") && !lowerName.endsWith(".markdown") && !lowerName.endsWith(".txt")) {
    addMessage("error", "请上传 .md 或 .markdown 背景材料。");
    clearBackground();
    return;
  }
  backgroundContext = await file.text();
  backgroundFilename = file.name;
  backgroundSummary.textContent = `${backgroundFilename} · ${backgroundContext.length} characters`;
  clearBackgroundBtn.hidden = false;
});

chooseBackgroundBtn?.addEventListener("click", () => backgroundFileInput.click());
clearBackgroundBtn.addEventListener("click", clearBackground);
pauseBtn.addEventListener("click", togglePause);
addNoteBtn.addEventListener("mousedown", (event) => event.preventDefault());
addNoteBtn.addEventListener("click", addSelectedNote);
continueNotesBtn?.addEventListener("click", submitActiveNoteCheckpoint);
downloadActivityLogBtn?.addEventListener("click", downloadActivityLog);
document.querySelectorAll("[data-final-insight]").forEach((textarea) => {
  textarea.addEventListener("change", () => {
    recordUserAction("final_insights_updated", {
      field: textarea.dataset.finalInsight,
      content: textarea.value.trim(),
      final_insights: getFinalInsightContents(),
    });
  });
});

// Delegate clicks on agent elements to show details modal
document.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  recordUserAction("button_clicked", {
    id: button.id || "",
    label: getButtonLabel(button),
    tab: button.dataset.tab || "",
  });
});

document.addEventListener("click", (event) => {
  const avatarBtn = event.target.closest("[data-avatar-agent-id]");
  const metaStrong = event.target.closest("[data-meta-agent-id]");
  const seatNode = event.target.closest("[data-seat-agent-id]");
  
  if (avatarBtn) {
    const agentId = avatarBtn.dataset.avatarAgentId;
    openAgentProfile(agentId);
  } else if (metaStrong) {
    const agentId = metaStrong.dataset.metaAgentId;
    openAgentProfile(agentId);
  } else if (seatNode) {
    const agentId = seatNode.dataset.seatAgentId;
    openAgentProfile(agentId);
  }
});

const modalCloseBtn = document.querySelector("#modalCloseBtn");
const modalOverlay = document.querySelector("#agentProfileModal .modal-overlay");
modalCloseBtn?.addEventListener("click", closeAgentProfile);
modalOverlay?.addEventListener("click", closeAgentProfile);

newOrderBtn?.addEventListener("click", () => {
  resetRunView();
  appShell.classList.replace("mode-salon", "mode-config");
  newOrderBtn.hidden = true;
  startBtn.disabled = true;
  facilitateBtn.disabled = false;
  requestInput.value = "";
  clearBackground();
  hideQuestionEditorView();
  questionEditor.innerHTML = "";
  chatLog.innerHTML = "";
  addMessage("facilitator", "World Cafe is ready.");
});

function openAgentProfile(agentId) {
  const profile = activeRun?.agent_profiles?.[agentId] || availableAgents.find(a => a.id === agentId);
  if (!profile) return;
  const modal = document.querySelector("#agentProfileModal");
  const avatar = document.querySelector("#modalAgentAvatar");
  const name = document.querySelector("#modalAgentName");
  const role = document.querySelector("#modalAgentRole");
  const skills = document.querySelector("#modalAgentSkills");
  const style = document.querySelector("#modalAgentStyle");

  if (avatar) avatar.textContent = agentInitials(profile.name || agentId);
  if (name) name.textContent = profile.name || agentId;
  if (role) role.textContent = profile.role || "Discussion participant";
  if (skills) {
    skills.innerHTML = (profile.skills || []).map(skill => `<span>${escapeHtml(skill)}</span>`).join("");
  }
  if (style) style.textContent = profile.style || "No style description yet.";

  // Dynamic memory lookup and rendering inside modal
  const memorySection = document.querySelector("#modalAgentMemorySection");
  if (memorySection) {
    const snapshot = agentMemorySnapshots[agentId];
    if (snapshot) {
      const rows = formatMemorySnapshot(snapshot);
      const body = rows.length
        ? rows.map((row) => `<p>${renderInlineMarkdown(escapeHtml(row))}</p>`).join("")
        : "<p>No internal memory yet.</p>";
      memorySection.innerHTML = `
        <h4>Current Internal Memory</h4>
        <div class="modal-memory-body">${body}</div>
      `;
      memorySection.hidden = false;
    } else {
      memorySection.hidden = true;
    }
  }

  if (modal) modal.hidden = false;
}

function closeAgentProfile() {
  const modal = document.querySelector("#agentProfileModal");
  if (modal) modal.hidden = true;
}

document.addEventListener("selectionchange", () => {
  pendingNoteSelection = getSelectedDiscussionSelection();
  addNoteBtn.disabled = !isNoteTakingActive() || !pendingNoteSelection;
});

async function init() {
  try {
    const config = await getJson("/api/config");
    const tokenLabel = config.token_count ? ` · ${config.token_count} tokens` : "";
    modelBadge.textContent = `${config.model} · ${config.base_url}${tokenLabel}`;
    tableCountInput.value = config.default_table_count || 3;
    speakersInput.value = config.default_speakers_per_table || 2;
    speechesInput.value = config.default_speeches_per_agent || 3;
    speechesPerAgent = getSpeechesPerAgent();
    if (!config.token_configured) {
      modelBadge.textContent += " · Token not configured";
    }
  } catch {
    modelBadge.textContent = "Config unavailable";
  }

  addMessage("facilitator", "World Cafe is ready.");
  renderAgentStatusDock();
  await loadAgentsForSettings();
}

requestForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const request = requestInput.value.trim();
  if (!request) return;

  addMessage("user", request);
  updateAgentStatus("facilitator", {
    status: "Reading Context",
    detail: "Generating guiding questions for each table.",
    meta: `${getTableCount()} tables requested`,
  });
  setBusy(true);
  setPhase("facilitate");

  try {
    const result = await postJson("/api/facilitate", {
      request,
      table_count: getTableCount(),
      background_context: backgroundContext,
      background_filename: backgroundFilename,
    });
    facilitatedTables = result.tables;
    console.log("[facilitate] full result:", JSON.stringify(result, null, 2));
    const expertSkill = result.tables?.[0]?.expert_skill || "";
    const expertRationale = result.expert_skill_routes?.rationale || result.tables?.[0]?.expert_rationale || "";
    lastExpertMeta = { expertSkill, expertRationale };
    updateAgentStatus("facilitator", {
      status: "Questions Ready",
      detail: "A guiding discussion question has been generated for each table.",
      meta: `${facilitatedTables.length} table questions`,
    });
    addMessage("facilitator", formatQuestions(facilitatedTables));
    await loadAgentsForSettings();
    renderQuestionEditor(facilitatedTables, { expertSkill, expertRationale });
    startBtn.disabled = false;
  } catch (error) {
    updateAgentStatus("facilitator", {
      status: "Error",
      detail: error.message,
      meta: "Facilitation failed",
    });
    setStatus("Facilitation Error", "error");
    addMessage("error", error.message);
  } finally {
    setBusy(false);
  }
});

startBtn.addEventListener("click", async () => {
  const tables = readEditedQuestions();
  if (tables.length !== getTableCount()) return;

  resetRunView();
  updateAgentStatus("facilitator", {
    status: "Setup Ready",
    detail: "Table discussion plans are ready and the workflow is starting.",
    meta: `${tables.length} tables · ${getRoundCount()} rounds`,
  });
  setStatus("Starting", "running");
  startBtn.disabled = true;
  facilitateBtn.disabled = true;

  try {
    activeRun = await postJson("/api/runs", {
      tables,
      rounds: getRoundCount(),
      speakers_per_table: getSpeakersPerTable(),
      speeches_per_agent: getSpeechesPerAgent(),
      host_assignments: hostAssignments,
      speaker_assignments: readSpeakerAssignments(),
      background_context: backgroundContext,
      background_filename: backgroundFilename,
    });
    maxRounds = activeRun.rounds;
    speechesPerAgent = activeRun.speeches_per_agent || getSpeechesPerAgent();
    roundBadge.textContent = `0 / ${maxRounds}`;
    pauseBtn.disabled = false;
    renderTables(activeRun);
    subscribeToRun(activeRun.run_id);
    appShell.classList.replace("mode-config", "mode-salon");
    newOrderBtn.hidden = true;
  } catch (error) {
    setStatus("Error", "error");
    addMessage("error", error.message);
    startBtn.disabled = false;
    facilitateBtn.disabled = false;
  }
});

function subscribeToRun(runId) {
  if (eventSource) eventSource.close();
  if (isPaused) return;
  eventSource = new EventSource(`/api/runs/${runId}/events`);

  eventSource.onmessage = (message) => {
    const event = JSON.parse(message.data);
    handleRunEvent(event);
  };

  eventSource.onerror = () => {
    if (eventSource) eventSource.close();
    if (runStatus.textContent !== "Done") {
      setStatus("Stream closed", "error");
    }
  };
}

function handleRunEvent(event) {
  if (event.type === "stream_closed") {
    eventSource?.close();
    return;
  }
  if (event.type === "run_started") {
    setStatus("Running", "running");
    updateAgentStatus("facilitator", {
      status: "Workflow Started",
      detail: "The World Cafe workflow engine is running.",
      meta: activeRun ? `${activeRun.table_count} tables started` : "Discussion running",
    });
    return;
  }
  if (event.type === "pause_changed") {
    if (event.status === "pause_requested") {
      setStatus("Pausing After Current Speaker", "running");
    } else if (event.status === "paused") {
      setStatus("Waiting For Notes", "running");
    } else if (event.status === "running") {
      setStatus("Running", "running");
    }
    return;
  }
  if (event.type === "note_checkpoint") {
    handleNoteCheckpointEvent(event);
    return;
  }
  if (event.type === "error") {
    setStatus("Error", "error");
    updateAgentStatus("facilitator", {
      status: "Error",
      detail: event.message || "The discussion workflow reported an error.",
      meta: "Needs attention",
    });
    addMessage("error", event.message || "The run failed, but the backend did not return a detailed error.");
    newOrderBtn.hidden = false;
    return;
  }
  if (event.type === "run_complete") {
    setStatus("Done", "");
    setPhase("done");
    updateAgentStatus("harvest", {
      status: "Done",
      detail: "The global harvest is complete and the final discussion insights are ready.",
      meta: `${traceTotal} events processed`,
    });
    renderHarvest(event.harvest?.content || "");
    addMessage("facilitator", "The global harvest is complete.");
    facilitateBtn.disabled = false;
    pauseBtn.disabled = true;
    pauseBtn.textContent = "Pause to Annotate";
    isPaused = false;
    activeNoteCheckpoint = null;
    pendingNoteCheckpoints = [];
    hideNoteCheckpointPanel();
    discussionPane.classList.remove("paused");
    newOrderBtn.hidden = false;
    return;
  }
  if (event.type !== "trace") return;

  const metadata = event.metadata || {};
  const eventKey = getTraceEventKey(event, metadata);
  if (seenEventKeys.has(eventKey)) return;
  seenEventKeys.add(eventKey);
  traceTotal += 1;
  traceCount.textContent = `${traceTotal} events`;
  setPhase(event.stage);

  if (event.stage === "round_started") {
    currentRound = (metadata.round_index || 0) + 1;
    roundBadge.textContent = `${currentRound} / ${maxRounds}`;
    setStatus(`Round ${currentRound}`, "running");
    updateAgentStatus("speaker", {
      status: `Round ${currentRound} Ready`,
      detail: "Speakers have been assigned to this round's tables.",
      meta: summarizeAssignments(metadata.assignments || {}),
    });
    updateAgentStatus("host", {
      status: `Round ${currentRound} Listening`,
      detail: "Table hosts are ready to record local discussion memory.",
      meta: `${Object.keys(metadata.assignments || {}).length} active tables`,
    });
    Object.entries(metadata.assignments || {}).forEach(([tableId, agentIds]) => {
      ensureRound(tableId, metadata.round_index || 0, agentIds);
    });
  }

  if (event.stage === "table_discussion") {
    ensureRound(metadata.table_id, metadata.round_index || 0, metadata.agent_ids || []);
    updateAgentStatus("speaker", {
      status: "Discussing",
      detail: `${metadata.table_id || "discussion table"} is active.`,
      meta: formatRoundStatusMeta(metadata),
    });
    updateAgentStatus("host", {
      status: "Observing Table",
      detail: `Host ${metadata.host_id || "host"} is maintaining memory for ${metadata.table_id || "this table"}.`,
      meta: formatRoundStatusMeta(metadata),
    });
  }

  if (event.stage === "host_opening") {
    updateAgentStatus("host", {
      status: "Opening Round",
      detail: `Host ${metadata.host_name || metadata.host_id || "host"} opened ${metadata.table_id || "the table"} with guiding prompts.`,
      meta: formatRoundStatusMeta(metadata),
    });
    appendHostOpening(metadata);
  }

  if (event.stage === "agent_contribution") {
    updateAgentStatus("speaker", {
      status: "Speaker Contributing",
      detail: `Speaker ${metadata.agent_name || metadata.agent_id || "participant"} contributed at ${metadata.table_id || "the table"}.`,
      meta: formatTurnStatusMeta(metadata),
    });
    appendContribution(metadata);
  }

  if (event.stage === "host_record") {
    updateAgentStatus("host", {
      status: "Recording Table Memory",
      detail: `Host ${metadata.host_name || metadata.host_id || "host"} updated and saved memory for ${metadata.table_id || "the table"}.`,
      meta: formatRoundStatusMeta(metadata),
    });
    appendHostRecord(metadata);
  }

  if (event.stage === "rotation") {
    setStatus(`Rotating To Round ${(metadata.next_round_index || 0) + 1}`, "running");
    updateAgentStatus("rotation", {
      status: "Rotating Speakers",
      detail: "Non-host speakers are rotating to the next table.",
      meta: formatRotationMeta(metadata),
    });
    appendRotationRecord(metadata);
  }

  if (event.stage === "harvest") {
    setStatus("Harvesting", "running");
    updateAgentStatus("harvest", {
      status: "Synthesizing Harvest",
      detail: "The harvest is clustering shared patterns, weak signals, tensions, and design opportunities.",
      meta: `${metadata.round_count || maxRounds || "?"} discussion rounds`,
    });
  }
}

function renderAgentStatusDock() {
  if (!agentStatusDock) return;
  agentStatusDock.innerHTML = Object.entries(agentRoleStatuses)
    .map(([key, item]) => renderAgentStatusAvatar(key, item))
    .join("");
}

function renderAgentStatusAvatar(key, item) {
  const time = item.time ? `<span>${escapeHtml(item.time)}</span>` : "";
  return `
    <button
      type="button"
      class="agent-status-avatar ${escapeHtml(item.tone || "")}"
      data-agent-role="${escapeHtml(key)}"
      aria-label="${escapeHtml(item.label)} status: ${escapeHtml(item.status)}"
    >
      <span class="avatar-mark">${escapeHtml(item.initials)}</span>
      <span class="avatar-label">${escapeHtml(item.label)}</span>
      <span class="agent-status-card" role="tooltip">
        <strong>${escapeHtml(item.label)}</strong>
        <em>${escapeHtml(item.status)}</em>
        <span>${escapeHtml(item.meta || "")}</span>
        <p>${escapeHtml(item.detail || "")}</p>
        ${time}
      </span>
    </button>
  `;
}

function updateAgentStatus(key, updates) {
  if (!agentRoleStatuses[key]) return;
  agentRoleStatuses[key] = {
    ...agentRoleStatuses[key],
    ...updates,
    time: formatActivityTime(),
  };
  renderAgentStatusDock();
}

function summarizeAssignments(assignments) {
  const tableCount = Object.keys(assignments).length;
  const speakerCount = Object.values(assignments).reduce(
    (count, agents) => count + Math.max((agents || []).length - 1, 0),
    0,
  );
  return `${tableCount} tables · ${speakerCount} speakers`;
}

function formatRoundStatusMeta(metadata) {
  const round = Number.isFinite(Number(metadata.round_index))
    ? `Round ${Number(metadata.round_index) + 1}`
    : "Round ?";
  const parts = [`${metadata.table_id || "table ?"} · ${round}`];
  if (Object.prototype.hasOwnProperty.call(metadata, "background_context_chars")) {
    parts.push(`${Number(metadata.background_context_chars) || 0} background chars`);
  }
  return parts.join(" · ");
}

function formatRotationMeta(metadata) {
  const tableCount = Object.keys(metadata.assignments || {}).length;
  const nextRound = Number.isFinite(Number(metadata.next_round_index))
    ? Number(metadata.next_round_index) + 1
    : "?";
  return `${tableCount || "?"} tables · Round ${nextRound}`;
}

function formatTurnStatusMeta(metadata) {
  const roundMeta = formatRoundStatusMeta(metadata);
  const turn = Number.isFinite(Number(metadata.turn_index))
    ? `Turn ${Number(metadata.turn_index) + 1}`
    : "Turn ?";
  const cycle = Number.isFinite(Number(metadata.cycle_index))
    ? `Cycle ${Number(metadata.cycle_index) + 1}`
    : "Cycle ?";
  return `${roundMeta} · ${cycle} · ${turn}`;
}

function getTraceEventKey(event, metadata) {
  return [
    event.stage,
    event.message,
    metadata.table_id || "",
    metadata.round_index ?? "",
    metadata.agent_id || metadata.host_id || "",
    metadata.turn_index ?? "",
    metadata.cycle_index ?? "",
    event.timestamp || "",
  ].join("|");
}

function showQuestionEditorView() {
  questionEditor.hidden = false;
  discussionPane.classList.add("show-editor");
}

function hideQuestionEditorView() {
  questionEditor.hidden = true;
  discussionPane.classList.remove("show-editor");
}

function renderQuestionEditor(tables, { expertSkill, expertRationale } = {}) {
  showQuestionEditorView();
  questionEditor.innerHTML = "";
  console.log("[renderQuestionEditor] expertSkill:", expertSkill, "expertRationale:", expertRationale);
  if (expertSkill && expertSkill !== "mixed") {
    const skillNames = { louyongqi: "娄永琪", wangmeng: "王萌", wangshouzhi: "王受之", liulong: "刘胧" };
    const displayName = skillNames[expertSkill] || expertSkill;
    const banner = document.createElement("div");
    banner.className = "skill-banner";
    banner.innerHTML = `<span class="skill-label">Expert Skill:</span> <strong>${escapeHtml(displayName)}</strong>${expertRationale && !expertRationale.includes("未提供") ? ` <span class="skill-rationale">— ${escapeHtml(expertRationale)}</span>` : ""}`;
    questionEditor.append(banner);
  }
  buildDefaultAssignments(tables);
  tables.forEach((table) => {
    questionEditor.append(renderLeftField(table));
    questionEditor.append(renderRightField(table.table_id));
    refreshAgentPromptBoxes(table.table_id);
  });
}

function readEditedQuestions() {
  return [...questionEditor.querySelectorAll("textarea[data-table-id]")].map((textarea) => {
    const tableId = textarea.dataset.tableId;
    const matchingTable = facilitatedTables.find((table) => table.table_id === tableId) || {};
    // Gather per-agent prompts from the assignment field and combine
    const agentPromptParts = [];
    questionEditor.querySelectorAll(`textarea[data-agent-prompt-for][data-agent-prompt-table="${tableId}"]`).forEach((ta) => {
      const val = ta.value.trim();
      if (val) {
        const agentName = ta.dataset.agentPromptFor || ta.dataset.agentPromptId;
        agentPromptParts.push(`[${agentName}] ${val}`);
      }
    });
    return {
      ...matchingTable,
      table_id: tableId,
      parent_question: matchingTable.parent_question || requestInput.value.trim(),
      question: textarea.value.trim(),
      guiding_question: textarea.value.trim(),
      agent_system_prompt: agentPromptParts.join("\n"),
    };
  });
}

function renderLeftFieldLegacy(table) {
  const tableId = table.table_id;
  const field = document.createElement("div");
  field.className = "question-field";
  
  const hostId = hostAssignments[tableId];
  const host = availableAgents.find((agent) => agent.id === hostId);
  const speakers = new Set(speakerAssignments[tableId] || []);
  const options = availableAgents
    .filter((agent) => agent.id !== hostId)
    .map((agent) => {
      const selected = speakers.has(agent.id) ? "selected" : "";
      return `<option value="${escapeHtml(agent.id)}" ${selected}>${escapeHtml(agent.name)} · ${escapeHtml(agent.role || agent.id)}</option>`;
    })
    .join("");

  field.innerHTML = `
    <div class="question-header">
      <label for="${tableId}">${tableId.replace("_", " ").toUpperCase()}</label>
      <div class="host-badge-editor">
        <span class="host-label">Host:</span>
        <span class="host-name">${escapeHtml(host?.name || hostId || "")}</span>
      </div>
    </div>
    <textarea id="${tableId}" data-table-id="${tableId}" placeholder="Enter a discussion topic or guiding question...">${escapeHtml(table.question)}</textarea>
    
    <div class="speaker-select-section">
      <div class="assignment-meta">
        <span>Select speaking agents</span>
        <span data-selected-count="${tableId}">${speakers.size} selected</span>
      </div>
      <select class="agent-select" multiple size="4" data-agent-select="${tableId}">
        ${options}
      </select>
    </div>
  `;

  const select = field.querySelector("select");
  select.addEventListener("change", () => {
    speakerAssignments[tableId] = [...select.selectedOptions].map((option) => option.value);
    field.querySelector(`[data-selected-count="${tableId}"]`).textContent =
      `${speakerAssignments[tableId].length} selected`;
    refreshAgentPromptBoxes(tableId);
  });

  return field;
}

function renderRightField(tableId) {
  const wrapper = document.createElement("div");
  wrapper.className = "prompt-field";
  wrapper.dataset.assignmentTableId = tableId;
  wrapper.innerHTML = `
    <div class="prompt-header">
      <span>Agent Prompt Configuration</span>
    </div>
    <div class="agent-prompt-list" data-prompt-list-table="${tableId}"></div>
  `;
  return wrapper;
}

function refreshAgentPromptBoxes(tableId) {
  const container = questionEditor.querySelector(`[data-prompt-list-table="${tableId}"]`);
  if (!container) return;
  const selectedIds = new Set(speakerAssignments[tableId] || []);
  
  // Preserve existing prompt values
  const existingValues = {};
  container.querySelectorAll("textarea[data-agent-prompt-id]").forEach((ta) => {
    existingValues[ta.dataset.agentPromptId] = ta.value;
  });
  
  container.innerHTML = "";
  
  if (selectedIds.size === 0) {
    container.innerHTML = `
      <div class="empty-prompt-placeholder">
        <span class="placeholder-icon">✨</span>
        <span class="placeholder-text">Select speaking agents on the left to configure their prompts</span>
      </div>
    `;
    return;
  }
  
  selectedIds.forEach((agentId) => {
    const agent = availableAgents.find((a) => a.id === agentId);
    const agentName = agent?.name || agentId;
    const box = document.createElement("div");
    box.className = "agent-prompt-box";
    box.innerHTML = `
      <label>${escapeHtml(agentName)} · Prompt</label>
      <textarea
        data-agent-prompt-id="${escapeHtml(agentId)}"
        data-agent-prompt-for="${escapeHtml(agentName)}"
        data-agent-prompt-table="${escapeHtml(tableId)}"
        rows="2"
        placeholder="Add an extra system prompt for ${escapeHtml(agentName)} (optional)"
      >${escapeHtml(existingValues[agentId] || "")}</textarea>
    `;
    container.append(box);
  });
}

function readSpeakerAssignmentsLegacy() {
  questionEditor.querySelectorAll("[data-agent-select]").forEach((select) => {
    speakerAssignments[select.dataset.agentSelect] = [...select.selectedOptions].map(
      (option) => option.value,
    );
  });
  return speakerAssignments;
}

function renderLeftField(table) {
  const tableId = table.table_id;
  const field = document.createElement("div");
  field.className = "question-field";

  const hostId = hostAssignments[tableId];
  const host = availableAgents.find((agent) => agent.id === hostId);
  const speakers = new Set(speakerAssignments[tableId] || []);
  const agentChoices = availableAgents
    .filter((agent) => agent.id !== hostId)
    .map((agent) => {
      const selected = speakers.has(agent.id);
      return `
        <button
          type="button"
          class="agent-choice ${selected ? "selected" : ""}"
          data-agent-choice="${escapeHtml(agent.id)}"
          aria-pressed="${selected ? "true" : "false"}"
        >
          <span>${escapeHtml(agent.name)}</span>
          <small>${escapeHtml(agent.role || agent.id)}</small>
        </button>
      `;
    })
    .join("");

  field.innerHTML = `
    <div class="question-header">
      <label for="${tableId}">${tableId.replace("_", " ").toUpperCase()}</label>
      <div class="host-badge-editor">
        <span class="host-label">Host:</span>
        <span class="host-name">${escapeHtml(host?.name || hostId || "")}</span>
      </div>
    </div>
    <textarea id="${tableId}" data-table-id="${tableId}" placeholder="Discussion question...">${escapeHtml(table.question)}</textarea>

    <div class="speaker-select-section">
      <div class="assignment-meta">
        <span>Select speaking agents</span>
        <span data-selected-count="${tableId}">${speakers.size} selected</span>
      </div>
      <div class="agent-select agent-choice-list" data-agent-select="${tableId}">
        ${agentChoices}
      </div>
    </div>
  `;

  const choiceList = field.querySelector("[data-agent-select]");
  choiceList.addEventListener("click", (event) => {
    const choice = event.target.closest("[data-agent-choice]");
    if (!choice) return;
    const agentId = choice.dataset.agentChoice;
    const selectedIds = new Set(speakerAssignments[tableId] || []);
    if (selectedIds.has(agentId)) {
      selectedIds.delete(agentId);
    } else {
      selectedIds.add(agentId);
    }
    speakerAssignments[tableId] = [...selectedIds];
    choiceList.querySelectorAll("[data-agent-choice]").forEach((item) => {
      const selected = selectedIds.has(item.dataset.agentChoice);
      item.classList.toggle("selected", selected);
      item.setAttribute("aria-pressed", selected ? "true" : "false");
    });
    field.querySelector(`[data-selected-count="${tableId}"]`).textContent =
      `${speakerAssignments[tableId].length} selected`;
    refreshAgentPromptBoxes(tableId);
  });

  return field;
}

function readSpeakerAssignments() {
  return speakerAssignments;
}

function renderTables(run) {
  const profiles = run.agent_profiles || {};
  tablesGrid.innerHTML = "";
  Object.entries(run.table_questions).forEach(([tableId, question]) => {
    const hostId = run.hosts[tableId];
    const hostName = profiles[hostId]?.name || hostId;
    const tableSpec = run.table_specs?.[tableId] || {};
    const table = document.createElement("section");
    table.className = "table-card";
    table.dataset.tableId = tableId;
    table.dataset.tableQuestion = question;
    table.innerHTML = `
      <header>
        <div class="table-title">
          <h3>${tableId.replace("_", " ").toUpperCase()}</h3>
          <span class="host-tag">Host ${escapeHtml(hostName)}</span>
        </div>
        <div class="table-question">
          <span>${escapeHtml(question)}</span>
        </div>
      </header>
      <div class="seating-chart-container" data-seating-container="${tableId}"></div>
      <div class="round-list" data-round-list></div>
    `;
    tablesGrid.append(table);
    
    const initialAgents = [hostId, ...(run.assignments[tableId] || [])];
    currentTableAgents[tableId] = initialAgents;
    drawSeatingChart(table, tableId, initialAgents);
  });
}

function drawSeatingChart(tableElement, tableId, agentIds, activeSpeakerId = null) {
  const container = (tableElement || document).querySelector(`[data-seating-container="${tableId}"]`);
  if (!container) return;
  container.innerHTML = "";
  
  // Center Table node
  const centerTable = document.createElement("div");
  centerTable.className = "seating-chart-table";
  centerTable.textContent = tableId.replace("table_", "T");
  container.append(centerTable);
  
  if (!agentIds || agentIds.length === 0) return;
  
  const M = agentIds.length;
  agentIds.forEach((agentId, i) => {
    const name = getAgentName(agentId);
    const initials = agentInitials(name);
    const seat = document.createElement("div");
    seat.className = "seating-chart-seat";
    seat.dataset.seatAgentId = agentId;
    
    const isHost = i === 0;
    if (isHost) {
      seat.classList.add("host");
    } else {
      seat.classList.add("speaker");
    }
    
    if (agentId === activeSpeakerId) {
      seat.classList.add("active-speaker");
      const steam = document.createElement("div");
      steam.className = "steam-vapor";
      steam.innerHTML = "<span></span><span></span><span></span>";
      seat.append(steam);
    }
    
    const seatContent = document.createElement("span");
    seatContent.className = "seat-initials";
    seatContent.textContent = initials;
    seat.append(seatContent);

    // Memory popover
    const popover = document.createElement("div");
    popover.className = "seat-memory-popover";
    const snapshot = agentMemorySnapshots[agentId];
    const roleTag = isHost ? "Host" : "Speaker";
    popover.innerHTML = renderSeatMemoryCard(name, roleTag, snapshot);
    seat.append(popover);

    seat.addEventListener("click", (e) => {
      // Close all other popovers in this container first
      container.querySelectorAll(".seat-memory-popover.visible").forEach((p) => {
        if (p !== popover) p.classList.remove("visible");
      });
      popover.classList.toggle("visible");
    });
    
    // Distribute seats radially around table (radius 42px)
    const angle = (i * 2 * Math.PI) / M - Math.PI / 2;
    const radius = 42;
    const dx = radius * Math.cos(angle);
    const dy = radius * Math.sin(angle);
    
    seat.style.left = `calc(50% + ${dx}px)`;
    seat.style.top = `calc(50% + ${dy}px)`;
    seat.style.transform = "translate(-50%, -50%)";
    
    container.append(seat);
  });
}

function ensureRound(tableId, roundIndex, agentIds = []) {
  if (!tableId) return null;
  const table = tablesGrid.querySelector(`[data-table-id="${tableId}"]`);
  if (!table) return null;
  
  if (agentIds && agentIds.length > 0) {
    currentTableAgents[tableId] = agentIds;
    drawSeatingChart(table, tableId, agentIds);
  }

  const list = table.querySelector("[data-round-list]");
  let round = list.querySelector(`[data-round-index="${roundIndex}"]`);
  if (round) return round;

  round = document.createElement("div");
  round.className = "round-block";
  round.dataset.roundIndex = roundIndex;
  round.innerHTML = `
    <div data-host-opening></div>
    <div data-contributions></div>
    <div data-host-record></div>
  `;
  list.append(round);
  return round;
}

function appendHostOpening(metadata) {
  const shouldScroll = shouldFollowTableScrollByTable(metadata.table_id);
  const round = ensureRound(metadata.table_id, metadata.round_index, metadata.agent_ids || []);
  if (!round) return;
  if (metadata.memory_snapshot) agentMemorySnapshots[metadata.host_id] = metadata.memory_snapshot;
  const slot = round.querySelector("[data-host-opening]");
  if (!slot) return;
  slot.innerHTML = renderAgentMessage({
    className: "host-opening",
    agentId: metadata.host_id,
    agentName: tableHostLabel(metadata.table_id),
    roleLabel: "Host Opening",
    metaLabel: formatRoundStatusMeta(metadata),
    content: metadata.content || "",
    memorySnapshot: metadata.memory_snapshot,
    tone: "host",
  });
  decorateHostNoteTarget(slot.querySelector(".host-opening"), metadata, "host_opening");
  scrollTableToBottom(round, shouldScroll);
  
  // Highlight host seat on map
  const agents = currentTableAgents[metadata.table_id] || (metadata.agent_ids || [metadata.host_id]);
  drawSeatingChart(null, metadata.table_id, agents, metadata.host_id);
}

function appendContribution(metadata) {
  const shouldScroll = shouldFollowTableScrollByTable(metadata.table_id);
  const round = ensureRound(metadata.table_id, metadata.round_index, []);
  if (!round) return;
  if (metadata.memory_snapshot) agentMemorySnapshots[metadata.agent_id] = metadata.memory_snapshot;
  const list = round.querySelector("[data-contributions]");
  const speech = document.createElement("div");
  speech.className = "speech";
  const speechId = [
    metadata.table_id,
    metadata.round_index,
    metadata.agent_id,
    metadata.cycle_index,
    metadata.turn_index,
  ].join("-");
  speech.id = `speech-${speechId}`;
  speech.dataset.speakerName = metadata.agent_name || metadata.agent_id || "";
  speech.dataset.speakerId = metadata.agent_id || "";
  speech.dataset.tableId = metadata.table_id || "";
  speech.dataset.roundIndex = metadata.round_index ?? "";
  if (metadata.generation_error) {
    speech.classList.add("speech-error");
  }
  const turnLabel = Number.isFinite(Number(metadata.turn_index))
    ? ` · Turn ${Number(metadata.turn_index) + 1}`
    : "";
  const cycleLabel = Number.isFinite(Number(metadata.cycle_index))
    ? ` · Cycle ${Number(metadata.cycle_index) + 1}`
    : "";
  speech.innerHTML = `
    ${renderAgentMessage({
      className: "",
      agentId: metadata.agent_id,
      agentName: metadata.agent_name || metadata.agent_id,
      roleLabel: `${cycleLabel.replace(/^ · /, "")}${turnLabel}`,
      metaLabel: formatRoundStatusMeta(metadata),
      content: metadata.content || "",
      memorySnapshot: metadata.memory_snapshot,
      tone: "speaker",
    })}
  `;
  list.append(speech);
  scrollTableToBottom(round, shouldScroll);
  
  // Highlight active speaker seat on map
  const agents = currentTableAgents[metadata.table_id] || [metadata.agent_id];
  drawSeatingChart(null, metadata.table_id, agents, metadata.agent_id);
}

function appendHostRecord(metadata) {
  const shouldScroll = shouldFollowTableScrollByTable(metadata.table_id);
  const round = ensureRound(metadata.table_id, metadata.round_index, []);
  if (!round) return;
  if (metadata.memory_snapshot) agentMemorySnapshots[metadata.host_id] = metadata.memory_snapshot;
  const slot = round.querySelector("[data-host-record]");
  slot.innerHTML = `
    ${renderAgentMessage({
      className: "host-record",
      agentId: metadata.host_id,
      agentName: tableHostLabel(metadata.table_id),
      roleLabel: "Host Record",
      metaLabel: formatRoundStatusMeta(metadata),
      content: metadata.content || "",
      memorySnapshot: metadata.memory_snapshot,
      tone: "host",
    })}
  `;
  decorateHostNoteTarget(slot.querySelector(".host-record"), metadata, "host_record");
  scrollTableToBottom(round, shouldScroll);
  
  // Highlight host seat on map
  const agents = currentTableAgents[metadata.table_id] || [metadata.host_id];
  drawSeatingChart(null, metadata.table_id, agents, metadata.host_id);
}

function tableHostLabel(tableId) {
  const match = String(tableId || "").match(/(\d+)$/);
  const number = match ? String(Number(match[1])) : String(tableId || "?");
  return `tb${number}`;
}

function decorateHostNoteTarget(element, metadata, kind) {
  if (!element) return;
  const tableId = metadata.table_id || "";
  const roundIndex = metadata.round_index ?? "";
  const hostId = metadata.host_id || "";
  element.id = `speech-${tableId}-${roundIndex}-${hostId}-${kind}`;
  element.dataset.speakerName = tableHostLabel(tableId);
  element.dataset.speakerId = hostId;
  element.dataset.tableId = tableId;
  element.dataset.roundIndex = roundIndex;
}

function renderAgentMessage({
  className,
  agentId,
  agentName,
  roleLabel,
  metaLabel,
  content,
  memorySnapshot,
  tone,
}) {
  const initials = agentInitials(agentName || agentId);
  const classes = ["agent-message", className, tone === "host" ? "host-tone" : "speaker-tone"]
    .filter(Boolean)
    .join(" ");
  return `
    <div class="${escapeHtml(classes)}">
      <button class="message-avatar" type="button" aria-label="${escapeHtml(agentName || agentId)} internal memory" data-avatar-agent-id="${escapeHtml(agentId)}">
        <span>${escapeHtml(initials)}</span>
        ${renderMemoryTooltip(agentName || agentId, memorySnapshot)}
      </button>
      <div class="message-bubble">
        <div class="message-meta">
          <strong data-meta-agent-id="${escapeHtml(agentId)}">${escapeHtml(agentName || agentId)}</strong>
          <span>${escapeHtml(roleLabel || "")}</span>
          <em>${escapeHtml(metaLabel || "")}</em>
        </div>
        <div class="markdown-lite">${renderMarkdownLite(content || "")}</div>
      </div>
    </div>
  `;
}

function renderMemoryTooltip(agentName, snapshot) {
  const body = renderMemoryTooltipBody(snapshot);
  return `
    <span class="memory-card" role="tooltip">
      <strong>${escapeHtml(agentName)} · Internal Memory</strong>
      ${body}
    </span>
  `;
}

function renderMemoryTooltipBody(snapshot) {
  if (!snapshot || typeof snapshot !== "object") {
    return "<p>No internal memory yet.</p>";
  }
  if (snapshot.kind === "table_host") {
    return renderHostMemoryTooltip(snapshot);
  }
  const rows = formatMemorySnapshot(snapshot);
  return rows.length
    ? rows.map((row) => `<p>${renderInlineMarkdown(escapeHtml(row))}</p>`).join("")
    : "<p>No internal memory yet.</p>";
}

function renderHostMemoryTooltip(snapshot) {
  const usage = snapshot.tablememory_usage_description
    ? `<p class="memory-usage">${escapeHtml(snapshot.tablememory_usage_description)}</p>`
    : "";
  const summary = `<p>Current table memory: ${escapeHtml(snapshot.living_summary || "None yet")}</p>`;
  const rounds = (snapshot.recent_rounds || [])
    .filter((round) => round && typeof round === "object")
    .map(renderMemoryRound)
    .join("");
  const fallbackRound = rounds || renderMemoryRound({
    round: snapshot.formatmemory?.round_index || "?",
    synthesis: snapshot.round_pattern_delta || "",
    repeated_themes: snapshot.formatmemory?.repeated_themes || snapshot.stable_patterns || [],
    minority_inspiring_views: snapshot.formatmemory?.minority_inspiring_views || snapshot.incomplete_or_weak_patterns || [],
    unresolved_tensions: snapshot.formatmemory?.unresolved_tensions || snapshot.tensions || [],
  });
  return `${usage}${summary}${fallbackRound}${renderMemoryList("Next-round question seeds", snapshot.next_round_question_seeds)}`;
}

function renderMemoryRound(round) {
  return `
    <section class="memory-round">
      <h4>Round ${escapeHtml(round.round || "?")}</h4>
      ${round.synthesis ? `<p class="memory-round-summary">${escapeHtml(round.synthesis)}</p>` : ""}
      ${renderMemoryList("Recurring Themes", round.repeated_themes)}
      ${renderMemoryList("Minority Signals", round.minority_inspiring_views)}
      ${renderMemoryList("Unresolved Tensions", round.unresolved_tensions)}
    </section>
  `;
}

function renderMemoryList(label, value) {
  if (!Array.isArray(value) || !value.length) return "";
  const items = value
    .filter((item) => item !== null && item !== undefined && String(item).trim())
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  if (!items) return "";
  return `<div class="memory-list"><span>${escapeHtml(label)}</span><ul>${items}</ul></div>`;
}

function renderSeatMemoryCard(agentName, roleTag, snapshot) {
  const rows = formatMemorySnapshot(snapshot);
  const sections = [];
  if (snapshot && snapshot.kind === "table_host") {
    const rounds = (snapshot.recent_rounds || [])
      .filter((round) => round && typeof round === "object")
      .map(renderSeatMemoryRound)
      .join("");
    if (rounds) sections.push(rounds);
  } else if (snapshot) {
    if (snapshot.personal_insight && snapshot.personal_insight !== "暂无迁移记忆。") {
      sections.push(`<div class="smc-section"><div class="smc-section-title">🧠 personal_insight</div><div class="smc-section-body">${escapeHtml(snapshot.personal_insight)}</div></div>`);
    }
  }
  const body = sections.length
    ? sections.join("")
    : '<div class="smc-empty">No internal memory yet</div>';
  return `
    <div class="smc-header">
      <span class="smc-name">${escapeHtml(agentName)}</span>
      <span class="smc-role">${escapeHtml(roleTag)}</span>
    </div>
    <div class="smc-body">${body}</div>
  `;
}

function renderSeatMemoryRound(round) {
  return `
    <div class="smc-section smc-round">
      <div class="smc-section-title">Round ${escapeHtml(round.round || "?")}</div>
      ${round.synthesis ? `<div class="smc-section-body">${escapeHtml(round.synthesis)}</div>` : ""}
      ${renderSeatMemoryList("Recurring Themes", round.repeated_themes)}
      ${renderSeatMemoryList("Minority Signals", round.minority_inspiring_views)}
      ${renderSeatMemoryList("Unresolved Tensions", round.unresolved_tensions)}
    </div>
  `;
}

function renderSeatMemoryList(label, value) {
  if (!Array.isArray(value) || !value.length) return "";
  const items = value
    .filter((item) => item !== null && item !== undefined && String(item).trim())
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  if (!items) return "";
  return `<div class="smc-sublist"><span>${escapeHtml(label)}</span><ul class="smc-list">${items}</ul></div>`;
}

// Dismiss seat memory popovers when clicking outside
document.addEventListener("click", () => {
  document.querySelectorAll(".seat-memory-popover.visible").forEach((p) => p.classList.remove("visible"));
});

function formatMemorySnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== "object") return [];
  const rows = [];
  if (snapshot.kind === "table_host") {
    (snapshot.recent_rounds || []).forEach((round) => {
      addListRows(rows, `第 ${round.round} 轮重复主题`, round.repeated_themes);
      addListRows(rows, `第 ${round.round} 轮少数启发`, round.minority_inspiring_views);
      addListRows(rows, `第 ${round.round} 轮未解张力`, round.unresolved_tensions);
    });
    return rows;
  }
  if (snapshot.personal_insight && snapshot.personal_insight !== "暂无迁移记忆。") {
    rows.push(`personal_insight: ${snapshot.personal_insight}`);
  }
  return rows;
}

function addListRows(rows, label, value) {
  if (!Array.isArray(value) || !value.length) return;
  rows.push(`${label}: ${value.join("; ")}`);
}

function addObjectRows(rows, label, value) {
  if (!value) return;
  if (typeof value === "string") {
    if (value.trim()) rows.push(`${label}: ${value}`);
    return;
  }
  if (Array.isArray(value)) {
    addListRows(rows, label, value);
    return;
  }
  if (typeof value === "object") {
    const compact = Object.entries(value)
      .filter(([, item]) => item !== null && item !== "")
      .map(([key, item]) => `${key}: ${item}`)
      .join("; ");
    if (compact) rows.push(`${label}: ${compact}`);
  }
}

function agentInitials(name) {
  const text = String(name || "?").trim();
  if (!text) return "?";
  const asciiWords = text.match(/[A-Za-z0-9]+/g);
  if (asciiWords?.length) {
    return asciiWords.slice(0, 2).map((word) => word[0]).join("").toUpperCase();
  }
  return [...text].slice(0, 2).join("");
}

function appendRotationRecord(metadata) {
  const assignments = metadata.assignments || {};
  const nextRound = Number.isFinite(Number(metadata.next_round_index))
    ? Number(metadata.next_round_index) + 1
    : "?";
  const afterRound = metadata.after_round_index ?? "unknown";
  Object.entries(assignments).forEach(([tableId, agentIds]) => {
    const table = tablesGrid.querySelector(`[data-table-id="${tableId}"]`);
    if (!table) return;
    const list = table.querySelector("[data-round-list]");
    let record = list.querySelector(`[data-rotation-after="${afterRound}"]`);
    if (!record) {
      record = document.createElement("div");
      record.className = "rotation-record";
      record.dataset.rotationAfter = afterRound;
      list.append(record);
    }
    record.innerHTML = `
      <strong>Rotate To Round ${escapeHtml(nextRound)}</strong>
      <p>${escapeHtml(formatRotatedAssignment(agentIds || []))}</p>
    `;
  });
}

function isNearBottom(el, threshold = 60) {
  return el.scrollHeight - el.scrollTop - el.clientHeight <= threshold;
}

function shouldFollowTableScrollByTable(tableId) {
  const table = tablesGrid.querySelector(`[data-table-id="${tableId}"]`);
  const list = table?.querySelector("[data-round-list]");
  return !list || isNearBottom(list);
}

function scrollTableToBottom(round, shouldScroll = true) {
  const list = round.closest(".round-list");
  if (!list || !shouldScroll) return;
  list.scrollTop = list.scrollHeight;
}

function renderHarvest(markdown) {
  harvestContent.classList.remove("muted");
  harvestContent.innerHTML = renderMarkdownLite(markdown || "No harvest generated.");
  expandBottomPanel("harvest");
}

function resetRunView() {
  traceTotal = 0;
  currentRound = 0;
  maxRounds = 0;
  speechesPerAgent = getSpeechesPerAgent();
  isPaused = false;
  seenEventKeys = new Set();
  agentMemorySnapshots = {};
  notebookEntries = [];
  noteSequence = 0;
  userActivityLog = [];
  pendingNoteSelection = null;
  pendingNoteCheckpoints = [];
  activeNoteCheckpoint = null;
  pauseBtn.disabled = true;
  pauseBtn.textContent = "Pause to Annotate";
  addNoteBtn.disabled = true;
  hideNoteCheckpointPanel();
  hideQuestionEditorView();
  discussionPane.classList.remove("paused");
  // Clear gated-pulse highlight
  document.querySelectorAll(".table-card").forEach(card => card.classList.remove("gated-pulse"));
  traceCount.textContent = "0 events";
  harvestContent.classList.add("muted");
  harvestContent.textContent = "等待讨论完成";
  tablesGrid.innerHTML = "";
  resetAgentRoleStatuses();
  renderNotebook();
  phaseTrack.querySelectorAll("span").forEach((item) => {
    item.classList.remove("active", "done");
  });
}

function resetAgentRoleStatuses() {
  updateAgentStatus("host", {
    status: "Idle",
    detail: "Waiting to record and maintain table memory.",
    meta: "No active table",
  });
  updateAgentStatus("speaker", {
    status: "Idle",
    detail: "Waiting to join table discussions.",
    meta: "No active speaker",
  });
  updateAgentStatus("rotation", {
    status: "Idle",
    detail: "Waiting for participants to rotate between tables.",
    meta: "No route yet",
  });
  updateAgentStatus("harvest", {
    status: "Idle",
    detail: "Waiting to synthesize cross-table patterns and design opportunities.",
    meta: "Not started",
  });
}

async function loadAgentsForSettings() {
  const needed = Math.max(16, getTableCount() * (getSpeakersPerTable() + 1));
  const data = await getJson(`/api/agents?count=${needed}`);
  availableAgents = data.agents || [];
}

function buildDefaultAssignments(tables) {
  const speakersPerTable = getSpeakersPerTable();
  hostAssignments = {};
  speakerAssignments = {};
  const agentIds = availableAgents.map((agent) => agent.id);
  tables.forEach((table, tableIndex) => {
    const hostStart = tables.length * speakersPerTable;
    const hostId = agentIds[(hostStart + tableIndex) % agentIds.length];
    hostAssignments[table.table_id] = hostId;
    const start = tableIndex * speakersPerTable;
    const speakers = [];
    for (let offset = 0; offset < speakersPerTable; offset += 1) {
      const agentId = agentIds[(start + offset) % agentIds.length];
      if (agentId !== hostId && !speakers.includes(agentId)) {
        speakers.push(agentId);
      }
    }
    speakerAssignments[table.table_id] = speakers;
  });
}

function formatRoundMeta(agentIds) {
  const agents = agentIds.length ? formatRotatedAssignment(agentIds) : "Waiting";
  return `${agents} · ${speechesPerAgent} turns each`;
}

function formatRotatedAssignment(agentIds) {
  return agentIds
    .map((agentId, index) => {
      const name = getAgentName(agentId);
      return index === 0 ? `Host stays: ${name}` : name;
    })
    .join(" · ");
}

function getAgentName(agentId) {
  if (!agentId) return "";
  return (
    activeRun?.agent_profiles?.[agentId]?.name ||
    availableAgents.find((agent) => agent.id === agentId)?.name ||
    agentId
  );
}

function getTableCount() {
  return clampNumber(tableCountInput.value, 1, 8, 3);
}

function getSpeakersPerTable() {
  return clampNumber(speakersInput.value, 1, 8, 2);
}

function getRoundCount() {
  return getTableCount();
}

function getSpeechesPerAgent() {
  return clampNumber(speechesInput.value, 1, 8, 3);
}

function clampNumber(value, min, max, fallback) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(max, Math.max(min, Math.round(number)));
}

function setPhase(phase) {
  const index = phaseOrder.indexOf(phase);
  if (index < 0) return;
  phaseTrack.querySelectorAll("span").forEach((item) => {
    const itemIndex = phaseOrder.indexOf(item.dataset.phase);
    item.classList.toggle("active", item.dataset.phase === phase);
    item.classList.toggle("done", itemIndex >= 0 && itemIndex < index);
  });
}

function setStatus(text, tone) {
  runStatus.textContent = text;
  runStatus.className = "status-pill";
  if (tone) runStatus.classList.add(tone);
}

function setBusy(isBusy) {
  facilitateBtn.disabled = isBusy;
  facilitateBtn.textContent = isBusy ? "Planning..." : "✦ Plan Topic";
}

function isNoteTakingActive() {
  return isPaused || Boolean(activeNoteCheckpoint);
}

function refreshNoteTakingControls() {
  discussionPane.classList.toggle("paused", isNoteTakingActive());
  pauseBtn.disabled = !activeRun || Boolean(activeNoteCheckpoint);
  pauseBtn.textContent = isPaused ? "继续讨论" : "暂停标注";
  addNoteBtn.disabled = !isNoteTakingActive() || !pendingNoteSelection;
  if (isNoteTakingActive()) expandBottomPanel("notebook");
  if (activeNoteCheckpoint) {
    renderActiveNoteCheckpoint();
  }
}

async function togglePause() {
  if (!activeRun) return;
  pauseBtn.disabled = true;
  try {
    if (!isPaused) {
      await postJson(`/api/runs/${activeRun.run_id}/pause`, {});
      isPaused = true;
      pendingNoteSelection = getSelectedDiscussionSelection() || pendingNoteSelection;
      refreshNoteTakingControls();
      setStatus("Pausing after current speaker", "running");
      return;
    }
    await postJson(`/api/runs/${activeRun.run_id}/resume`, {});
    isPaused = false;
    refreshNoteTakingControls();
    setStatus("Running", "running");
    if (!eventSource || eventSource.readyState === EventSource.CLOSED) {
      subscribeToRun(activeRun.run_id);
    }
  } catch (error) {
    addMessage("error", error.message);
  } finally {
    refreshNoteTakingControls();
  }
}

function handleNoteCheckpointEvent(event) {
  if (event.status === "waiting_for_notes") {
    enqueueNoteCheckpoint(event);
    return;
  }
  if (event.status === "notes_submitted") {
    finishNoteCheckpoint(event.checkpoint_id);
  }
}

function enqueueNoteCheckpoint(checkpoint) {
  if (!checkpoint?.checkpoint_id) return;
  if (activeNoteCheckpoint?.checkpoint_id === checkpoint.checkpoint_id) return;
  if (pendingNoteCheckpoints.some((item) => item.checkpoint_id === checkpoint.checkpoint_id)) return;
  if (!activeNoteCheckpoint) {
    activateNoteCheckpoint(checkpoint);
    return;
  }
  pendingNoteCheckpoints.push(checkpoint);
  renderActiveNoteCheckpoint();
}

function activateNoteCheckpoint(checkpoint) {
  activeNoteCheckpoint = checkpoint;
  noteCheckpointPanel.hidden = false;
  expandBottomPanel("notebook");
  setStatus(`待换桌 · ${checkpoint.table_id} R${Number(checkpoint.round_index) + 1}`, "running");
  
  // Highlight active checkpoint table card
  document.querySelectorAll(".table-card").forEach(card => card.classList.remove("gated-pulse"));
  const tableCard = document.querySelector(`.table-card[data-table-id="${checkpoint.table_id}"]`);
  if (tableCard) {
    tableCard.classList.add("gated-pulse");
    tableCard.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  updateAgentStatus("host", {
    status: "等待换桌",
    detail: `${checkpoint.table_id} 已暂停：请完成本轮设计洞察/机会笔记，点击"换桌"后桌长才会生成本轮记忆。`,
    meta: `第 ${Number(checkpoint.round_index) + 1} 轮`,
  });
  ensureRound(checkpoint.table_id, checkpoint.round_index, []);
  refreshNoteTakingControls();
}

function finishNoteCheckpoint(checkpointId) {
  pendingNoteCheckpoints = pendingNoteCheckpoints.filter((item) => item.checkpoint_id !== checkpointId);
  if (activeNoteCheckpoint?.checkpoint_id === checkpointId) {
    activeNoteCheckpoint = null;
    hideNoteCheckpointPanel();
    
    // Clear highlight
    document.querySelectorAll(".table-card").forEach(card => card.classList.remove("gated-pulse"));

    if (pendingNoteCheckpoints.length) {
      activateNoteCheckpoint(pendingNoteCheckpoints.shift());
    } else {
      setStatus("Running", "running");
      refreshNoteTakingControls();
    }
  }
}

function hideNoteCheckpointPanel() {
  if (noteCheckpointPanel) {
    noteCheckpointPanel.hidden = true;
  }
  if (continueNotesBtn) {
    continueNotesBtn.disabled = false;
    continueNotesBtn.textContent = "Rotate Table";
  }
}

function renderActiveNoteCheckpoint() {
  if (!activeNoteCheckpoint || !noteCheckpointPanel) return;
  const notes = getNotesForCheckpoint(activeNoteCheckpoint);
  const roundLabel = Number(activeNoteCheckpoint.round_index) + 1;
  if (noteCheckpointTitle) {
    noteCheckpointTitle.textContent = `${activeNoteCheckpoint.table_id} · R${roundLabel} · ${notes.length} 条笔记`;
  }
  if (continueNotesBtn) {
    continueNotesBtn.textContent = notes.length ? "提交并换桌" : "直接换桌";
  }
}

async function submitActiveNoteCheckpoint() {
  if (!activeRun || !activeNoteCheckpoint) return;
  const checkpoint = activeNoteCheckpoint;
  const notes = getNotesForCheckpoint(checkpoint).map(noteToPayload);
  continueNotesBtn.disabled = true;
  continueNotesBtn.textContent = "Rotating...";
  try {
    await postJson(`/api/runs/${activeRun.run_id}/note-checkpoint/continue`, {
      checkpoint_id: checkpoint.checkpoint_id,
      table_id: checkpoint.table_id,
      round_index: Number(checkpoint.round_index),
      action: "switch_table",
      notes,
    });
    updateAgentStatus("host", {
      status: "Generating Host Memory",
      detail: `${checkpoint.table_id}'s host is combining user-marked notes into internal memory before closing the round.`,
      meta: `${notes.length} notes · switch table`,
    });
    finishNoteCheckpoint(checkpoint.checkpoint_id);
  } catch (error) {
    addMessage("error", error.message);
    continueNotesBtn.disabled = false;
    renderActiveNoteCheckpoint();
  }
}

function getNotesForCheckpoint(checkpoint) {
  return notebookEntries.filter(
    (entry) =>
      entry.tableId === checkpoint.table_id &&
      Number(entry.roundIndex) === Number(checkpoint.round_index),
  );
}

function noteToPayload(entry) {
  return {
    id: entry.id,
    text: entry.text,
    table_id: entry.tableId,
    round_index: Number(entry.roundIndex),
    speaker_name: entry.speakerName,
    speaker_id: entry.speakerId,
    speech_id: entry.speechId,
    speech_target_id: entry.speechTargetId,
    created_at: entry.createdAt,
  };
}

function getSelectedDiscussionText() {
  const selectionInfo = getSelectedDiscussionSelection() || pendingNoteSelection;
  return selectionInfo?.text || "";
}

function getSelectedDiscussionSelection() {
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) return null;
  const text = selection.toString().trim();
  if (!text) return null;
  const anchorSpeech = getClosestSpeech(selection.anchorNode);
  const focusSpeech = getClosestSpeech(selection.focusNode);
  if (!anchorSpeech || anchorSpeech !== focusSpeech) return null;
  return {
    text,
    speech: anchorSpeech,
    range: selection.getRangeAt(0).cloneRange(),
  };
}

function getClosestSpeech(node) {
  if (!node) return null;
  const element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
  return element?.closest(".speech, .host-opening, .host-record") || null;
}

function addSelectedNote() {
  const selectionInfo = getSelectedDiscussionSelection() || pendingNoteSelection;
  if (!selectionInfo) return;
  const { text, speech, range } = selectionInfo;
  const noteId = `note-${++noteSequence}`;
  const highlighted = highlightSelectionRange(range, noteId);
  const roundBlock = speech.closest("[data-round-index]");
  const tableCard = speech.closest("[data-table-id]");
  const tableId = speech.dataset.tableId || tableCard?.dataset.tableId || activeNoteCheckpoint?.table_id || "";
  const roundIndexValue = speech.dataset.roundIndex || roundBlock?.dataset.roundIndex;
  const roundIndex = Number.isFinite(Number(roundIndexValue))
    ? Number(roundIndexValue)
    : Number(activeNoteCheckpoint?.round_index);
  const noteEntry = {
    id: noteId,
    text,
    speakerName: speech.dataset.speakerName || "Unknown speaker",
    speakerId: speech.dataset.speakerId || "",
    tableId,
    roundIndex,
    speechId: speech.id,
    speechTargetId: highlighted?.id || speech.id,
    round: Number.isFinite(roundIndex) ? roundIndex + 1 : currentRound,
    createdAt: new Date().toLocaleTimeString(),
  };
  notebookEntries = [...notebookEntries, noteEntry];
  recordUserAction("note_added", noteToLogEntry(noteEntry));
  window.getSelection()?.removeAllRanges();
  pendingNoteSelection = null;
  renderNotebook();
  refreshNoteTakingControls();
  addNoteBtn.disabled = true;
}

function renderNotebook() {
  notebookCount.textContent = `已记录 ${notebookEntries.length} 条笔记`;
  notebookList.innerHTML = "";
  notebookEntries.forEach((entry, index) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "notebook-entry";
    item.dataset.noteTarget = entry.id;
    item.innerHTML = `
      <div class="notebook-entry-meta">#${index + 1} · ${escapeHtml(entry.tableId || "?")} · ${escapeHtml(entry.speakerName)} · Round ${entry.round || "?"} · ${escapeHtml(entry.createdAt)}</div>
      <p>${escapeHtml(entry.text)}</p>
    `;
    item.addEventListener("click", () => jumpToNote(entry));
    notebookList.append(item);
  });
}

function highlightSelectionRange(range, noteId) {
  const speech = getClosestSpeech(range.commonAncestorContainer);
  if (!speech) return null;
  const simpleMark = document.createElement("mark");
  simpleMark.className = "user-note-highlight";
  simpleMark.dataset.noteId = noteId;
  try {
    simpleMark.append(range.extractContents());
    range.insertNode(simpleMark);
    return simpleMark;
  } catch {
    simpleMark.remove();
  }

  const textNodes = [];
  const walker = document.createTreeWalker(
    speech,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        if (!node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        if (node.parentElement?.closest(".user-note-highlight")) {
          return NodeFilter.FILTER_REJECT;
        }
        return range.intersectsNode(node)
          ? NodeFilter.FILTER_ACCEPT
          : NodeFilter.FILTER_REJECT;
      },
    },
  );
  while (walker.nextNode()) {
    textNodes.push(walker.currentNode);
  }
  textNodes.reverse().forEach((node) => {
    const start = node === range.startContainer ? range.startOffset : 0;
    const end = node === range.endContainer ? range.endOffset : node.nodeValue.length;
    if (start >= end) return;
    const after = node.splitText(end);
    const selected = node.splitText(start);
    const mark = document.createElement("mark");
    mark.className = "user-note-highlight";
    mark.dataset.noteId = noteId;
    selected.parentNode.insertBefore(mark, after);
    mark.append(selected);
  });
  return document.querySelector(`[data-note-id="${noteId}"]`);
}

function jumpToNote(entry) {
  const target =
    document.querySelector(`[data-note-id="${entry.id}"]`) ||
    document.getElementById(entry.speechTargetId || entry.speechId);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "center" });
  target.classList.add("note-jump-focus");
  window.setTimeout(() => target.classList.remove("note-jump-focus"), 1400);
}

function clearBackground() {
  backgroundContext = "";
  backgroundFilename = "";
  backgroundFileInput.value = "";
  backgroundSummary.textContent = "No background file uploaded";
  clearBackgroundBtn.hidden = true;
}

function addMessage(kind, content) {
  const message = document.createElement("div");
  message.className = `message ${kind}`;
  if (kind === "facilitator") {
    message.innerHTML = `<div class="markdown-lite">${renderMarkdownLite(content)}</div>`;
  } else {
    message.textContent = content;
  }
  const shouldScroll = isNearBottom(chatLog);
  chatLog.append(message);
  if (shouldScroll) chatLog.scrollTop = chatLog.scrollHeight;
}

function formatQuestions(tables) {
  return tables
    .map((table) => {
      return `${table.table_id}: ${table.question}`;
    })
    .join("\n\n");
}

async function getJson(url) {
  const response = await fetch(url);
  return readJsonResponse(response);
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  return readJsonResponse(response);
}

async function readJsonResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `Request failed: ${response.status}`);
  }
  return data;
}


function recordUserAction(type, details = {}) {
  userActivityLog = [
    ...userActivityLog,
    {
      type,
      timestamp: new Date().toISOString(),
      run_id: activeRun?.run_id || "",
      current_round: currentRound,
      active_checkpoint: activeNoteCheckpoint
        ? {
            checkpoint_id: activeNoteCheckpoint.checkpoint_id,
            table_id: activeNoteCheckpoint.table_id,
            round_index: activeNoteCheckpoint.round_index,
          }
        : null,
      details,
    },
  ];
}

function getButtonLabel(button) {
  return (button.innerText || button.textContent || button.getAttribute("aria-label") || button.id || "")
    .replace(/\s+/g, " ")
    .trim();
}

function getFinalInsightContents() {
  return [...document.querySelectorAll("[data-final-insight]")].map((textarea) => ({
    key: textarea.dataset.finalInsight || "",
    label: textarea.closest("label")?.querySelector("span")?.textContent?.trim() || textarea.dataset.finalInsight || "",
    content: textarea.value.trim(),
  }));
}

function getUserFinalSubmission() {
  const fields = getFinalInsightContents();
  return {
    submitted_at: new Date().toISOString(),
    fields,
    text: fields
      .filter((field) => field.content)
      .map((field) => `${field.label || field.key}: ${field.content}`)
      .join("\n\n"),
  };
}

function getGlobalHarvestExport() {
  return {
    markdown: harvestContent?.innerHTML || "",
    text: harvestContent?.innerText?.trim() || "",
  };
}

function getNotebookStats() {
  const byTable = {};
  const byRound = {};
  notebookEntries.forEach((entry) => {
    const tableKey = entry.tableId || "unknown";
    const roundKey = Number.isFinite(Number(entry.roundIndex)) ? String(Number(entry.roundIndex) + 1) : "unknown";
    byTable[tableKey] = (byTable[tableKey] || 0) + 1;
    byRound[roundKey] = (byRound[roundKey] || 0) + 1;
  });
  return {
    total: notebookEntries.length,
    by_table: byTable,
    by_round: byRound,
  };
}

function getRunLogSummary() {
  if (!activeRun) return null;
  return {
    run_id: activeRun.run_id || "",
    status: activeRun.status || runStatus.textContent || "",
    table_count: activeRun.table_count || Object.keys(activeRun.table_questions || {}).length || getTableCount(),
    rounds: activeRun.rounds || maxRounds || getRoundCount(),
    speakers_per_table: activeRun.speakers_per_table || getSpeakersPerTable(),
    speeches_per_agent: activeRun.speeches_per_agent || speechesPerAgent || getSpeechesPerAgent(),
  };
}

function noteToLogEntry(entry) {
  return {
    id: entry.id,
    text: entry.text,
    table_id: entry.tableId,
    round_index: Number(entry.roundIndex),
    round: entry.round,
    speaker_name: entry.speakerName,
    speaker_id: entry.speakerId,
    speech_id: entry.speechId,
    speech_target_id: entry.speechTargetId,
    created_at: entry.createdAt,
  };
}

function getTableChatHistories() {
  return [...tablesGrid.querySelectorAll(".table-card")].map((table) => {
    const tableId = table.dataset.tableId || "";
    const records = [...table.querySelectorAll(".host-opening, .speech, .host-record")].map((item) => {
      const meta = item.querySelector(".message-meta");
      return {
        id: item.id || "",
        table_id: item.dataset.tableId || tableId,
        round_index: Number.isFinite(Number(item.dataset.roundIndex)) ? Number(item.dataset.roundIndex) : null,
        round: Number.isFinite(Number(item.dataset.roundIndex)) ? Number(item.dataset.roundIndex) + 1 : null,
        speaker_name: item.dataset.speakerName || meta?.querySelector("strong")?.textContent?.trim() || "",
        speaker_id: item.dataset.speakerId || "",
        role_label: meta?.querySelector("span")?.textContent?.trim() || "",
        meta_label: meta?.querySelector("em")?.textContent?.trim() || "",
        content: item.querySelector(".markdown-lite")?.innerText?.trim() || "",
        kind: item.classList.contains("host-opening")
          ? "host_opening"
          : item.classList.contains("host-record")
            ? "host_record"
            : "agent_contribution",
      };
    });
    return {
      table_id: tableId,
      table_question: table.dataset.tableQuestion || "",
      history: records,
    };
  });
}

function downloadActivityLog() {
  const userNotes = notebookEntries.map(noteToLogEntry);
  const finalSubmission = getUserFinalSubmission();
  const globalHarvest = getGlobalHarvestExport();
  recordUserAction("activity_log_downloaded", {
    event_count_before_download: userActivityLog.length,
    user_note_count: userNotes.length,
    table_history_count: getTableChatHistories().reduce((total, table) => total + table.history.length, 0),
    final_submission_fields: finalSubmission.fields.length,
    global_harvest_chars: globalHarvest.text.length,
  });
  const payload = {
    generated_at: new Date().toISOString(),
    run: getRunLogSummary(),
    notebook_stats: getNotebookStats(),
    user_notes: userNotes,
    notes: userNotes,
    table_chat_histories: getTableChatHistories(),
    global_harvest: globalHarvest,
    user_final_submission: finalSubmission,
    final_insights: finalSubmission.fields,
    activity_log: userActivityLog,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const runId = activeRun?.run_id || "no-run";
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  link.href = url;
  link.download = `agent-cafe-user-log-${runId}-${stamp}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function renderMarkdownLite(markdown) {
  const lines = escapeHtml(emphasizeDesignOpportunities(markdown)).split(/\r?\n/);
  const html = [];
  let inList = false;

  const closeList = () => {
    if (inList) {
      html.push("</ul>");
      inList = false;
    }
  };

  lines.forEach((line) => {
    if (line.startsWith("### ")) {
      closeList();
      html.push(`<h3>${renderInlineMarkdown(line.slice(4))}</h3>`);
      return;
    }
    if (line.startsWith("## ")) {
      closeList();
      html.push(`<h2>${renderInlineMarkdown(line.slice(3))}</h2>`);
      return;
    }
    if (line.startsWith("- ")) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${renderInlineMarkdown(line.slice(2))}</li>`);
      return;
    }
    if (!line.trim()) {
      closeList();
      html.push("<br />");
      return;
    }
    closeList();
    html.push(`<p>${renderInlineMarkdown(line)}</p>`);
  });

  closeList();
  return html.join("");
}

const designOpportunityTerms = [
  "design opportunity",
  "new design opportunity",
  "opportunity hypothesis",
  "opportunity signal",
  "potential opportunity",
  "opportunity",
  "opportunities",
];

const designOpportunityPattern = new RegExp(
  designOpportunityTerms.map(escapeRegExp).join("|"),
  "i",
);

const designOpportunitySentencePattern = new RegExp(
  `([^。！？!?；;\\n]*(?:${designOpportunityTerms.map(escapeRegExp).join("|")})[^。！？!?；;\\n]*(?:[。！？!?；;]|$))`,
  "gi",
);

function emphasizeDesignOpportunities(markdown) {
  const text = String(markdown || "");
  if (!designOpportunityPattern.test(text)) return text;
  return text
    .split("```")
    .map((block, index) => {
      if (index % 2 === 1) return block;
      return block.split(/\r?\n/).map(emphasizeDesignOpportunityLine).join("\n");
    })
    .join("```");
}

function emphasizeDesignOpportunityLine(line) {
  if (!designOpportunityPattern.test(line) || line.includes("**") || line.trimStart().startsWith("#")) {
    return line;
  }
  const prefix = line.match(/^(\s*(?:[-*]\s+|\d+\.\s+)?)/)?.[1] || "";
  const body = line.slice(prefix.length);
  return prefix + body.replace(designOpportunitySentencePattern, (sentence) => {
    const leading = sentence.match(/^\s*/)?.[0] || "";
    const trailing = sentence.match(/\s*$/)?.[0] || "";
    const core = sentence.trim();
    return core ? `${leading}**${core}**${trailing}` : sentence;
  });
}

function renderInlineMarkdown(html) {
  return html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/* ── Bottom Panel Tab Logic ── */
const bottomPanel = document.querySelector("#bottomPanel");
const bottomPanelToggle = document.querySelector("#bottomPanelToggle");

if (bottomPanel && bottomPanelToggle) {
  bottomPanel.addEventListener("click", (e) => {
    const tab = e.target.closest(".bottom-tab");
    if (tab) {
      bottomPanel.querySelectorAll(".bottom-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const key = tab.dataset.tab;
      bottomPanel.dataset.activeTab = key || "";
      bottomPanel.querySelectorAll(".bottom-tab-content").forEach(c => c.classList.toggle("active", c.dataset.tab === key));
      setBottomPanelExpanded(true);
    }
  });
  bottomPanelToggle.addEventListener("click", () => {
    setBottomPanelExpanded(!bottomPanel.classList.contains("expanded"));
  });
  bottomPanel.dataset.activeTab = bottomPanel.querySelector(".bottom-tab.active")?.dataset.tab || "notebook";
  syncBottomPanelLayoutState();
}

function setBottomPanelExpanded(expanded) {
  if (!bottomPanel) return;
  bottomPanel.classList.toggle("expanded", expanded);
  syncBottomPanelLayoutState();
}

function syncBottomPanelLayoutState() {
  appShell?.classList.toggle("bottom-panel-expanded", Boolean(bottomPanel?.classList.contains("expanded")));
}

function expandBottomPanel(tabKey) {
  if (!bottomPanel) return;
  if (tabKey) {
    bottomPanel.dataset.activeTab = tabKey;
    bottomPanel.querySelectorAll(".bottom-tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tabKey));
    bottomPanel.querySelectorAll(".bottom-tab-content").forEach(c => c.classList.toggle("active", c.dataset.tab === tabKey));
  }
  setBottomPanelExpanded(true);
}
