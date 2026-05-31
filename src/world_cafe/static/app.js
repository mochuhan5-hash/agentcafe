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
const discussionPane = document.querySelector(".discussion-pane");
const backgroundFileInput = document.querySelector("#backgroundFile");
const backgroundSummary = document.querySelector("#backgroundSummary");
const clearBackgroundBtn = document.querySelector("#clearBackgroundBtn");

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
let availableAgents = [];
let hostAssignments = {};
let speakerAssignments = {};
let backgroundContext = "";
let backgroundFilename = "";

const phaseOrder = ["facilitate", "setup", "round_started", "rotation", "harvest", "done"];

init();

tableCountInput.addEventListener("change", async () => {
  await loadAgentsForSettings();
  facilitatedTables = [];
  questionEditor.hidden = true;
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

document.addEventListener("selectionchange", () => {
  pendingNoteSelection = getSelectedDiscussionSelection();
  addNoteBtn.disabled = !isPaused || !pendingNoteSelection;
});

async function init() {
  try {
    const config = await getJson("/api/config");
    modelBadge.textContent = `${config.model} · ${config.base_url}`;
    tableCountInput.value = config.default_table_count || 4;
    speakersInput.value = config.default_speakers_per_table || 3;
    roundsInput.value = config.default_rounds || 3;
    speechesInput.value = config.default_speeches_per_agent || 3;
    speechesPerAgent = getSpeechesPerAgent();
    if (!config.token_configured) {
      modelBadge.textContent += " · token missing";
    }
  } catch {
    modelBadge.textContent = "config unavailable";
  }

  addMessage("facilitator", "World Cafe is ready.");
  await loadAgentsForSettings();
}

requestForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const request = requestInput.value.trim();
  if (!request) return;

  addMessage("user", request);
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
    addMessage("facilitator", `${result.facilitation_note}\n\n${formatQuestions(facilitatedTables)}`);
    await loadAgentsForSettings();
    renderQuestionEditor(facilitatedTables);
    startBtn.disabled = false;
  } catch (error) {
    addMessage("error", error.message);
  } finally {
    setBusy(false);
  }
});

startBtn.addEventListener("click", async () => {
  const tables = readEditedQuestions();
  if (tables.length !== getTableCount()) return;

  resetRunView();
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
    return;
  }
  if (event.type === "pause_changed") {
    if (event.status === "pause_requested") {
      setStatus("Pausing after current speaker", "running");
    } else if (event.status === "paused") {
      setStatus("Paused for notes", "running");
    } else if (event.status === "running") {
      setStatus("Running", "running");
    }
    return;
  }
  if (event.type === "error") {
    setStatus("Error", "error");
    addMessage("error", event.message || "运行出错，但后端没有返回详细错误。");
    return;
  }
  if (event.type === "run_complete") {
    setStatus("Done", "");
    setPhase("done");
    renderHarvest(event.harvest?.content || "");
    addMessage("facilitator", "Harvest completed.");
    facilitateBtn.disabled = false;
    pauseBtn.disabled = true;
    pauseBtn.textContent = "暂停标注";
    isPaused = false;
    discussionPane.classList.remove("paused");
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
    Object.entries(metadata.assignments || {}).forEach(([tableId, agentIds]) => {
      ensureRound(tableId, metadata.round_index || 0, agentIds);
    });
  }

  if (event.stage === "table_discussion") {
    ensureRound(metadata.table_id, metadata.round_index || 0, metadata.agent_ids || []);
  }

  if (event.stage === "agent_contribution") {
    appendContribution(metadata);
  }

  if (event.stage === "host_record") {
    appendHostRecord(metadata);
  }

  if (event.stage === "rotation") {
    setStatus(`Rotating to round ${(metadata.next_round_index || 0) + 1}`, "running");
  }

  if (event.stage === "harvest") {
    setStatus("Harvesting", "running");
  }
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

function renderQuestionEditor(tables) {
  questionEditor.hidden = false;
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
  return [...questionEditor.querySelectorAll("textarea")].map((textarea) => ({
    table_id: textarea.dataset.tableId,
    question: textarea.value.trim(),
  }));
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
      <span data-selected-count>${speakers.size} selected</span>
    </div>
    <select class="agent-select" multiple size="7" data-agent-select="${tableId}">
      ${options}
    </select>
  `;
  const select = wrapper.querySelector("select");
  select.addEventListener("change", () => {
    speakerAssignments[tableId] = [...select.selectedOptions].map((option) => option.value);
    wrapper.querySelector("[data-selected-count]").textContent =
      `${speakerAssignments[tableId].length} selected`;
  });
  return wrapper;
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
    const table = document.createElement("section");
    table.className = "table-card";
    table.dataset.tableId = tableId;
    table.innerHTML = `
      <header>
        <div class="table-title">
          <h3>${tableId.replace("_", " ").toUpperCase()}</h3>
          <span class="host-tag">桌长 ${escapeHtml(hostName)}</span>
        </div>
        <p class="table-question">${escapeHtml(question)}</p>
      </header>
      <div class="round-list" data-round-list></div>
    `;
    tablesGrid.append(table);
  });
}

function ensureRound(tableId, roundIndex, agentIds = []) {
  if (!tableId) return null;
  const table = tablesGrid.querySelector(`[data-table-id="${tableId}"]`);
  if (!table) return null;
  const list = table.querySelector("[data-round-list]");
  let round = list.querySelector(`[data-round-index="${roundIndex}"]`);
  if (round) return round;

  const displayRound = Number(roundIndex) + 1;
  round = document.createElement("div");
  round.className = "round-block";
  round.dataset.roundIndex = roundIndex;
  round.innerHTML = `
    <div class="round-heading">
      <span>Round ${displayRound}</span>
      <span>${formatRoundMeta(agentIds)}</span>
    </div>
    <div data-contributions></div>
    <div data-host-record></div>
  `;
  list.append(round);
  return round;
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
  const turnLabel = Number.isFinite(Number(metadata.turn_index))
    ? ` · turn ${Number(metadata.turn_index) + 1}`
    : "";
  const cycleLabel = Number.isFinite(Number(metadata.cycle_index))
    ? ` · cycle ${Number(metadata.cycle_index) + 1}`
    : "";
  speech.innerHTML = `
    <strong>${escapeHtml(metadata.agent_name || metadata.agent_id)}${escapeHtml(cycleLabel)}${escapeHtml(turnLabel)}</strong>
    <div class="markdown-lite">${renderMarkdownLite(metadata.content || "")}</div>
  `;
  list.append(speech);
  scrollTableToBottom(round);
}

function appendHostRecord(metadata) {
  const round = ensureRound(metadata.table_id, metadata.round_index, []);
  if (!round) return;
  const slot = round.querySelector("[data-host-record]");
  slot.innerHTML = `
    <div class="host-record">
      <strong>桌长记录 · ${escapeHtml(metadata.host_name || metadata.host_id)}</strong>
      <div class="markdown-lite">${renderMarkdownLite(metadata.content || "")}</div>
    </div>
  `;
  scrollTableToBottom(round);
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
  pauseBtn.disabled = true;
  pauseBtn.textContent = "暂停标注";
  addNoteBtn.disabled = true;
  discussionPane.classList.remove("paused");
  traceCount.textContent = "0 events";
  harvestContent.classList.add("muted");
  harvestContent.textContent = "等待讨论完成";
  tablesGrid.innerHTML = "";
  renderNotebook();
  phaseTrack.querySelectorAll("span").forEach((item) => {
    item.classList.remove("active", "done");
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
  const agents = agentIds.length ? agentIds.join(" · ") : "pending";
  return `${agents} · 每人 ${speechesPerAgent} 次`;
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
  facilitateBtn.textContent = isBusy ? "Facilitating..." : "✦ Facilitate";
}

async function togglePause() {
  if (!activeRun) return;
  pauseBtn.disabled = true;
  try {
    if (!isPaused) {
      await postJson(`/api/runs/${activeRun.run_id}/pause`, {});
      isPaused = true;
      discussionPane.classList.add("paused");
      pauseBtn.textContent = "继续讨论";
      addNoteBtn.disabled = !getSelectedDiscussionText();
      setStatus("Pausing after current speaker", "running");
      return;
    }
    await postJson(`/api/runs/${activeRun.run_id}/resume`, {});
    isPaused = false;
    discussionPane.classList.remove("paused");
    pauseBtn.textContent = "暂停标注";
    addNoteBtn.disabled = true;
    setStatus("Running", "running");
    if (!eventSource || eventSource.readyState === EventSource.CLOSED) {
      subscribeToRun(activeRun.run_id);
    }
  } catch (error) {
    addMessage("error", error.message);
  } finally {
    pauseBtn.disabled = false;
  }
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
      speechId: speech.id,
      speechTargetId: highlighted?.id || speech.id,
      round: currentRound,
      createdAt: new Date().toLocaleTimeString(),
    },
  ];
  window.getSelection()?.removeAllRanges();
  pendingNoteSelection = null;
  renderNotebook();
  addNoteBtn.disabled = true;
}

function renderNotebook() {
  notebookCount.textContent = `${notebookEntries.length} notes`;
  notebookList.innerHTML = "";
  notebookEntries.forEach((entry, index) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "notebook-entry";
    item.dataset.noteTarget = entry.id;
    item.innerHTML = `
      <div class="notebook-entry-meta">#${index + 1} · ${escapeHtml(entry.speakerName)} · Round ${entry.round || "?"} · ${escapeHtml(entry.createdAt)}</div>
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
  message.textContent = content;
  chatLog.append(message);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function formatQuestions(tables) {
  return tables.map((table) => `${table.table_id}: ${table.question}`).join("\n");
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
  const lines = escapeHtml(markdown).split(/\r?\n/);
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
      html.push(`<h3>${line.slice(4)}</h3>`);
      return;
    }
    if (line.startsWith("## ")) {
      closeList();
      html.push(`<h2>${line.slice(3)}</h2>`);
      return;
    }
    if (line.startsWith("- ")) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${line.slice(2)}</li>`);
      return;
    }
    if (!line.trim()) {
      closeList();
      html.push("<br />");
      return;
    }
    closeList();
    html.push(`<p>${line}</p>`);
  });

  closeList();
  return html.join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
