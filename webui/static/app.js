const state = {
  payload: null,
  matchPayload: null,
  mode: readStoredMode(),
  tab: readStoredTab(),
};

const elements = {
  newGameForm: document.getElementById("new-game-form"),
  aiMatchForm: document.getElementById("ai-match-form"),
  opponent: document.getElementById("opponent"),
  seed: document.getElementById("seed"),
  matchAgentA: document.getElementById("match-agent-a"),
  matchAgentB: document.getElementById("match-agent-b"),
  matchSeed: document.getElementById("match-seed"),
  tabHuman: document.getElementById("tab-human"),
  tabMatch: document.getElementById("tab-match"),
  visibilityControls: document.getElementById("visibility-controls"),
  humanLayout: document.getElementById("human-layout"),
  matchLayout: document.getElementById("match-layout"),
  modeNormal: document.getElementById("mode-normal"),
  modeDebug: document.getElementById("mode-debug"),
  debugBadge: document.getElementById("debug-badge"),
  inspectorEyebrow: document.getElementById("inspector-eyebrow"),
  inspectorTitle: document.getElementById("inspector-title"),
  statusBanner: document.getElementById("status-banner"),
  metrics: document.getElementById("metrics"),
  fireworks: document.getElementById("fireworks"),
  discardPile: document.getElementById("discard-pile"),
  opponentHand: document.getElementById("opponent-hand"),
  hintControls: document.getElementById("hint-controls"),
  humanHand: document.getElementById("human-hand"),
  recommendation: document.getElementById("recommendation"),
  receivedHint: document.getElementById("received-hint"),
  hintScoringSection: document.getElementById("hint-scoring-section"),
  discardScoringSection: document.getElementById("discard-scoring-section"),
  hintScores: document.getElementById("hint-scores"),
  discardScores: document.getElementById("discard-scores"),
  turnLog: document.getElementById("turn-log"),
  matchStatusBanner: document.getElementById("match-status-banner"),
  matchMetrics: document.getElementById("match-metrics"),
  matchFireworks: document.getElementById("match-fireworks"),
  matchDiscardPile: document.getElementById("match-discard-pile"),
  matchAgentAName: document.getElementById("match-agent-a-name"),
  matchAgentAHand: document.getElementById("match-agent-a-hand"),
  matchAgentBName: document.getElementById("match-agent-b-name"),
  matchAgentBHand: document.getElementById("match-agent-b-hand"),
  matchSummary: document.getElementById("match-summary"),
  matchTurnLog: document.getElementById("match-turn-log"),
  metricTemplate: document.getElementById("metric-template"),
};

const intentionLabels = {
  play: "Play",
  discard: "Discard",
  may_discard: "May Discard",
  keep: "Keep",
};

async function requestJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function loadState() {
  const payload = await requestJSON("/api/state");
  applyPayload(payload);
}

async function startNewGame(event) {
  event.preventDefault();
  const payload = await requestJSON("/api/new-game", {
    method: "POST",
    body: JSON.stringify({
      opponent: elements.opponent.value,
      seed: elements.seed.value,
    }),
  });
  applyPayload(payload);
}

async function runAIMatch(event) {
  event.preventDefault();
  const payload = await requestJSON("/api/ai-match", {
    method: "POST",
    body: JSON.stringify({
      agent_a: elements.matchAgentA.value,
      agent_b: elements.matchAgentB.value,
      seed: elements.matchSeed.value,
    }),
  });
  applyMatchPayload(payload);
}

async function sendAction(payload) {
  const nextState = await requestJSON("/api/action", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  applyPayload(nextState);
}

function applyPayload(payload) {
  state.payload = payload;
  if (payload.status) {
    elements.opponent.value = payload.status.opponent;
  }
  render();
}

function applyMatchPayload(payload) {
  state.matchPayload = payload;
  state.tab = "match";
  window.localStorage.setItem("hanabiUiTab", state.tab);
  if (payload.status) {
    elements.matchAgentA.value = payload.status.agent_a;
    elements.matchAgentB.value = payload.status.agent_b;
  }
  render();
}

function render() {
  renderTabChrome();
  if (state.tab === "match") {
    renderAIMatch(state.matchPayload);
    return;
  }
  if (state.payload) {
    renderHumanView(state.payload);
  }
}

function renderTabChrome() {
  const matchTab = state.tab === "match";
  elements.tabHuman.classList.toggle("active", !matchTab);
  elements.tabMatch.classList.toggle("active", matchTab);
  elements.newGameForm.classList.toggle("hidden", matchTab);
  elements.aiMatchForm.classList.toggle("hidden", !matchTab);
  elements.visibilityControls.classList.toggle("hidden", matchTab);
  elements.humanLayout.classList.toggle("hidden", matchTab);
  elements.matchLayout.classList.toggle("hidden", !matchTab);
}

function renderHumanView(payload) {
  renderModeChrome();
  renderStatus(payload);
  renderMetrics(payload);
  renderFireworks(payload);
  renderDiscardPile(payload);
  renderOpponentHand(payload);
  renderHintControls(payload);
  renderHumanHand(payload);
  renderInspector(payload);
  renderLog(payload);
}

function renderAIMatch(payload) {
  if (!payload) {
    renderAIMatchEmpty();
    return;
  }
  renderAIMatchStatus(payload);
  renderAIMatchMetrics(payload);
  renderFireworksInto(elements.matchFireworks, payload.fireworks);
  renderDiscardPileInto(elements.matchDiscardPile, payload.discard_pile);
  elements.matchAgentAName.textContent = `${capitalize(payload.status.agent_a)} Hand`;
  elements.matchAgentBName.textContent = `${capitalize(payload.status.agent_b)} Hand`;
  renderVisibleHand(elements.matchAgentAHand, payload.agent_a_hand, true);
  renderVisibleHand(elements.matchAgentBHand, payload.agent_b_hand, true);
  renderAIMatchSummary(payload);
  renderLogInto(elements.matchTurnLog, payload.log);
}

function renderAIMatchEmpty() {
  elements.matchStatusBanner.textContent = "Run an AI vs AI match to see both agents play the paper-style heuristics to completion.";
  renderMetricsInto(elements.matchMetrics, []);
  renderFireworksInto(elements.matchFireworks, {});
  renderDiscardPileInto(elements.matchDiscardPile, []);
  elements.matchAgentAName.textContent = "Agent A";
  elements.matchAgentBName.textContent = "Agent B";
  elements.matchAgentAHand.innerHTML = `<span class="empty">No match run yet.</span>`;
  elements.matchAgentBHand.innerHTML = `<span class="empty">No match run yet.</span>`;
  elements.matchSummary.innerHTML = `<p>Select two agents and press <strong>Run Match</strong>.</p>`;
  renderLogInto(elements.matchTurnLog, []);
}

function renderModeChrome() {
  const debug = isDebugMode();
  document.body.classList.toggle("mode-debug", debug);
  document.body.classList.toggle("mode-normal", !debug);
  elements.modeNormal.classList.toggle("active", !debug);
  elements.modeDebug.classList.toggle("active", debug);
  elements.debugBadge.classList.toggle("hidden", !debug);
  elements.inspectorEyebrow.textContent = debug ? "Paper Logic" : "Public History";
  elements.inspectorTitle.textContent = debug ? "Heuristic Inspector" : "Action History";
  elements.recommendation.classList.toggle("hidden", !debug);
  elements.receivedHint.classList.toggle("hidden", !debug);
  elements.hintScoringSection.classList.toggle("hidden", !debug);
  elements.discardScoringSection.classList.toggle("hidden", !debug);
}

function renderStatus(payload) {
  const status = payload.status;
  let text = "";
  if (payload.error) {
    text = payload.error;
  } else if (status.game_over) {
    text = `Game over. Final score ${status.score}.`;
  } else if (status.human_turn) {
    text = `Your turn against ${capitalize(status.opponent)}. Choose one legal action type: Play, Discard, or Hint. Score ${status.score}, hints ${status.hints}/${status.max_hints}.`;
  } else {
    text = `${capitalize(status.opponent)} is processing its turn.`;
  }
  elements.statusBanner.textContent = text;
}

function renderAIMatchStatus(payload) {
  if (payload.error) {
    elements.matchStatusBanner.textContent = payload.error;
    return;
  }
  const status = payload.status;
  elements.matchStatusBanner.textContent = `${capitalize(status.agent_a)} and ${capitalize(status.agent_b)} completed an AI-vs-AI match. Final score ${status.score}.`;
}

function renderMetrics(payload) {
  const metrics = [
    ["Score", payload.status.score],
    ["Hints", `${payload.status.hints}/${payload.status.max_hints}`],
    ["Mistakes", `${payload.status.mistakes}/${payload.status.max_mistakes}`],
    ["Deck", payload.status.deck_size],
    ["Turn", payload.status.turn_number],
    ["Opponent", capitalize(payload.status.opponent)],
  ];
  renderMetricsInto(elements.metrics, metrics);
}

function renderAIMatchMetrics(payload) {
  const metrics = [
    ["Score", payload.status.score],
    ["Hints", `${payload.status.hints}/${payload.status.max_hints}`],
    ["Mistakes", `${payload.status.mistakes}/${payload.status.max_mistakes}`],
    ["Deck", payload.status.deck_size],
    ["Turns", payload.summary.turns_played],
    ["Match", `${capitalize(payload.status.agent_a)} vs ${capitalize(payload.status.agent_b)}`],
  ];
  renderMetricsInto(elements.matchMetrics, metrics);
}

function renderMetricsInto(container, metrics) {
  container.innerHTML = "";
  metrics.forEach(([label, value]) => {
    const node = elements.metricTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".metric-label").textContent = label;
    node.querySelector(".metric-value").textContent = value;
    container.appendChild(node);
  });
}

function renderFireworks(payload) {
  renderFireworksInto(elements.fireworks, payload.fireworks);
}

function renderFireworksInto(container, fireworks) {
  container.innerHTML = "";
  Object.entries(fireworks).forEach(([color, rank]) => {
    const badge = document.createElement("div");
    badge.className = `firework-badge color-${color}`;
    badge.innerHTML = `<span>${capitalize(color)}</span><strong>${rank}</strong>`;
    container.appendChild(badge);
  });
}

function renderDiscardPile(payload) {
  renderDiscardPileInto(elements.discardPile, payload.discard_pile);
}

function renderDiscardPileInto(container, discardPile) {
  container.innerHTML = "";
  if (!discardPile.length) {
    container.innerHTML = `<span class="empty">No discarded cards yet.</span>`;
    return;
  }
  discardPile.forEach((item) => {
    const badge = document.createElement("div");
    badge.className = "token-badge";
    badge.innerHTML = `<span>${item.short}</span><strong>x${item.count}</strong>`;
    container.appendChild(badge);
  });
}

function renderOpponentHand(payload) {
  renderVisibleHand(elements.opponentHand, payload.opponent_hand, isDebugMode());
}

function renderVisibleHand(container, hand, showIntentions) {
  container.innerHTML = "";
  hand.forEach((card, index) => {
    const article = document.createElement("article");
    article.className = `opponent-card color-${card.color}`;
    article.style.animationDelay = `${index * 40}ms`;
    article.innerHTML = `
      <div class="slot-label">Slot ${card.slot + 1}</div>
      <div class="card-main">${card.short}</div>
      <div class="card-sub">${capitalize(card.color)} ${card.rank}</div>
      ${showIntentions && card.intention ? `<div class="card-meta"><span class="chip">${intentionLabels[card.intention]}</span></div>` : ""}
    `;
    container.appendChild(article);
  });
}

function renderHintControls(payload) {
  const disabled = !payload.status.human_turn;
  const hintColors = payload.controls.hint_colors;
  const hintRanks = payload.controls.hint_ranks;
  elements.hintControls.innerHTML = `
    <div class="subsection-head">
      <h3>Give a Hint</h3>
      <span class="inline-note">${disabled ? "Wait for your turn." : "Hints apply to every matching card."}</span>
    </div>
    <div class="hint-actions color-actions"></div>
    <div class="hint-actions rank-actions"></div>
  `;

  const colorActions = elements.hintControls.querySelector(".color-actions");
  const rankActions = elements.hintControls.querySelector(".rank-actions");

  hintColors.forEach((color) => {
    const button = document.createElement("button");
    button.className = "secondary-button";
    button.disabled = disabled;
    button.textContent = capitalize(color);
    button.addEventListener("click", () => sendAction({
      kind: "hint",
      target_player: 1,
      hint_kind: "color",
      hint_value: color,
    }));
    colorActions.appendChild(button);
  });

  hintRanks.forEach((rank) => {
    const button = document.createElement("button");
    button.disabled = disabled;
    button.textContent = `Rank ${rank}`;
    button.addEventListener("click", () => sendAction({
      kind: "hint",
      target_player: 1,
      hint_kind: "rank",
      hint_value: rank,
    }));
    rankActions.appendChild(button);
  });

  if (!hintColors.length && !hintRanks.length) {
    elements.hintControls.innerHTML += `<div class="empty">No legal hints available.</div>`;
  }
}

function renderHumanHand(payload) {
  elements.humanHand.innerHTML = "";
  const debug = isDebugMode();
  payload.human_hand.forEach((card, index) => {
    const article = document.createElement("article");
    article.className = "human-card";
    article.style.animationDelay = `${index * 50}ms`;
    article.innerHTML = debug
      ? renderDebugHiddenHandCard(card, payload)
      : renderPublicHiddenHandCard(card, payload);
    article.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => sendAction({
        kind: button.dataset.action,
        card_index: Number(button.dataset.slot),
      }));
    });
    elements.humanHand.appendChild(article);
  });
}

function renderInspector(payload) {
  if (!isDebugMode()) {
    elements.recommendation.innerHTML = "";
    elements.receivedHint.innerHTML = "";
    elements.receivedHint.classList.add("hidden");
    elements.hintScores.innerHTML = "";
    elements.discardScores.innerHTML = "";
    return;
  }

  const recommendation = payload.heuristics.recommendation;
  const bestHint = payload.heuristics.best_hint;
  elements.recommendation.innerHTML = `
    <div class="subsection-head">
      <h3>Intentional Recommendation</h3>
      <span class="inline-note">Shared with the agent code</span>
    </div>
    <p><strong>${recommendation.label}</strong></p>
    ${bestHint ? `<p>Best hint: <strong>${bestHint.label}</strong> with score <strong>${bestHint.score}</strong>.</p>` : `<p>No positive intentional hint is available right now.</p>`}
  `;

  if (payload.pending_received_hint) {
    const hint = payload.pending_received_hint;
    elements.receivedHint.classList.remove("hidden");
    elements.receivedHint.innerHTML = `
      <div class="subsection-head">
        <h3>Latest Received Hint</h3>
      </div>
      <p>${capitalize(hint.kind)} ${hint.value} on slots ${hint.positive_slots.map((slot) => slot + 1).join(", ")}.</p>
    `;
  } else {
    elements.receivedHint.classList.add("hidden");
    elements.receivedHint.innerHTML = "";
  }

  elements.hintScores.innerHTML = "";
  payload.heuristics.hint_assessments.forEach((item) => {
    const row = document.createElement("div");
    row.className = `score-item ${item.valid ? "" : "invalid"}`;
    row.innerHTML = `
      <span>${item.label}</span>
      <strong>${item.valid ? `score ${item.score}` : "blocked"}</strong>
    `;
    elements.hintScores.appendChild(row);
  });

  elements.discardScores.innerHTML = "";
  payload.heuristics.discard_scores.forEach((item) => {
    const row = document.createElement("div");
    row.className = "score-item";
    row.innerHTML = `
      <span>Slot ${item.slot + 1}</span>
      <strong>${Number(item.score).toFixed(2)}</strong>
    `;
    elements.discardScores.appendChild(row);
  });
}

function renderAIMatchSummary(payload) {
  if (payload.error) {
    elements.matchSummary.innerHTML = `<p>${payload.error}</p>`;
    return;
  }
  elements.matchSummary.innerHTML = `
    <div class="subsection-head">
      <h3>${payload.summary.label}</h3>
      <span class="inline-note">Paper-style AI self-play</span>
    </div>
    <p>Final score: <strong>${payload.summary.final_score}</strong></p>
    <p>Turns played: <strong>${payload.summary.turns_played}</strong></p>
  `;
}

function renderLog(payload) {
  renderLogInto(elements.turnLog, payload.log);
}

function renderLogInto(container, logEntries) {
  container.innerHTML = "";
  if (!logEntries.length) {
    container.innerHTML = `<div class="empty">No actions yet. Start playing.</div>`;
    return;
  }
  logEntries.forEach((entry) => {
    const article = document.createElement("article");
    article.className = "log-entry";
    article.innerHTML = `
      <div class="log-entry-head">
        <strong>${entry.headline || "Turn"}</strong>
        <span class="log-badge log-badge-${entry.kind}">${entry.action_label || String(entry.kind || "").toUpperCase()}</span>
      </div>
      <div class="log-entry-body">${entry.detail || entry.text}</div>
    `;
    container.appendChild(article);
  });
  container.scrollTop = container.scrollHeight;
}

function renderDebugHiddenHandCard(card, payload) {
  return `
    <div class="slot-label">Slot ${card.slot + 1}</div>
    ${renderCheatCardFace(card)}
    ${renderCardActionButtons(card.slot, payload)}
  `;
}

function renderPublicHiddenHandCard(card, payload) {
  return `
    <div class="slot-label">Slot ${card.slot + 1}</div>
    ${renderHiddenCardFace()}
    <div class="card-main">Hidden Card</div>
    <div class="card-sub">Only legal hint information is shown in Normal mode.</div>
    <div class="public-knowledge">
      ${renderPublicHintKnowledge(card.hint_knowledge)}
    </div>
    ${renderCardActionButtons(card.slot, payload)}
  `;
}

function renderCheatCardFace(card) {
  if (!card.actual_short) {
    return "";
  }
  return `
    <div class="revealed-card-face color-${card.actual_color}">
      <div class="revealed-card-short">${card.actual_short}</div>
      <div class="revealed-card-sub">${capitalize(card.actual_color)} ${card.actual_rank}</div>
    </div>
  `;
}

function renderHiddenCardFace() {
  return `
    <div class="hidden-card-face">
      <div class="hidden-card-glyph">?</div>
      <div class="hidden-card-sub">Card back</div>
    </div>
  `;
}

function renderCardActionButtons(slot, payload) {
  const canPlay = payload.status.human_turn && isCardActionLegal(payload, "play", slot);
  const canDiscard = payload.status.human_turn && isCardActionLegal(payload, "discard", slot);
  return `
    <div class="card-actions">
      <button class="secondary-button" ${canPlay ? "" : "disabled"} data-action="play" data-slot="${slot}">Play</button>
      <button class="muted-button" ${canDiscard ? "" : "disabled"} data-action="discard" data-slot="${slot}">Discard</button>
    </div>
  `;
}

function isCardActionLegal(payload, kind, slot) {
  return payload.controls.legal_actions.some((action) => action.kind === kind && action.card_index === slot);
}

function renderPublicHintKnowledge(hintKnowledge) {
  const colors = hintKnowledge.allowed_colors;
  const ranks = hintKnowledge.allowed_ranks;

  const colorLine = formatHintKnowledgeLine("Color", colors, ["green", "yellow", "white", "blue", "red"]);
  const rankLine = formatHintKnowledgeLine("Rank", ranks, [1, 2, 3, 4, 5]);

  if (!colorLine && !rankLine) {
    return `<div class="knowledge-line"><strong>No direct hints yet.</strong></div>`;
  }

  return [colorLine, rankLine].filter(Boolean).join("");
}

function formatHintKnowledgeLine(label, allowedValues, universe) {
  if (!allowedValues.length || allowedValues.length === universe.length) {
    return "";
  }
  if (allowedValues.length === 1) {
    return `<div class="knowledge-line"><strong>${label} hint:</strong> ${capitalize(String(allowedValues[0]))}</div>`;
  }
  const blocked = universe.filter((value) => !allowedValues.includes(value));
  if (!blocked.length) {
    return "";
  }
  return `<div class="knowledge-line"><strong>Not ${label.toLowerCase()}:</strong> ${blocked.map((value) => capitalize(String(value))).join(", ")}</div>`;
}

function capitalize(value) {
  if (!value) {
    return "";
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function isDebugMode() {
  return state.mode === "debug";
}

function setMode(mode) {
  state.mode = mode === "debug" ? "debug" : "normal";
  window.localStorage.setItem("hanabiViewMode", state.mode);
  render();
}

function readStoredMode() {
  const stored = window.localStorage.getItem("hanabiViewMode");
  return stored === "debug" ? "debug" : "normal";
}

function setTab(tab) {
  state.tab = tab === "match" ? "match" : "human";
  window.localStorage.setItem("hanabiUiTab", state.tab);
  render();
}

function readStoredTab() {
  const stored = window.localStorage.getItem("hanabiUiTab");
  return stored === "match" ? "match" : "human";
}

elements.newGameForm.addEventListener("submit", (event) => {
  startNewGame(event).catch(handleError);
});

elements.aiMatchForm.addEventListener("submit", (event) => {
  runAIMatch(event).catch(handleError);
});

elements.tabHuman.addEventListener("click", () => setTab("human"));
elements.tabMatch.addEventListener("click", () => setTab("match"));
elements.modeNormal.addEventListener("click", () => setMode("normal"));
elements.modeDebug.addEventListener("click", () => setMode("debug"));

render();
loadState().catch(handleError);

function handleError(error) {
  console.error(error);
  if (state.tab === "match") {
    elements.matchStatusBanner.textContent = `Error: ${error.message}`;
  } else {
    elements.statusBanner.textContent = `Error: ${error.message}`;
  }
}
