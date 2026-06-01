const HISTORY_PAGE_SIZE = 6;
const VALID_TASK_STATUSES = new Set(["todo", "in_progress", "done"]);
const STATUS_MESSAGE_SECONDS = 5;

let localRecords = [];
let visibleHistoryCount = HISTORY_PAGE_SIZE;
let activeRecordId = null;
let messageCountdownTimer = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function showMessage(text, type) {
  const message = document.getElementById("message");
  clearMessageTimer();
  let secondsRemaining = STATUS_MESSAGE_SECONDS;
  message.textContent = text;
  message.className = `status ${type}`;
  messageCountdownTimer = window.setInterval(() => {
    secondsRemaining -= 1;
    if (secondsRemaining <= 0) {
      clearMessage();
      return;
    }
  }, 1000);
}

function clearMessage() {
  clearMessageTimer();
  const message = document.getElementById("message");
  message.textContent = "";
  message.className = "status hidden";
}

function clearMessageTimer() {
  if (messageCountdownTimer !== null) {
    window.clearInterval(messageCountdownTimer);
    messageCountdownTimer = null;
  }
}

function setButtonLoading(button, loadingText, isLoading) {
  if (!button) {
    return;
  }

  if (!button.dataset.defaultLabel) {
    button.dataset.defaultLabel = button.textContent;
  }

  button.disabled = isLoading;
  button.classList.toggle("is-loading", isLoading);
  button.textContent = isLoading ? loadingText : button.dataset.defaultLabel;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  return { response, data };
}

function getRecordSortTime(record) {
  return String(record?.updated_at || record?.created_at || "");
}

function sortRecordsNewestFirst(records) {
  return [...records].sort((left, right) => {
    const leftTime = getRecordSortTime(left);
    const rightTime = getRecordSortTime(right);
    return rightTime.localeCompare(leftTime);
  });
}

function setLocalRecords(records) {
  localRecords = sortRecordsNewestFirst(Array.isArray(records) ? records : []);
  window.STUDY_PLAN_RECORDS = [...localRecords];
}

function upsertLocalRecord(record) {
  const recordId = String(record?.id || "").trim();
  if (!recordId) {
    return;
  }

  const nextRecords = localRecords.filter((item) => String(item?.id || "") !== recordId);
  nextRecords.push(record);
  setLocalRecords(nextRecords);
}

function removeLocalRecord(recordId) {
  const targetId = String(recordId || "").trim();
  setLocalRecords(localRecords.filter((item) => String(item?.id || "") !== targetId));
}

function getLatestLocalRecord() {
  return localRecords.length > 0 ? localRecords[0] : null;
}

function findRecordById(recordId) {
  const targetId = String(recordId || "").trim();
  if (!targetId) {
    return null;
  }
  return localRecords.find((record) => String(record?.id || "") === targetId) || null;
}

function getPlanStrategy(plan) {
  return String(plan?.strategy || plan?.planning_strategy || "");
}

function buildFallbackShortText(text, maxWords = 8, maxChars = 60) {
  const normalized = String(text || "")
    .replace(/\s+/g, " ")
    .replace(/^[\s,.;:-]+|[\s,.;:-]+$/g, "")
    .trim();

  if (!normalized) {
    return "";
  }

  const words = normalized.split(" ");
  const chosen = [];
  for (const word of words) {
    const candidate = [...chosen, word].join(" ");
    if (chosen.length >= maxWords || candidate.length > maxChars) {
      break;
    }
    chosen.push(word);
  }

  const shortText = chosen.join(" ").trim();
  return shortText || normalized.slice(0, maxChars).trim();
}

function getPlanTitle(record) {
  const plan = record?.plan || {};
  const explicitTitle = String(plan.short_title || plan.title || "").trim();
  if (explicitTitle) {
    return explicitTitle;
  }

  const topic = String(record?.perceived_state?.topic || "").trim();
  if (topic) {
    return buildFallbackShortText(topic, 6, 40);
  }

  return buildFallbackShortText(record?.goal || "Study Plan", 8, 50) || "Study Plan";
}

function getStudyNotes(plan) {
  if (Array.isArray(plan?.study_notes)) {
    return plan.study_notes;
  }
  if (Array.isArray(plan?.tips)) {
    return plan.tips;
  }
  return [];
}

function getDailyTasks(plan) {
  return Array.isArray(plan?.daily_tasks) ? plan.daily_tasks : [];
}

function getTaskDayNumber(day, index) {
  return day?.day ?? day?.day_number ?? index + 1;
}

function getTaskFocus(day) {
  if ("day_number" in (day || {}) || "title" in (day || {})) {
    return String(day?.title || day?.focus || "");
  }
  return String(day?.focus || "");
}

function getTaskObjective(day) {
  if ("day_number" in (day || {}) || "title" in (day || {})) {
    return String(day?.focus || day?.objective || "");
  }
  return String(day?.objective || "");
}

function getTaskText(task) {
  if (typeof task === "string") {
    return task;
  }
  return String(task?.text || task?.task || "");
}

function getTaskStatus(task) {
  const status = typeof task === "string" ? "todo" : String(task?.status || "todo");
  return VALID_TASK_STATUSES.has(status) ? status : "todo";
}

function getTaskBadgeClass(status) {
  if (status === "done") {
    return "task-status-badge status-done";
  }
  if (status === "in_progress") {
    return "task-status-badge status-in-progress";
  }
  return "task-status-badge status-todo";
}

function getTaskStatusLabel(status) {
  if (status === "done") {
    return "Done";
  }
  if (status === "in_progress") {
    return "In Progress";
  }
  return "To Do";
}

function calculateProgress(record) {
  const days = getDailyTasks(record?.plan || {});
  let total = 0;
  let done = 0;

  for (const day of days) {
    const tasks = Array.isArray(day?.tasks) ? day.tasks : [];
    for (const task of tasks) {
      total += 1;
      if (getTaskStatus(task) === "done") {
        done += 1;
      }
    }
  }

  return {
    done,
    total,
    percentage: total > 0 ? Math.round((done / total) * 100) : 0,
  };
}

function renderProgressBar(record, compact = false) {
  const progress = calculateProgress(record);
  const compactClass = compact ? " progress-stack-compact" : "";
  return `
    <div class="progress-stack${compactClass}">
      <div class="progress-meta">
        <span>Progress</span>
        <strong>${progress.done} / ${progress.total} tasks completed</strong>
      </div>
      <div class="progress-bar" aria-label="Progress ${progress.percentage}%">
        <span style="width: ${progress.percentage}%;"></span>
      </div>
    </div>
  `;
}

function renderList(items, emptyText) {
  if (!Array.isArray(items) || items.length === 0) {
    return `<p class="muted">${escapeHtml(emptyText)}</p>`;
  }

  return `
    <ul class="bullet-list spacious-list">
      ${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
    </ul>
  `;
}

function renderTaskStatusControls(recordId, task) {
  const taskId = String(task?.id || "");
  const currentStatus = getTaskStatus(task);
  const options = [
    { value: "todo", label: "To Do" },
    { value: "in_progress", label: "In Progress" },
    { value: "done", label: "Done" },
  ];

  return `
    <div class="task-controls" role="group" aria-label="Update task status">
      ${options.map((option) => `
        <button
          type="button"
          class="task-status-button ${currentStatus === option.value ? "is-active" : ""}"
          data-task-action="status"
          data-record-id="${escapeHtml(recordId)}"
          data-task-id="${escapeHtml(taskId)}"
          data-status="${escapeHtml(option.value)}"
        >
          ${escapeHtml(option.label)}
        </button>
      `).join("")}
    </div>
  `;
}

function renderTaskRows(recordId, tasks) {
  if (!Array.isArray(tasks) || tasks.length === 0) {
    return '<p class="muted">No tasks recorded.</p>';
  }

  return `
    <div class="task-list">
      ${tasks.map((task) => {
        const normalizedTask = typeof task === "string"
          ? { id: "", text: task, status: "todo" }
          : task;
        const status = getTaskStatus(normalizedTask);
        return `
          <article class="task-item ${status === "done" ? "is-done" : ""}">
            <div class="task-main">
              <div class="task-copy">
                <p class="task-text">${escapeHtml(getTaskText(normalizedTask))}</p>
              </div>
              <span class="${getTaskBadgeClass(status)}">${escapeHtml(getTaskStatusLabel(status))}</span>
            </div>
            ${renderTaskStatusControls(recordId, normalizedTask)}
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function renderTaskPreview(day) {
  const tasks = Array.isArray(day?.tasks) ? day.tasks : [];
  if (tasks.length === 0) {
    return '<p class="muted">No tasks recorded.</p>';
  }

  return `
    <ul class="bullet-list spacious-list">
      ${tasks.map((task) => `<li>${escapeHtml(getTaskText(task))}</li>`).join("")}
    </ul>
  `;
}

function renderEmptyPlanState() {
  return '<div class="empty-state">No plan yet. Create a study plan to begin.</div>';
}

function renderPlan(record) {
  const container = document.getElementById("latest-plan");
  if (!record) {
    container.innerHTML = renderEmptyPlanState();
    return;
  }

  const plan = record.plan || {};
  const state = record.perceived_state || {};
  const feedbackSection = record.latest_feedback ? `
    <section class="detail-panel detail-panel-wide feedback-note">
      <h4>Latest feedback</h4>
      <p>${escapeHtml(record.latest_feedback)}</p>
    </section>
  ` : "";

  container.innerHTML = `
    <article class="plan-shell">
      <div class="plan-hero">
        <div class="plan-hero-copy">
          <p class="section-label">Current Plan</p>
          <h3 class="plan-title">${escapeHtml(getPlanTitle(record))}</h3>
          <p class="plan-summary">${escapeHtml(record.goal || "")}</p>
        </div>
        <div class="plan-hero-meta">
          <div class="plan-badge-row">
            <span class="task-badge">${escapeHtml(state.task_type || "study plan")}</span>
          </div>
          <p class="timestamp-note">Created: ${escapeHtml(record.created_at || "")}</p>
          <p class="timestamp-note">Last updated: ${escapeHtml(record.updated_at || record.created_at || "")}</p>
          <div class="plan-hero-actions">
            <button class="secondary-button" type="button" data-record-id="${escapeHtml(record.id || "")}">
              View / Edit
            </button>
            <button
              class="danger-button"
              type="button"
              data-modal-action="delete-plan"
              data-record-id="${escapeHtml(record.id || "")}"
            >
              Delete
            </button>
          </div>
        </div>
      </div>

      ${renderProgressBar(record)}

      <div class="summary-grid">
        <article class="summary-tile">
          <span class="meta-label">Topic</span>
          <strong>${escapeHtml(state.topic || "")}</strong>
        </article>
        <article class="summary-tile">
          <span class="meta-label">Days</span>
          <strong>${escapeHtml(state.days || "")}</strong>
        </article>
        <article class="summary-tile">
          <span class="meta-label">Difficulty</span>
          <strong>${escapeHtml(state.difficulty || "")}</strong>
        </article>
        <article class="summary-tile">
          <span class="meta-label">Task Type</span>
          <strong>${escapeHtml(state.task_type || "")}</strong>
        </article>
      </div>

      <div class="plan-detail-grid">
        <section class="detail-panel detail-panel-wide">
          <h4>Summary</h4>
          <p>${escapeHtml(plan.summary || "")}</p>
        </section>

        <section class="detail-panel detail-panel-wide">
          <h4>Strategy</h4>
          <p>${escapeHtml(getPlanStrategy(plan))}</p>
        </section>

        <section class="detail-panel">
          <h4>Priority list</h4>
          ${renderList(plan.priority_list, "No priorities recorded.")}
        </section>

        <section class="detail-panel">
          <h4>Study notes</h4>
          ${renderList(getStudyNotes(plan), "No study notes recorded.")}
        </section>

        <section class="detail-panel risk-panel detail-panel-wide">
          <h4>Risk warning</h4>
          <p>${escapeHtml(plan.risk_warning || "")}</p>
        </section>

        ${feedbackSection}
      </div>

      <section class="tasks-section">
        <div class="tasks-section-head">
          <div>
            <p class="section-label">Daily schedule</p>
            <h4>Daily tasks</h4>
          </div>
        </div>
        <div class="days-grid">
          ${getDailyTasks(plan).map((day, index) => `
            <article class="day-card">
              <span class="day-label">Day ${escapeHtml(getTaskDayNumber(day, index))}</span>
              <h5 class="day-title">${escapeHtml(getTaskFocus(day))}</h5>
              <p class="day-focus">${escapeHtml(getTaskObjective(day))}</p>
              ${renderTaskPreview(day)}
            </article>
          `).join("")}
        </div>
      </section>
    </article>
  `;
}

function renderHistory(records) {
  const container = document.getElementById("history-list");
  const controls = document.getElementById("history-controls");
  const loadMoreButton = document.getElementById("load-more-button");

  if (!Array.isArray(records) || records.length === 0) {
    container.innerHTML = '<div class="empty-state">No plan yet. Create a study plan to begin.</div>';
    controls.classList.add("hidden");
    return;
  }

  const visibleRecords = records.slice(0, visibleHistoryCount);
  container.innerHTML = visibleRecords.map((record) => {
    const state = record.perceived_state || {};
    return `
      <article class="history-card">
        <div class="history-top">
          <p class="section-label">Plan</p>
          <span class="task-badge">${escapeHtml(state.task_type || "study plan")}</span>
        </div>
        <div class="history-body">
          <div class="history-copy">
            <h3 class="history-title">${escapeHtml(getPlanTitle(record))}</h3>
            <p class="history-summary">${escapeHtml(record.plan?.summary || "")}</p>
            <div class="history-goal-block">
              <span class="meta-label">Goal</span>
              <p class="history-goal">${escapeHtml(record.goal || "")}</p>
            </div>
          </div>
          <div class="history-meta">
            <div class="history-date">
              <span class="meta-label">Created</span>
              <span class="meta-value">${escapeHtml(record.created_at || "")}</span>
            </div>
            <div class="history-date">
              <span class="meta-label">Last updated</span>
              <span class="meta-value">${escapeHtml(record.updated_at || record.created_at || "")}</span>
            </div>
          </div>
          <div class="history-progress">
            ${renderProgressBar(record, true)}
          </div>
        </div>
        <div class="history-actions">
          <button class="secondary-button history-button" type="button" data-record-id="${escapeHtml(record.id || "")}">
            View / Edit
          </button>
          <button
            class="danger-button history-button"
            type="button"
            data-modal-action="delete-plan"
            data-record-id="${escapeHtml(record.id || "")}"
          >
            Delete
          </button>
        </div>
      </article>
    `;
  }).join("");

  if (records.length > visibleHistoryCount) {
    controls.classList.remove("hidden");
    loadMoreButton.classList.remove("hidden");
  } else {
    controls.classList.add("hidden");
    loadMoreButton.classList.add("hidden");
  }
}

function renderUpdateHistoryPanel(record) {
  const history = Array.isArray(record?.update_history) ? [...record.update_history] : [];
  history.sort((left, right) => String(right?.timestamp || "").localeCompare(String(left?.timestamp || "")));

  return `
    <details class="update-history-panel">
      <summary>Update history (${history.length})</summary>
      <div class="update-history-list">
        ${history.length > 0 ? history.map((entry) => `
          <article class="update-history-item">
            <span class="meta-label">${escapeHtml(entry.timestamp || "")}</span>
            <p>${escapeHtml(entry.feedback || "")}</p>
          </article>
        `).join("") : '<p class="muted">No update history yet.</p>'}
      </div>
    </details>
  `;
}

function renderModalContent(record) {
  const plan = record.plan || {};
  const state = record.perceived_state || {};
  const latestFeedbackNote = record.latest_feedback ? `
    <div class="latest-feedback-note">
      <span class="meta-label">Latest feedback</span>
      <p>${escapeHtml(record.latest_feedback)}</p>
    </div>
  ` : "";

  return `
    <div class="modal-detail-shell">
      <header class="modal-header">
        <div class="modal-header-copy">
          <p class="section-label">Plan details</p>
          <h2 id="record-modal-title">${escapeHtml(getPlanTitle(record))}</h2>
        </div>
        <div class="modal-header-meta">
          <div class="plan-badge-row modal-badge-row">
            <span class="task-badge">${escapeHtml(state.task_type || "study plan")}</span>
          </div>
          <p class="timestamp-note">Created: ${escapeHtml(record.created_at || "")}</p>
          <p class="timestamp-note">Last updated: ${escapeHtml(record.updated_at || record.created_at || "")}</p>
        </div>
      </header>

      <section class="detail-section detail-section-wide">
        <h4>Goal</h4>
        <p>${escapeHtml(record.goal || "")}</p>
      </section>

      <section class="detail-section detail-section-wide">
        ${renderProgressBar(record)}
      </section>

      <section class="detail-section detail-section-wide">
        <h4>Perceived state</h4>
        <div class="summary-grid modal-summary-grid">
          <article class="summary-tile">
            <span class="meta-label">Topic</span>
            <strong>${escapeHtml(state.topic || "")}</strong>
          </article>
          <article class="summary-tile">
            <span class="meta-label">Days</span>
            <strong>${escapeHtml(state.days || "")}</strong>
          </article>
          <article class="summary-tile">
            <span class="meta-label">Difficulty</span>
            <strong>${escapeHtml(state.difficulty || "")}</strong>
          </article>
          <article class="summary-tile">
            <span class="meta-label">Task Type</span>
            <strong>${escapeHtml(state.task_type || "")}</strong>
          </article>
        </div>
      </section>

      <section class="detail-section detail-section-wide">
        <h4>Summary</h4>
        <p>${escapeHtml(plan.summary || "")}</p>
      </section>

      <section class="detail-section detail-section-wide">
        <h4>Strategy</h4>
        <p>${escapeHtml(getPlanStrategy(plan))}</p>
      </section>

      <section class="detail-section detail-section-wide">
        <h4>Daily tasks</h4>
        <div class="detail-daily-grid">
          ${getDailyTasks(plan).map((day, index) => `
            <article class="day-card detail-day-card">
              <span class="day-label">Day ${escapeHtml(getTaskDayNumber(day, index))}</span>
              <h5 class="day-title">${escapeHtml(getTaskFocus(day))}</h5>
              <p class="day-focus">${escapeHtml(getTaskObjective(day))}</p>
              ${renderTaskRows(record.id, Array.isArray(day.tasks) ? day.tasks : [])}
            </article>
          `).join("")}
        </div>
      </section>

      <div class="detail-two-column">
        <section class="detail-section">
          <h4>Priority list</h4>
          ${renderList(plan.priority_list, "No priorities recorded.")}
        </section>

        <section class="detail-section">
          <h4>Study notes</h4>
          ${renderList(getStudyNotes(plan), "No study notes recorded.")}
        </section>
      </div>

      <section class="detail-section risk-panel detail-section-wide">
        <h4>Risk warning</h4>
        <p>${escapeHtml(plan.risk_warning || "")}</p>
      </section>

      <section class="detail-section plan-update-panel detail-section-wide">
        <h4>Update this plan</h4>
        <p class="helper-text">
          Describe how you want to revise this plan, for example: add more practice tasks,
          make Day 3 shorter, or focus on weak areas.
        </p>
        ${latestFeedbackNote}
        <textarea
          id="modal-feedback-${escapeHtml(record.id || "")}"
          class="textarea-compact"
          placeholder="Add more practice questions to Day 3 and make Day 5 a final review day."
        ></textarea>
        <div class="modal-actions">
          <button
            type="button"
            data-modal-action="update-plan"
            data-record-id="${escapeHtml(record.id || "")}"
          >
            Update Plan
          </button>
        </div>
      </section>

      ${renderUpdateHistoryPanel(record)}

      <section class="modal-danger-zone">
        <h4>Delete plan</h4>
        <p class="helper-text">
          Remove this plan from the local data store. This action cannot be undone.
        </p>
        <div class="modal-actions">
          <button
            type="button"
            class="danger-button"
            data-modal-action="delete-plan"
            data-record-id="${escapeHtml(record.id || "")}"
          >
            Delete
          </button>
        </div>
      </section>
    </div>
  `;
}

function showRecordDetails(recordId) {
  const record = findRecordById(recordId);
  if (!record) {
    showMessage("Could not find that plan in local data.", "error");
    return;
  }

  activeRecordId = String(recordId);
  const modal = document.getElementById("record-modal");
  const modalCard = modal.querySelector(".modal-card");
  const content = document.getElementById("record-modal-content");
  content.innerHTML = renderModalContent(record);
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  modalCard.scrollTop = 0;
}

function closeRecordDetails() {
  const modal = document.getElementById("record-modal");
  const content = document.getElementById("record-modal-content");
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
  content.innerHTML = "";
  document.body.classList.remove("modal-open");
  activeRecordId = null;
}

function refreshModalIfOpen() {
  if (!activeRecordId) {
    return;
  }

  const modal = document.getElementById("record-modal");
  if (modal.classList.contains("hidden")) {
    return;
  }

  const record = findRecordById(activeRecordId);
  if (!record) {
    closeRecordDetails();
    return;
  }

  document.getElementById("record-modal-content").innerHTML = renderModalContent(record);
}

function loadMoreHistory() {
  visibleHistoryCount += HISTORY_PAGE_SIZE;
  renderHistory(localRecords);
}

function renderLocalData() {
  renderPlan(getLatestLocalRecord());
  renderHistory(localRecords);
  refreshModalIfOpen();
}

async function loadHistory() {
  try {
    const { data } = await requestJson("/api/history");
    setLocalRecords(data.records || []);
    renderLocalData();
  } catch (error) {
    showMessage("Could not load planning history.", "error");
  }
}

async function createPlan() {
  const goalInput = document.getElementById("goal-input");
  const createButton = document.getElementById("create-button");
  const goal = goalInput.value.trim();

  if (!goal) {
    showMessage("Please enter a study goal.", "error");
    return;
  }

  clearMessage();
  setButtonLoading(createButton, "Generating...", true);
  try {
    const { response, data } = await requestJson("/api/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal }),
    });

    if (!response.ok || !data.success) {
      showMessage(data.error || "Failed to create the study plan.", "error");
      return;
    }

    upsertLocalRecord(data.record);
    visibleHistoryCount = Math.max(HISTORY_PAGE_SIZE, visibleHistoryCount);
    renderLocalData();
    goalInput.value = "";
    showMessage("Study plan generated.", "success");
  } catch (error) {
    showMessage("Failed to create the study plan.", "error");
  } finally {
    setButtonLoading(createButton, "Generating...", false);
  }
}

async function updatePlanFromModal(recordId) {
  const input = document.getElementById(`modal-feedback-${recordId}`);
  const button = document.querySelector(`[data-modal-action="update-plan"][data-record-id="${recordId}"]`);
  const feedback = input ? input.value.trim() : "";

  if (!feedback) {
    showMessage("Please enter update instructions for this plan.", "error");
    return;
  }

  clearMessage();
  setButtonLoading(button, "Updating...", true);
  try {
    const { response, data } = await requestJson("/api/update-plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ record_id: recordId, feedback }),
    });

    if (!response.ok || !data.success) {
      showMessage(data.error || "Failed to update this plan.", "error");
      return;
    }

    upsertLocalRecord(data.record);
    renderLocalData();
    showMessage("Plan updated.", "success");
  } catch (error) {
    showMessage("Failed to update this plan.", "error");
  } finally {
    setButtonLoading(button, "Updating...", false);
  }
}

function cloneRecordsSnapshot() {
  return JSON.parse(JSON.stringify(localRecords));
}

function applyTaskStatusLocally(recordId, taskId, status) {
  const record = findRecordById(recordId);
  if (!record) {
    return false;
  }

  for (const day of getDailyTasks(record.plan || {})) {
    const tasks = Array.isArray(day.tasks) ? day.tasks : [];
    for (const task of tasks) {
      if (String(task?.id || "") !== String(taskId || "")) {
        continue;
      }
      task.status = status;
      record.updated_at = new Date().toISOString().slice(0, 19);
      return true;
    }
  }
  return false;
}

async function updateTaskStatus(recordId, taskId, status) {
  if (!VALID_TASK_STATUSES.has(status)) {
    showMessage("Invalid task status.", "error");
    return;
  }

  const record = findRecordById(recordId);
  if (!record) {
    showMessage("Could not find that plan in local data.", "error");
    return;
  }

  let currentStatus = null;
  for (const day of getDailyTasks(record.plan || {})) {
    for (const task of Array.isArray(day.tasks) ? day.tasks : []) {
      if (String(task?.id || "") === String(taskId || "")) {
        currentStatus = getTaskStatus(task);
      }
    }
  }
  if (currentStatus === status) {
    return;
  }

  const snapshot = cloneRecordsSnapshot();
  if (!applyTaskStatusLocally(recordId, taskId, status)) {
    showMessage("Could not find that task in local data.", "error");
    return;
  }

  renderLocalData();

  try {
    const { response, data } = await requestJson("/api/task-status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ record_id: recordId, task_id: taskId, status }),
    });

    if (!response.ok || !data.success) {
      setLocalRecords(snapshot);
      renderLocalData();
      showMessage(data.error || "Failed to update task status.", "error");
      return;
    }

    upsertLocalRecord(data.record);
    renderLocalData();
  } catch (error) {
    setLocalRecords(snapshot);
    renderLocalData();
    showMessage("Failed to update task status.", "error");
  }
}

async function deletePlan(recordId) {
  if (!window.confirm("Are you sure you want to delete this plan? This cannot be undone.")) {
    return;
  }

  const button = document.querySelector(`[data-modal-action="delete-plan"][data-record-id="${recordId}"]`);
  clearMessage();
  setButtonLoading(button, "Deleting...", true);

  try {
    const { response, data } = await requestJson("/api/delete-plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ record_id: recordId }),
    });

    if (!response.ok || !data.success) {
      showMessage(data.error || "Failed to delete this plan.", "error");
      return;
    }

    removeLocalRecord(recordId);
    closeRecordDetails();
    renderLocalData();
    showMessage("Plan deleted.", "success");
  } catch (error) {
    showMessage("Failed to delete this plan.", "error");
  } finally {
    setButtonLoading(button, "Deleting...", false);
  }
}

function initializeRecords() {
  const bootRecords = Array.isArray(window.STUDY_PLAN_RECORDS) ? window.STUDY_PLAN_RECORDS : [];
  setLocalRecords(bootRecords);
  renderLocalData();
  if (localRecords.length === 0) {
    loadHistory();
  }
}

function handleRecordClick(event) {
  const taskButton = event.target.closest("[data-task-action='status']");
  if (taskButton) {
    updateTaskStatus(
      taskButton.dataset.recordId || "",
      taskButton.dataset.taskId || "",
      taskButton.dataset.status || "",
    );
    return;
  }

  const modalActionButton = event.target.closest("[data-modal-action]");
  if (modalActionButton) {
    const recordId = modalActionButton.dataset.recordId || "";
    const action = modalActionButton.dataset.modalAction || "";
    if (action === "update-plan") {
      updatePlanFromModal(recordId);
      return;
    }
    if (action === "delete-plan") {
      deletePlan(recordId);
      return;
    }
  }

  const detailButton = event.target.closest("[data-record-id]");
  if (!detailButton) {
    return;
  }

  if (detailButton instanceof HTMLButtonElement) {
    showRecordDetails(detailButton.dataset.recordId || "");
  }
}

function handleEscapeClose(event) {
  if (event.key === "Escape") {
    closeRecordDetails();
  }
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}

window.addEventListener("DOMContentLoaded", () => {
  document.getElementById("create-button").addEventListener("click", createPlan);
  document.getElementById("load-more-button").addEventListener("click", loadMoreHistory);
  document.getElementById("back-to-top-button").addEventListener("click", scrollToTop);
  document.querySelectorAll("[data-scroll-top]").forEach((element) => {
    element.addEventListener("click", (event) => {
      event.preventDefault();
      scrollToTop();
    });
  });
  document.getElementById("record-modal-close").addEventListener("click", closeRecordDetails);
  document.getElementById("record-modal-backdrop").addEventListener("click", closeRecordDetails);
  document.addEventListener("click", handleRecordClick);
  document.addEventListener("keydown", handleEscapeClose);
  initializeRecords();
});
