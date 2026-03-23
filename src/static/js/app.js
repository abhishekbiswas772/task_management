/* ── Constants ──────────────────────────────────────────────────── */
const COLUMNS = [
  "TODO",
  "In Progress",
  "Internal Testing",
  "Client Deployment UAT",
  "Client Production",
  "Dependency List",
  "Done Internally",
];

const COL_COLORS = {
  "TODO":                   "#6B7280",
  "In Progress":            "#8B5CF6",
  "Internal Testing":       "#3B82F6",
  "Client Deployment UAT":  "#F97316",
  "Client Production":      "#22C55E",
  "Dependency List":        "#B45309",
  "Done Internally":        "#14B8A6",
};

const PRIORITY_COLORS = { High: "#EF4444", Medium: "#F97316", Low: "#22C55E" };

/* ── State ──────────────────────────────────────────────────────── */
const state = {
  month:      new Date().getMonth() + 1,
  year:       new Date().getFullYear(),
  tasks:      [],
  dragTaskId: null,
};

let currentTaskId = null;

/* ── API ────────────────────────────────────────────────────────── */
const api = {
  async getTasks(month, year) {
    const r = await fetch(`/api/tasks?month=${month}&year=${year}`);
    return r.json();
  },
  async createTask(data) {
    const r = await fetch("/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return r.json();
  },
  async updateTask(id, data) {
    const r = await fetch(`/api/tasks/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return r.json();
  },
  async deleteTask(id) {
    const r = await fetch(`/api/tasks/${id}`, { method: "DELETE" });
    return r.json();
  },
  async addComment(taskId, text) {
    const r = await fetch(`/api/tasks/${taskId}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    return r.json();
  },
  async deleteComment(commentId) {
    const r = await fetch(`/api/comments/${commentId}`, { method: "DELETE" });
    return r.json();
  },
};

/* ── Helpers ────────────────────────────────────────────────────── */
function esc(str) {
  const d = document.createElement("div");
  d.appendChild(document.createTextNode(String(str || "")));
  return d.innerHTML;
}

function hexAlpha(hex, a) {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${a})`;
}

function monthName(m) {
  return new Date(2000, m - 1, 1).toLocaleString("default", { month: "long" });
}

function isCurrentMonth() {
  const n = new Date();
  return state.month === n.getMonth() + 1 && state.year === n.getFullYear();
}

function fmtDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

function fmtDateTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
    + " · "
    + d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

function dueColor(iso) {
  const d = new Date(iso);
  const now = new Date();
  if (d < now) return "#EF4444";
  if (d - now < 86_400_000) return "#F97316";
  return "#3B82F6";
}

function toast(msg) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = msg;
  document.getElementById("toast-container").appendChild(el);
  setTimeout(() => el.remove(), 2600);
}

/* ── Render: Header ─────────────────────────────────────────────── */
function renderHeader() {
  document.getElementById("monthName").textContent = monthName(state.month);
  document.getElementById("yearDisplay").textContent = state.year;
  document.getElementById("todayBtn").style.display = isCurrentMonth() ? "none" : "inline-block";

  const count = state.tasks.length;
  document.getElementById("taskSummary").textContent =
    `${count} task${count !== 1 ? "s" : ""}`;
}

/* ── Render: Board ──────────────────────────────────────────────── */
function renderBoard() {
  document.getElementById("board").innerHTML =
    COLUMNS.map(renderColumn).join("");
  attachDragDrop();
  attachCardClicks();
  attachAddButtons();
}

function renderColumn(col) {
  const tasks = state.tasks.filter(t => t.column_name === col);
  const color = COL_COLORS[col];
  const bodyHtml = tasks.length
    ? tasks.map(renderCard).join("")
    : `<div class="empty-state">
         <div class="empty-icon">📋</div>
         <span>No tasks</span>
       </div>`;

  return `
    <div class="column" data-column="${esc(col)}" style="--col-color:${color}">
      <div class="column-header">
        <div class="column-header-top">
          <div class="column-accent" style="background:${color}"></div>
          <span class="column-name">${esc(col)}</span>
          <span class="column-badge" style="color:${color};background:${hexAlpha(color,0.12)}">${tasks.length}</span>
        </div>
        <button class="add-task-btn" data-column="${esc(col)}">
          <span class="plus-icon">+</span> Add Task
        </button>
      </div>
      <div class="column-body" data-column="${esc(col)}">${bodyHtml}</div>
    </div>`;
}

function renderCard(task) {
  const pc    = PRIORITY_COLORS[task.priority] || "#F97316";
  const cc    = (task.comments || []).length;
  const dueTxt = task.due_date
    ? `<span class="task-due" style="color:${dueColor(task.due_date)};background:${dueColor(task.due_date)}18">
         🔔 ${fmtDateTime(task.due_date)}
       </span>`
    : "";
  const cmtTxt = cc
    ? `<span class="task-comment-count">💬 ${cc}</span>`
    : "";

  return `
    <div class="task-card" data-id="${task.id}" draggable="true">
      <div class="task-priority-bar" style="background:${pc}"></div>
      <div class="task-card-content">
        <div class="task-card-top">
          <span class="priority-badge" style="color:${pc};background:${hexAlpha(pc,0.1)}">${esc(task.priority)}</span>
          ${cmtTxt}
        </div>
        <div class="task-title">${esc(task.title)}</div>
        ${task.description ? `<div class="task-desc">${esc(task.description)}</div>` : ""}
        <div class="task-footer">
          ${dueTxt}
          <span class="task-created">${fmtDate(task.created_at)}</span>
        </div>
      </div>
    </div>`;
}

/* ── Drag & Drop ────────────────────────────────────────────────── */
function attachDragDrop() {
  document.querySelectorAll(".task-card").forEach(card => {
    card.addEventListener("dragstart", e => {
      state.dragTaskId = card.dataset.id;
      card.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", card.dataset.id);
    });
    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");
    });
  });

  document.querySelectorAll(".column").forEach(col => {
    col.addEventListener("dragover", e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      col.classList.add("drag-over");
    });
    col.addEventListener("dragleave", e => {
      if (!col.contains(e.relatedTarget)) col.classList.remove("drag-over");
    });
    col.addEventListener("drop", async e => {
      e.preventDefault();
      col.classList.remove("drag-over");
      const taskId = state.dragTaskId || e.dataTransfer.getData("text/plain");
      const target = col.dataset.column;
      if (!taskId || !target) return;
      const task = state.tasks.find(t => t.id === taskId);
      if (!task || task.column_name === target) return;

      task.column_name = target;
      renderBoard();
      renderHeader();
      await api.updateTask(taskId, { column_name: target });
      toast(`Moved to "${target}"`);
    });
  });
}

function attachCardClicks() {
  document.querySelectorAll(".task-card").forEach(card => {
    card.addEventListener("click", () => openDetail(card.dataset.id));
  });
}

function attachAddButtons() {
  document.querySelectorAll(".add-task-btn").forEach(btn => {
    btn.addEventListener("click", () => openAddTask(btn.dataset.column));
  });
}

/* ── Load data ──────────────────────────────────────────────────── */
async function loadTasks() {
  // Show skeleton
  document.getElementById("board").innerHTML = COLUMNS.map(col => `
    <div class="column" style="--col-color:${COL_COLORS[col]}">
      <div class="column-header">
        <div class="column-header-top">
          <div class="column-accent" style="background:${COL_COLORS[col]}"></div>
          <span class="column-name">${esc(col)}</span>
        </div>
      </div>
      <div class="column-body">
        <div class="skeleton-card"></div>
        <div class="skeleton-card"></div>
      </div>
    </div>`).join("");

  state.tasks = await api.getTasks(state.month, state.year);
  renderHeader();
  renderBoard();
}

/* ── Month nav ──────────────────────────────────────────────────── */
function changeMonth(delta) {
  state.month += delta;
  if (state.month > 12) { state.month = 1;  state.year++; }
  if (state.month < 1)  { state.month = 12; state.year--; }
  renderHeader();
  loadTasks();
}

/* ── Add Task Modal ─────────────────────────────────────────────── */
function openAddTask(column = COLUMNS[0]) {
  const modal = document.getElementById("addTaskModal");
  document.getElementById("addTaskTitle").value    = "";
  document.getElementById("addTaskDesc").value     = "";
  document.getElementById("addColumnSelect").value = column;
  document.getElementById("addTaskPriority").value = "Medium";
  document.getElementById("addDueDateToggle").checked = false;
  document.getElementById("addDueDateRow").style.display = "none";
  modal.classList.add("open");
  setTimeout(() => document.getElementById("addTaskTitle").focus(), 60);
}

function closeAddTask() {
  document.getElementById("addTaskModal").classList.remove("open");
}

async function submitAddTask() {
  const title = document.getElementById("addTaskTitle").value.trim();
  if (!title) {
    document.getElementById("addTaskTitle").focus();
    return;
  }
  const hasDue  = document.getElementById("addDueDateToggle").checked;
  const dueVal  = document.getElementById("addDueDate").value;
  const btn     = document.getElementById("submitAddTask");
  btn.disabled  = true;

  await api.createTask({
    title,
    description: document.getElementById("addTaskDesc").value,
    column:      document.getElementById("addColumnSelect").value,
    month:       state.month,
    year:        state.year,
    priority:    document.getElementById("addTaskPriority").value,
    due_date:    hasDue && dueVal ? dueVal : null,
  });

  btn.disabled = false;
  closeAddTask();
  await loadTasks();
  toast("Task created");
}

/* ── Task Detail Modal ──────────────────────────────────────────── */
function openDetail(taskId) {
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;
  currentTaskId = taskId;
  renderDetail(task);
  document.getElementById("taskDetailModal").classList.add("open");
}

function closeDetail() {
  document.getElementById("taskDetailModal").classList.remove("open");
  currentTaskId = null;
}

function renderDetail(task) {
  const pc  = PRIORITY_COLORS[task.priority] || "#F97316";
  const cc  = COL_COLORS[task.column_name]   || "#6B7280";
  const comments = (task.comments || []);

  const commentsHtml = comments.length
    ? comments.map(c => `
        <div class="comment-row">
          <div class="comment-content">
            <p>${esc(c.text)}</p>
            <span class="comment-date">${fmtDate(c.created_at)}</span>
          </div>
          <button class="comment-delete-btn" data-comment-id="${c.id}" title="Delete">✕</button>
        </div>`).join("")
    : `<p style="font-size:13px;color:var(--text-subtle);padding:4px 0">No comments yet.</p>`;

  const dueHtml = task.due_date
    ? `<div class="due-badge" style="color:${dueColor(task.due_date)};background:${hexAlpha(dueColor(task.due_date),0.08)}">
         🔔 ${fmtDateTime(task.due_date)}
         ${new Date(task.due_date) < new Date()
           ? '<span class="overdue-tag">Overdue</span>'
           : `<span style="font-size:11px;opacity:.7">${relativeTime(task.due_date)}</span>`}
       </div>`
    : `<span style="font-size:13px;color:var(--text-subtle)">No reminder set.</span>`;

  document.getElementById("detailContent").innerHTML = `
    <input class="detail-title-input" id="detailTitle" type="text" value="${esc(task.title)}" />

    <div class="detail-meta">
      <span class="priority-badge" style="color:${pc};background:${hexAlpha(pc,0.1)}">🚩 ${esc(task.priority)}</span>
      <span class="priority-badge" style="color:${cc};background:${hexAlpha(cc,0.1)}">${esc(task.column_name)}</span>
      <span style="font-size:11px;color:var(--text-subtle);margin-left:auto">Created ${fmtDate(task.created_at)}</span>
    </div>

    <div class="divider"></div>

    <div class="form-row">
      <div class="form-group">
        <label>Column</label>
        <select id="detailColumn">
          ${COLUMNS.map(c => `<option value="${esc(c)}" ${task.column_name === c ? "selected" : ""}>${esc(c)}</option>`).join("")}
        </select>
      </div>
      <div class="form-group">
        <label>Priority</label>
        <div class="priority-selector">
          ${["Low","Medium","High"].map(p => {
            const active = task.priority === p;
            const pColor = PRIORITY_COLORS[p];
            return `<button class="priority-btn ${active ? "active" : ""}" data-priority="${p}"
                      style="${active ? `background:${pColor};color:#fff;border-color:${pColor}` : ""}">${p}</button>`;
          }).join("")}
        </div>
      </div>
    </div>

    <div class="form-group">
      <label>Description</label>
      <textarea id="detailDesc" rows="4">${esc(task.description)}</textarea>
    </div>

    <div class="divider"></div>

    <div class="form-group">
      <label>Reminder / Due Date</label>
      <div class="toggle-row">
        <span class="toggle-label-text">Set due date</span>
        <label class="switch">
          <input type="checkbox" id="detailDueToggle" ${task.due_date ? "checked" : ""} />
          <span class="slider"></span>
        </label>
      </div>
      <div id="detailDueDateRow" style="display:${task.due_date ? "block" : "none"}">
        <input type="datetime-local" id="detailDueDate"
               value="${task.due_date ? task.due_date.slice(0, 16) : ""}" />
      </div>
      <div id="dueBadgeDisplay">${dueHtml}</div>
    </div>

    <div class="divider"></div>

    <div class="form-group">
      <label>Comments (${comments.length})</label>
      <div class="comments-list" id="commentsList">${commentsHtml}</div>
      <div class="add-comment-row">
        <textarea id="newCommentText" rows="2" placeholder="Write a comment…"></textarea>
        <button class="btn-primary" id="submitComment">Post</button>
      </div>
    </div>

    <div class="detail-actions">
      <button class="btn-danger" id="deleteTaskBtn">Delete Task</button>
      <button class="btn-primary" id="saveDetailBtn">Save Changes</button>
    </div>`;

  // Events inside detail
  document.getElementById("detailDueToggle").addEventListener("change", e => {
    document.getElementById("detailDueDateRow").style.display = e.target.checked ? "block" : "none";
  });

  document.querySelectorAll(".priority-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".priority-btn").forEach(b => {
        b.classList.remove("active");
        b.style.cssText = "";
      });
      const color = PRIORITY_COLORS[btn.dataset.priority];
      btn.classList.add("active");
      btn.style.background   = color;
      btn.style.color        = "#fff";
      btn.style.borderColor  = color;
    });
  });

  document.getElementById("saveDetailBtn").addEventListener("click", saveDetail);
  document.getElementById("deleteTaskBtn").addEventListener("click", deleteCurrentTask);
  document.getElementById("submitComment").addEventListener("click", submitComment);

  document.querySelectorAll(".comment-delete-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      await api.deleteComment(btn.dataset.commentId);
      await loadTasks();
      const updated = state.tasks.find(t => t.id === currentTaskId);
      if (updated) renderDetail(updated);
      toast("Comment deleted");
    });
  });
}

async function saveDetail() {
  if (!currentTaskId) return;
  const btn = document.getElementById("saveDetailBtn");
  btn.disabled = true;

  const hasDue    = document.getElementById("detailDueToggle").checked;
  const dueVal    = document.getElementById("detailDueDate").value;
  const activePri = document.querySelector(".priority-btn.active");

  await api.updateTask(currentTaskId, {
    title:       document.getElementById("detailTitle").value.trim(),
    description: document.getElementById("detailDesc").value,
    column_name: document.getElementById("detailColumn").value,
    priority:    activePri ? activePri.dataset.priority : "Medium",
    due_date:    hasDue && dueVal ? dueVal : null,
  });

  btn.disabled = false;
  await loadTasks();
  const updated = state.tasks.find(t => t.id === currentTaskId);
  if (updated) renderDetail(updated);
  toast("Changes saved");
}

async function deleteCurrentTask() {
  if (!currentTaskId) return;
  if (!confirm("Delete this task and all its comments?")) return;
  await api.deleteTask(currentTaskId);
  closeDetail();
  await loadTasks();
  toast("Task deleted");
}

async function submitComment() {
  const text = document.getElementById("newCommentText").value.trim();
  if (!text || !currentTaskId) return;
  const btn = document.getElementById("submitComment");
  btn.disabled = true;
  await api.addComment(currentTaskId, text);
  btn.disabled = false;
  document.getElementById("newCommentText").value = "";
  await loadTasks();
  const updated = state.tasks.find(t => t.id === currentTaskId);
  if (updated) renderDetail(updated);
  toast("Comment added");
}

function relativeTime(iso) {
  const diff = new Date(iso) - new Date();
  if (diff <= 0) return "";
  const h = Math.floor(diff / 3_600_000);
  if (h < 1) return "< 1h left";
  if (h < 24) return `${h}h left`;
  return `${Math.floor(h / 24)}d left`;
}

/* ── Export Modal ───────────────────────────────────────────────── */
function openExport() {
  const label = `${monthName(state.month)} ${state.year}`;
  const count = state.tasks.length;
  document.getElementById("exportMonthLabel").textContent = label;
  document.getElementById("exportCountLabel").textContent =
    `${count} task${count !== 1 ? "s" : ""}`;
  document.getElementById("exportModal").classList.add("open");
}

function closeExport() {
  document.getElementById("exportModal").classList.remove("open");
}

function doExportCSV() {
  const label = `${monthName(state.month)}-${state.year}`;
  window.location.href =
    `/api/export/csv?month=${state.month}&year=${state.year}&label=${encodeURIComponent(label)}`;
  closeExport();
}

function doExportExcel() {
  const label = `${monthName(state.month)}-${state.year}`;
  window.location.href =
    `/api/export/excel?month=${state.month}&year=${state.year}&label=${encodeURIComponent(label)}`;
  closeExport();
}

/* ── Init ───────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  /* Month nav */
  document.getElementById("prevMonth").addEventListener("click", () => changeMonth(-1));
  document.getElementById("nextMonth").addEventListener("click", () => changeMonth(1));
  document.getElementById("todayBtn").addEventListener("click", () => {
    const n = new Date();
    state.month = n.getMonth() + 1;
    state.year  = n.getFullYear();
    renderHeader();
    loadTasks();
  });

  /* Export */
  document.getElementById("exportBtn").addEventListener("click", openExport);
  document.getElementById("closeExportModal").addEventListener("click", closeExport);
  document.getElementById("exportCsvBtn").addEventListener("click", doExportCSV);
  document.getElementById("exportExcelBtn").addEventListener("click", doExportExcel);

  /* Add task modal */
  document.getElementById("cancelAddTask").addEventListener("click", closeAddTask);
  document.getElementById("submitAddTask").addEventListener("click", submitAddTask);
  document.getElementById("addDueDateToggle").addEventListener("change", e => {
    document.getElementById("addDueDateRow").style.display = e.target.checked ? "block" : "none";
  });
  document.getElementById("addTaskTitle").addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submitAddTask(); }
  });

  /* Detail modal */
  document.getElementById("closeDetailModal").addEventListener("click", closeDetail);

  /* Click outside to close */
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", e => {
      if (e.target === overlay) {
        overlay.classList.remove("open");
        if (overlay.id === "taskDetailModal") currentTaskId = null;
      }
    });
  });

  /* ESC to close */
  document.addEventListener("keydown", e => {
    if (e.key !== "Escape") return;
    document.querySelectorAll(".modal-overlay.open").forEach(m => {
      m.classList.remove("open");
      if (m.id === "taskDetailModal") currentTaskId = null;
    });
  });

  renderHeader();
  loadTasks();
});
