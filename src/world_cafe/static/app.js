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
const roundsInput = document.querySelector("#roundCount");
const speechesInput = document.querySelector("#speechesPerAgent");
const pauseBtn = document.querySelector("#pauseBtn");
const addNoteBtn = document.querySelector("#addNoteBtn");
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
const clearBackgroundBtn = document.querySelector("#clearBackgroundBtn");
const agentStatusDock = document.querySelector("#agentStatusDock");
const newOrderBtn = document.querySelector("#newOrderBtn");
const appShell = document.querySelector(".app-shell");

let facilitatedTables = [];
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
let pendingNoteSelection = null;
let pendingNoteCheckpoints = [];
let activeNoteCheckpoint = null;
let availableAgents = [];
let hostAssignments = {};
let speakerAssignments = {};
let backgroundContext = "";
let backgroundFilename = "";
let currentTableAgents = {};

const phaseOrder = ["facilitate", "setup", "round_started", "rotation", "harvest", "done"];
const agentRoleStatuses = {
  facilitator: {
    label: "引导主持",
    initials: "F",
    tone: "green",
    status: "就绪",
    detail: "等待梳理各桌研讨问题。",
    meta: "空闲",
    time: "",
  },
  host: {
    label: "咖啡桌长",
    initials: "H",
    tone: "amber",
    status: "空闲",
    detail: "等待记录并维护各桌研讨记忆。",
    meta: "暂无活跃桌",
    time: "",
  },
  speaker: {
    label: "发言代表",
    initials: "S",
    tone: "blue",
    status: "空闲",
    detail: "等待参与各桌子研讨。",
    meta: "暂无活跃发言",
    time: "",
  },
  rotation: {
    label: "桌次轮换",
    initials: "R",
    tone: "rose",
    status: "空闲",
    detail: "等待代表在不同研讨桌之间轮换。",
    meta: "暂无路径",
    time: "",
  },
  harvest: {
    label: "全局总结",
    initials: "G",
    tone: "green",
    status: "空闲",
    detail: "等待提炼跨桌的共性模式与设计机会。",
    meta: "未开始",
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
    renderQuestionEditor(facilitatedTables);
  }
});

backgroundFileInput.addEventListener("change", async () => {
  const file = backgroundFileInput.files?.[0];
  if (!file) {
    clearBackground();
    return;
  }
  const lowerName = file.name.toLowerCase();
  if (!lowerName.endsWith(".md") && !lowerName.endsWith(".markdown")) {
    addMessage("error", "请上传 .md 或 .markdown 背景材料。");
    clearBackground();
    return;
  }
  backgroundContext = await file.text();
  backgroundFilename = file.name;
  backgroundSummary.textContent = `${backgroundFilename} · ${backgroundContext.length} 字符`;
  clearBackgroundBtn.hidden = false;
});

clearBackgroundBtn.addEventListener("click", clearBackground);
pauseBtn.addEventListener("click", togglePause);
addNoteBtn.addEventListener("mousedown", (event) => event.preventDefault());
addNoteBtn.addEventListener("click", addSelectedNote);
continueNotesBtn?.addEventListener("click", submitActiveNoteCheckpoint);

// Delegate clicks on agent elements to show details modal
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
  addMessage("facilitator", "世界咖啡研讨准备就绪。");
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
  if (role) role.textContent = profile.role || "研讨代表";
  if (skills) {
    skills.innerHTML = (profile.skills || []).map(skill => `<span>${escapeHtml(skill)}</span>`).join("");
  }
  if (style) style.textContent = profile.style || "暂无风格描述。";

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
    tableCountInput.value = config.default_table_count || 4;
    speakersInput.value = config.default_speakers_per_table || 3;
    roundsInput.value = config.default_rounds || 3;
    speechesInput.value = config.default_speeches_per_agent || 3;
    speechesPerAgent = getSpeechesPerAgent();
    if (!config.token_configured) {
      modelBadge.textContent += " · 未配置 Token";
    }
  } catch {
    modelBadge.textContent = "配置不可用";
  }

  addMessage("facilitator", "世界咖啡研讨准备就绪。");
  renderAgentStatusDock();
  await loadAgentsForSettings();
}

requestForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const request = requestInput.value.trim();
  if (!request) return;

  addMessage("user", request);
  updateAgentStatus("facilitator", {
    status: "读取上下文中",
    detail: "正在为各桌生成研讨引导问题。",
    meta: `已请求 ${getTableCount()} 桌`,
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
    updateAgentStatus("facilitator", {
      status: "引导问题已就绪",
      detail: "已成功为各桌生成一个研讨引导问题。",
      meta: `共 ${facilitatedTables.length} 桌问题`,
    });
    addMessage("facilitator", formatQuestions(facilitatedTables));
    await loadAgentsForSettings();
    renderQuestionEditor(facilitatedTables);
    startBtn.disabled = false;
  } catch (error) {
    updateAgentStatus("facilitator", {
      status: "错误",
      detail: error.message,
      meta: "引导生成失败",
    });
    setStatus("引导方案错误", "error");
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
    status: "研讨配置就绪",
    detail: "各桌研讨方案配置已就绪，流程图正在启动中。",
    meta: `${tables.length} 桌 · ${getRoundCount()} 轮`,
  });
  setStatus("正在启动", "running");
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
    setStatus("进行中", "running");
    updateAgentStatus("facilitator", {
      status: "流程已启动",
      detail: "世界咖啡流程引擎已在运行中。",
      meta: activeRun ? `已启动 ${activeRun.table_count} 桌` : "研讨进行中",
    });
    return;
  }
  if (event.type === "pause_changed") {
    if (event.status === "pause_requested") {
      setStatus("等待当前发言结束后暂停", "running");
    } else if (event.status === "paused") {
      setStatus("等待记录笔记", "running");
    } else if (event.status === "running") {
      setStatus("进行中", "running");
    }
    return;
  }
  if (event.type === "note_checkpoint") {
    handleNoteCheckpointEvent(event);
    return;
  }
  if (event.type === "error") {
    setStatus("错误", "error");
    updateAgentStatus("facilitator", {
      status: "错误",
      detail: event.message || "研讨流程报告了错误。",
      meta: "需要处理",
    });
    addMessage("error", event.message || "运行出错，但后端没有返回详细错误。");
    newOrderBtn.hidden = false;
    return;
  }
  if (event.type === "run_complete") {
    setStatus("已完成", "");
    setPhase("done");
    updateAgentStatus("harvest", {
      status: "已完成",
      detail: "全局收获汇总已完成，最终讨论洞察成果已就绪。",
      meta: `已处理 ${traceTotal} 个事件`,
    });
    renderHarvest(event.harvest?.content || "");
    addMessage("facilitator", "研讨成果全局收获汇总已完成。");
    facilitateBtn.disabled = false;
    pauseBtn.disabled = true;
    pauseBtn.textContent = "暂停标注";
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
  traceCount.textContent = `${traceTotal} 个事件`;
  setPhase(event.stage);

  if (event.stage === "round_started") {
    currentRound = (metadata.round_index || 0) + 1;
    roundBadge.textContent = `${currentRound} / ${maxRounds}`;
    setStatus(`第 ${currentRound} 轮`, "running");
    updateAgentStatus("speaker", {
      status: `第 ${currentRound} 轮就绪`,
      detail: "发言代表已分配到本轮各研讨桌。",
      meta: summarizeAssignments(metadata.assignments || {}),
    });
    updateAgentStatus("host", {
      status: `第 ${currentRound} 轮倾听中`,
      detail: "各桌桌长已准备好记录局部讨论记忆并处理讨论线索。",
      meta: `${Object.keys(metadata.assignments || {}).length} 个活动研讨桌`,
    });
    Object.entries(metadata.assignments || {}).forEach(([tableId, agentIds]) => {
      ensureRound(tableId, metadata.round_index || 0, agentIds);
    });
  }

  if (event.stage === "table_discussion") {
    ensureRound(metadata.table_id, metadata.round_index || 0, metadata.agent_ids || []);
    updateAgentStatus("speaker", {
      status: "研讨讨论中",
      detail: `${metadata.table_id || "研讨桌"} 的讨论正活跃进行中。`,
      meta: formatRoundStatusMeta(metadata),
    });
    updateAgentStatus("host", {
      status: "观察桌子中",
      detail: `桌长 ${metadata.host_id || "桌长"} 正在维护 ${metadata.table_id || "该桌"} 的研讨记忆。`,
      meta: formatRoundStatusMeta(metadata),
    });
  }

  if (event.stage === "host_opening") {
    updateAgentStatus("host", {
      status: "开启讨论轮次",
      detail: `桌长 ${metadata.host_name || metadata.host_id || "桌长"} 带着引导线索开启了 ${metadata.table_id || "研讨桌"} 的讨论。`,
      meta: formatRoundStatusMeta(metadata),
    });
    appendHostOpening(metadata);
  }

  if (event.stage === "agent_contribution") {
    updateAgentStatus("speaker", {
      status: "代表发言中",
      detail: `发言代表 ${metadata.agent_name || metadata.agent_id || "代表"} 对 ${metadata.table_id || "研讨桌"} 发表了意见。`,
      meta: formatTurnStatusMeta(metadata),
    });
    appendContribution(metadata);
  }

  if (event.stage === "host_record") {
    updateAgentStatus("host", {
      status: "记录桌子记忆",
      detail: `桌长 ${metadata.host_name || metadata.host_id || "桌长"} 更新并保存了 ${metadata.table_id || "研讨桌"} 的讨论记忆。`,
      meta: formatRoundStatusMeta(metadata),
    });
    appendHostRecord(metadata);
  }

  if (event.stage === "rotation") {
    setStatus(`正在轮换至第 ${(metadata.next_round_index || 0) + 1} 轮`, "running");
    updateAgentStatus("rotation", {
      status: "代表轮换中",
      detail: "非桌长的发言代表正在轮换去下一张研讨桌。",
      meta: formatRotationMeta(metadata),
    });
    appendRotationRecord(metadata);
  }

  if (event.stage === "harvest") {
    setStatus("正在全局成果提炼", "running");
    updateAgentStatus("harvest", {
      status: "全局成果汇总中",
      detail: "全局成果总结正在对共性模式、弱信号、张力以及设计机会进行聚类提炼。",
      meta: `${metadata.round_count || maxRounds || "?"} 轮研讨`,
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
    time: new Date().toLocaleTimeString(),
  };
  renderAgentStatusDock();
}

function summarizeAssignments(assignments) {
  const tableCount = Object.keys(assignments).length;
  const speakerCount = Object.values(assignments).reduce(
    (count, agents) => count + Math.max((agents || []).length - 1, 0),
    0,
  );
  return `${tableCount} 桌 · ${speakerCount} 位发言代表`;
}

function formatRoundStatusMeta(metadata) {
  const round = Number.isFinite(Number(metadata.round_index))
    ? `第 ${Number(metadata.round_index) + 1} 轮`
    : "第 ? 轮";
  const parts = [`${metadata.table_id || "研讨桌 ?"} · ${round}`];
  if (Object.prototype.hasOwnProperty.call(metadata, "background_context_chars")) {
    parts.push(`背景 ${Number(metadata.background_context_chars) || 0} 字符`);
  }
  return parts.join(" · ");
}

function formatRotationMeta(metadata) {
  const tableCount = Object.keys(metadata.assignments || {}).length;
  const nextRound = Number.isFinite(Number(metadata.next_round_index))
    ? Number(metadata.next_round_index) + 1
    : "?";
  return `${tableCount || "?"} 桌 · 第 ${nextRound} 轮`;
}

function formatTurnStatusMeta(metadata) {
  const roundMeta = formatRoundStatusMeta(metadata);
  const turn = Number.isFinite(Number(metadata.turn_index))
    ? `总第 ${Number(metadata.turn_index) + 1} 位`
    : "总第 ? 位";
  const cycle = Number.isFinite(Number(metadata.cycle_index))
    ? `第 ${Number(metadata.cycle_index) + 1} 次发言`
    : "第 ? 次发言";
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

function renderQuestionEditor(tables) {
  showQuestionEditorView();
  questionEditor.innerHTML = "";
  buildDefaultAssignments(tables);
  tables.forEach((table) => {
    const field = document.createElement("div");
    field.className = "question-field";
    field.innerHTML = `
      <label for="${table.table_id}">${table.table_id}</label>
      <textarea id="${table.table_id}" data-table-id="${table.table_id}">${escapeHtml(table.question)}</textarea>
    `;
    questionEditor.append(field);
    questionEditor.append(renderAssignmentField(table.table_id));
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

function renderAssignmentField(tableId) {
  const wrapper = document.createElement("div");
  wrapper.className = "assignment-field";
  wrapper.dataset.assignmentTableId = tableId;
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
  wrapper.innerHTML = `
      <div class="assignment-meta">
      <span>桌长 ${escapeHtml(host?.name || hostId || "")}</span>
      <span data-selected-count>已选 ${speakers.size} 人</span>
    </div>
    <select class="agent-select" multiple size="7" data-agent-select="${tableId}">
      ${options}
    </select>
    <div class="agent-prompt-list" data-prompt-list-table="${tableId}"></div>
  `;
  const select = wrapper.querySelector("select");
  select.addEventListener("change", () => {
    speakerAssignments[tableId] = [...select.selectedOptions].map((option) => option.value);
    wrapper.querySelector("[data-selected-count]").textContent =
      `已选 ${speakerAssignments[tableId].length} 人`;
    refreshAgentPromptBoxes(wrapper, tableId);
  });
  // Initial render of prompt boxes for pre-selected agents
  refreshAgentPromptBoxes(wrapper, tableId);
  return wrapper;
}

function refreshAgentPromptBoxes(wrapper, tableId) {
  const container = wrapper.querySelector(`[data-prompt-list-table="${tableId}"]`);
  if (!container) return;
  const selectedIds = new Set(speakerAssignments[tableId] || []);
  // Preserve existing prompt values
  const existingValues = {};
  container.querySelectorAll("textarea[data-agent-prompt-id]").forEach((ta) => {
    existingValues[ta.dataset.agentPromptId] = ta.value;
  });
  container.innerHTML = "";
  if (selectedIds.size === 0) return;
  selectedIds.forEach((agentId) => {
    const agent = availableAgents.find((a) => a.id === agentId);
    const agentName = agent?.name || agentId;
    const box = document.createElement("div");
    box.className = "agent-prompt-box";
    box.innerHTML = `
      <label>${escapeHtml(agentName)} · 提示词</label>
      <textarea
        data-agent-prompt-id="${escapeHtml(agentId)}"
        data-agent-prompt-for="${escapeHtml(agentName)}"
        data-agent-prompt-table="${escapeHtml(tableId)}"
        rows="2"
        placeholder="为 ${escapeHtml(agentName)} 设置额外的 System Prompt（可选）"
      >${escapeHtml(existingValues[agentId] || "")}</textarea>
    `;
    container.append(box);
  });
}

function readSpeakerAssignments() {
  questionEditor.querySelectorAll("[data-agent-select]").forEach((select) => {
    speakerAssignments[select.dataset.agentSelect] = [...select.selectedOptions].map(
      (option) => option.value,
    );
  });
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
          <span class="host-tag">桌长 ${escapeHtml(hostName)}</span>
        </div>
        <div class="table-question">
          <span>${escapeHtml(question)}</span>
        </div>
      </header>
      <div class="seating-chart-container" data-seating-container="${tableId}"></div>
      <div class="round-list" data-round-list></div>
    `;
    tablesGrid.append(table);
    
    // Draw initial seating chart
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
    
    if (i === 0) {
      seat.classList.add("host");
      seat.title = `桌长: ${name}`;
    } else {
      seat.classList.add("speaker");
      seat.title = `发言嘉宾: ${name}`;
    }
    
    if (agentId === activeSpeakerId) {
      seat.classList.add("active-speaker");
      const steam = document.createElement("div");
      steam.className = "steam-vapor";
      steam.innerHTML = "<span></span><span></span><span></span>";
      seat.append(steam);
    }
    
    const seatContent = document.createElement("span");
    seatContent.textContent = initials;
    seat.append(seatContent);
    
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

  const displayRound = Number(roundIndex) + 1;
  const tableQuestion = table.dataset.tableQuestion || "";
  round = document.createElement("div");
  round.className = "round-block";
  round.dataset.roundIndex = roundIndex;
  round.innerHTML = `
    <div class="round-heading">
      <div class="round-question">
        <span>${escapeHtml(tableQuestion)}</span>
      </div>
      <div class="round-meta">
        <span>Round ${displayRound}</span>
        <span>${formatRoundMeta(agentIds)}</span>
      </div>
    </div>
    <div data-host-opening></div>
    <div data-contributions></div>
    <div data-host-record></div>
  `;
  list.append(round);
  return round;
}

function appendHostOpening(metadata) {
  const round = ensureRound(metadata.table_id, metadata.round_index, metadata.agent_ids || []);
  if (!round) return;
  const slot = round.querySelector("[data-host-opening]");
  if (!slot) return;
  slot.innerHTML = renderAgentMessage({
    className: "host-opening",
    agentId: metadata.host_id,
    agentName: metadata.host_name || metadata.host_id,
    roleLabel: "桌长开场",
    metaLabel: formatRoundStatusMeta(metadata),
    content: metadata.content || "",
    memorySnapshot: metadata.memory_snapshot,
    tone: "host",
  });
  scrollTableToBottom(round);
  
  // Highlight host seat on map
  const agents = currentTableAgents[metadata.table_id] || (metadata.agent_ids || [metadata.host_id]);
  drawSeatingChart(null, metadata.table_id, agents, metadata.host_id);
}

function appendContribution(metadata) {
  const round = ensureRound(metadata.table_id, metadata.round_index, []);
  if (!round) return;
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
    ? ` · 总第 ${Number(metadata.turn_index) + 1} 位`
    : "";
  const cycleLabel = Number.isFinite(Number(metadata.cycle_index))
    ? ` · 第 ${Number(metadata.cycle_index) + 1} 次发言`
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
  scrollTableToBottom(round);
  
  // Highlight active speaker seat on map
  const agents = currentTableAgents[metadata.table_id] || [metadata.agent_id];
  drawSeatingChart(null, metadata.table_id, agents, metadata.agent_id);
}

function appendHostRecord(metadata) {
  const round = ensureRound(metadata.table_id, metadata.round_index, []);
  if (!round) return;
  const slot = round.querySelector("[data-host-record]");
  slot.innerHTML = `
    ${renderAgentMessage({
      className: "host-record",
      agentId: metadata.host_id,
      agentName: metadata.host_name || metadata.host_id,
      roleLabel: "桌长记录",
      metaLabel: formatRoundStatusMeta(metadata),
      content: metadata.content || "",
      memorySnapshot: metadata.memory_snapshot,
      tone: "host",
    })}
  `;
  scrollTableToBottom(round);
  
  // Highlight host seat on map
  const agents = currentTableAgents[metadata.table_id] || [metadata.host_id];
  drawSeatingChart(null, metadata.table_id, agents, metadata.host_id);
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
      <button class="message-avatar" type="button" aria-label="${escapeHtml(agentName || agentId)} 的内在记忆" data-avatar-agent-id="${escapeHtml(agentId)}">
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
  const rows = formatMemorySnapshot(snapshot);
  const body = rows.length
    ? rows.map((row) => `<p>${renderInlineMarkdown(escapeHtml(row))}</p>`).join("")
    : "<p>暂无内在记忆记录。</p>";
  return `
    <span class="memory-card" role="tooltip">
      <strong>${escapeHtml(agentName)} · 内在记忆</strong>
      ${body}
    </span>
  `;
}

function formatMemorySnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== "object") return [];
  const rows = [];
  if (snapshot.kind === "table_host") {
    rows.push(`当前桌面记忆：${snapshot.living_summary || "暂无"}`);
    addListRows(rows, "保留洞察", snapshot.key_insights);
    addListRows(rows, "开放问题", snapshot.open_questions);
    addListRows(rows, "张力", snapshot.tensions);
    if (snapshot.cumulative_pattern_evolution) rows.push(`累计演化：${snapshot.cumulative_pattern_evolution}`);
    addListRows(rows, "跨轮重复模式", snapshot.recurring_patterns_across_rounds);
    addListRows(rows, "变化中的信号", snapshot.emerging_or_fading_signals);
    addListRows(rows, "持续未解张力", snapshot.unresolved_tensions_over_time);
    if (snapshot.round_pattern_delta) rows.push(`本轮在累计历史中的变化：${snapshot.round_pattern_delta}`);
    addListRows(rows, "下一轮问题种子", snapshot.next_round_question_seeds);
    (snapshot.recent_rounds || []).forEach((round) => {
      if (round.synthesis) rows.push(`第 ${round.round} 轮汇总：${round.synthesis}`);
      if (round.cumulative_pattern_evolution) rows.push(`第 ${round.round} 轮演化：${round.cumulative_pattern_evolution}`);
    });
    return rows;
  }
  if (snapshot.bridge_intent) rows.push(`迁移意图：${snapshot.bridge_intent}`);
  addObjectRows(rows, "个人迁移记忆", snapshot.agent_generated_memory);
  return rows;
}

function addListRows(rows, label, value) {
  if (!Array.isArray(value) || !value.length) return;
  rows.push(`${label}：${value.join("；")}`);
}

function addObjectRows(rows, label, value) {
  if (!value) return;
  if (typeof value === "string") {
    if (value.trim()) rows.push(`${label}：${value}`);
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
      .join("；");
    if (compact) rows.push(`${label}：${compact}`);
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
      <strong>轮换到 Round ${escapeHtml(nextRound)}</strong>
      <p>${escapeHtml(formatRotatedAssignment(agentIds || []))}</p>
    `;
  });
}

function scrollTableToBottom(round) {
  const list = round.closest(".round-list");
  if (!list) return;
  list.scrollTop = list.scrollHeight;
}

function renderHarvest(markdown) {
  harvestContent.classList.remove("muted");
  harvestContent.innerHTML = renderMarkdownLite(markdown || "No harvest generated.");
}

function resetRunView() {
  traceTotal = 0;
  currentRound = 0;
  maxRounds = 0;
  speechesPerAgent = getSpeechesPerAgent();
  isPaused = false;
  seenEventKeys = new Set();
  notebookEntries = [];
  noteSequence = 0;
  pendingNoteSelection = null;
  pendingNoteCheckpoints = [];
  activeNoteCheckpoint = null;
  pauseBtn.disabled = true;
  pauseBtn.textContent = "暂停标注";
  addNoteBtn.disabled = true;
  hideNoteCheckpointPanel();
  hideQuestionEditorView();
  discussionPane.classList.remove("paused");
  // Clear gated-pulse highlight
  document.querySelectorAll(".table-card").forEach(card => card.classList.remove("gated-pulse"));
  traceCount.textContent = "0 个事件";
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
    status: "空闲",
    detail: "等待记录并维护各桌研讨记忆。",
    meta: "暂无活动桌",
  });
  updateAgentStatus("speaker", {
    status: "空闲",
    detail: "等待参与各桌讨论。",
    meta: "暂无活动发言人",
  });
  updateAgentStatus("rotation", {
    status: "空闲",
    detail: "等待代表在不同研讨桌之间轮换。",
    meta: "暂无路径",
  });
  updateAgentStatus("harvest", {
    status: "空闲",
    detail: "等待提炼跨桌的共性模式与设计机会。",
    meta: "未开始",
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
  const agents = agentIds.length ? formatRotatedAssignment(agentIds) : "等待中";
  return `${agents} · 每人 ${speechesPerAgent} 次`;
}

function formatRotatedAssignment(agentIds) {
  return agentIds
    .map((agentId, index) => {
      const name = getAgentName(agentId);
      return index === 0 ? `桌长留守 ${name}` : name;
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
  return clampNumber(tableCountInput.value, 1, 8, 4);
}

function getSpeakersPerTable() {
  return clampNumber(speakersInput.value, 1, 8, 3);
}

function getRoundCount() {
  return clampNumber(roundsInput.value, 1, 6, 3);
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
  facilitateBtn.textContent = isBusy ? "规划中..." : "✦ 主题规划";
}

function isNoteTakingActive() {
  return isPaused || Boolean(activeNoteCheckpoint);
}

function refreshNoteTakingControls() {
  discussionPane.classList.toggle("paused", isNoteTakingActive());
  pauseBtn.disabled = !activeRun || Boolean(activeNoteCheckpoint);
  pauseBtn.textContent = isPaused ? "继续讨论" : "暂停标注";
  addNoteBtn.disabled = !isNoteTakingActive() || !pendingNoteSelection;
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
    detail: `${checkpoint.table_id} 已暂停：请完成本轮设计洞察/机会笔记，点击“换桌”后桌长才会生成本轮记忆。`,
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
    continueNotesBtn.textContent = "换桌";
  }
}

function renderActiveNoteCheckpoint() {
  if (!activeNoteCheckpoint || !noteCheckpointPanel) return;
  const notes = getNotesForCheckpoint(activeNoteCheckpoint);
  const roundLabel = Number(activeNoteCheckpoint.round_index) + 1;
  const queued = pendingNoteCheckpoints.length ? ` · 另有 ${pendingNoteCheckpoints.length} 桌等待换桌` : "";
  if (noteCheckpointTitle) {
    noteCheckpointTitle.textContent = `${activeNoteCheckpoint.table_id} · Round ${roundLabel} · 换桌前笔记`;
  }
  if (noteCheckpointDetail) {
    noteCheckpointDetail.textContent = `请先完成本桌本轮的设计洞察/机会笔记，点击“换桌”后桌长才会结合笔记生成内在记忆、输出结束语，并进入换桌。将提交 ${notes.length} 条笔记${queued}。`;
  }
  if (continueNotesBtn) {
    continueNotesBtn.textContent = notes.length ? `提交 ${notes.length} 条笔记并换桌` : "无笔记，直接换桌";
  }
}

async function submitActiveNoteCheckpoint() {
  if (!activeRun || !activeNoteCheckpoint) return;
  const checkpoint = activeNoteCheckpoint;
  const notes = getNotesForCheckpoint(checkpoint).map(noteToPayload);
  continueNotesBtn.disabled = true;
  continueNotesBtn.textContent = "换桌中...";
  try {
    await postJson(`/api/runs/${activeRun.run_id}/note-checkpoint/continue`, {
      checkpoint_id: checkpoint.checkpoint_id,
      table_id: checkpoint.table_id,
      round_index: Number(checkpoint.round_index),
      action: "switch_table",
      notes,
    });
    updateAgentStatus("host", {
      status: "生成桌长记忆",
      detail: `${checkpoint.table_id} 桌长正在结合用户标注笔记更新内在记忆，然后输出本轮结束语。`,
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
  return element?.closest(".speech") || null;
}

function addSelectedNote() {
  const selectionInfo = getSelectedDiscussionSelection() || pendingNoteSelection;
  if (!selectionInfo) return;
  const { text, speech, range } = selectionInfo;
  const noteId = `note-${++noteSequence}`;
  const highlighted = highlightSelectionRange(range, noteId);
  notebookEntries = [
    ...notebookEntries,
    {
      id: noteId,
      text,
      speakerName: speech.dataset.speakerName || "Unknown speaker",
      speakerId: speech.dataset.speakerId || "",
      tableId: speech.dataset.tableId || "",
      roundIndex: Number(speech.dataset.roundIndex),
      speechId: speech.id,
      speechTargetId: highlighted?.id || speech.id,
      round: Number(speech.dataset.roundIndex) + 1 || currentRound,
      createdAt: new Date().toLocaleTimeString(),
    },
  ];
  window.getSelection()?.removeAllRanges();
  pendingNoteSelection = null;
  renderNotebook();
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
  backgroundSummary.textContent = "未上传背景材料";
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
  chatLog.append(message);
  chatLog.scrollTop = chatLog.scrollHeight;
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
  "设计机会",
  "新的设计机会",
  "新机会",
  "机会假设",
  "机会线索",
  "潜在机会",
  "机会",
  "design opportunity",
  "opportunity hypothesis",
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
