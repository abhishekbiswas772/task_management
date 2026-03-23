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

/* ── API helpers ────────────────────────────────────────────────── */
async function apiFetch(url, options = {}) {
  const r = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (r.status === 401) {
    window.location.href = "/auth/login";
    return null;
  }
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.message || body.error || `HTTP ${r.status}`);
  }
  if (r.status === 204) return null;
  return r.json();
}

const api = {
  getTasks:      (m, y)   => apiFetch(`/api/tasks/?month=${m}&year=${y}`),
  getSummary:    (m, y)   => apiFetch(`/api/export/summary?month=${m}&year=${y}`),
  createTask:    (data)   => apiFetch("/api/tasks/", { method: "POST", body: JSON.stringify(data) }),
  updateTask:    (id, d)  => apiFetch(`/api/tasks/${id}`, { method: "PUT", body: JSON.stringify(d) }),
  deleteTask:    (id)     => apiFetch(`/api/tasks/${id}`, { method: "DELETE" }),
  addComment:    (tid, t) => apiFetch(`/api/tasks/${tid}/comments`, { method: "POST", body: JSON.stringify({ text: t }) }),
  deleteComment: (cid)    => apiFetch(`/api/comments/${cid}`, { method: "DELETE" }),
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
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function fmtDateTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
    + " · " + d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

function dueColor(iso) {
  const d = new Date(iso), now = new Date();
  if (d < now) return "#EF4444";
  if (d - now < 86_400_000) return "#F97316";
  return "#3B82F6";
}

function relativeTime(iso) {
  const diff = new Date(iso) - new Date();
  if (diff <= 0) return "";
  const h = Math.floor(diff / 3_600_000);
  if (h < 1) return "< 1h left";
  if (h < 24) return `${h}h left`;
  return `${Math.floor(h / 24)}d left`;
}

function toast(msg, type = "default") {
  const el = document.createElement("div");
  el.className = "toast";
  if (type === "error") el.style.background = "#7F1D1D";
  el.textContent = msg;
  document.getElementById("toast-container").appendChild(el);
  setTimeout(() => el.remove(), 2800);
}

function summaryExportLabel() {
  return `Summary-${monthName(state.month)}-${state.year}`;
}

function polarToCartesian(cx, cy, r, angle) {
  const radians = (angle - 90) * (Math.PI / 180);
  return {
    x: cx + r * Math.cos(radians),
    y: cy + r * Math.sin(radians),
  };
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`;
}

function chartEmpty(message) {
  return `<div class="summary-empty">${esc(message)}</div>`;
}

function renderHeatmapChart(dailyActivity = []) {
  if (!dailyActivity.length) return chartEmpty("No activity data available.");
  const maxCount = Math.max(...dailyActivity.map(item => item.count), 0);
  const palette = ["#E2E8F0", "#BFDBFE", "#7DD3FC", "#38BDF8", "#0EA5E9", "#0369A1"];
  const getColor = count => {
    if (!count) return palette[0];
    const idx = Math.min(palette.length - 1, Math.ceil((count / maxCount) * (palette.length - 1)));
    return palette[idx];
  };

  const cells = dailyActivity.map(item => `
    <div class="heatmap-cell" style="background:${getColor(item.count)}" title="Day ${item.day}: ${item.count} tasks">
      ${item.day}
    </div>
  `).join("");

  return `
    <div class="summary-heatmap-grid">${cells}</div>
    <div class="summary-legend">
      <span class="summary-legend-item"><span class="summary-legend-swatch" style="background:${palette[0]}"></span>Low</span>
      <span class="summary-legend-item"><span class="summary-legend-swatch" style="background:${palette[3]}"></span>Medium</span>
      <span class="summary-legend-item"><span class="summary-legend-swatch" style="background:${palette[5]}"></span>High</span>
    </div>
  `;
}

function renderBarChart(columns = []) {
  if (!columns.length) return chartEmpty("No column data available.");
  const width = 520;
  const height = 220;
  const padding = { top: 20, right: 20, bottom: 60, left: 36 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const maxValue = Math.max(...columns.map(item => item.count), 1);
  const barWidth = chartWidth / columns.length * 0.62;
  const gap = chartWidth / columns.length;

  const bars = columns.map((item, index) => {
    const x = padding.left + index * gap + (gap - barWidth) / 2;
    const barHeight = (item.count / maxValue) * chartHeight;
    const y = padding.top + chartHeight - barHeight;
    return `
      <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="10" fill="#4F46E5"></rect>
      <text x="${x + barWidth / 2}" y="${y - 8}" text-anchor="middle" font-size="11" fill="#475569">${item.count}</text>
      <text x="${x + barWidth / 2}" y="${height - 20}" text-anchor="middle" font-size="10" fill="#64748B">${esc(item.name.slice(0, 12))}</text>
    `;
  }).join("");

  return `
    <svg class="summary-svg" viewBox="0 0 ${width} ${height}" aria-label="Column bar graph">
      <line x1="${padding.left}" y1="${padding.top + chartHeight}" x2="${width - padding.right}" y2="${padding.top + chartHeight}" stroke="#CBD5E1" stroke-width="1"/>
      ${bars}
    </svg>
  `;
}

function renderLineChart(weeklySummary = []) {
  if (!weeklySummary.length) return chartEmpty("No weekly data available.");
  const width = 620;
  const height = 240;
  const padding = { top: 20, right: 20, bottom: 40, left: 28 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const maxValue = Math.max(...weeklySummary.map(item => item.task_count), 1);

  const points = weeklySummary.map((item, index) => {
    const x = padding.left + (index * chartWidth) / Math.max(weeklySummary.length - 1, 1);
    const y = padding.top + chartHeight - (item.task_count / maxValue) * chartHeight;
    return { ...item, x, y };
  });

  const polyline = points.map(point => `${point.x},${point.y}`).join(" ");
  const markers = points.map(point => `
    <circle cx="${point.x}" cy="${point.y}" r="4.5" fill="#F97316"></circle>
    <text x="${point.x}" y="${point.y - 10}" text-anchor="middle" font-size="11" fill="#475569">${point.task_count}</text>
    <text x="${point.x}" y="${height - 12}" text-anchor="middle" font-size="10" fill="#64748B">${esc(point.label)}</text>
  `).join("");

  return `
    <svg class="summary-svg" viewBox="0 0 ${width} ${height}" aria-label="Weekly trend line graph">
      <line x1="${padding.left}" y1="${padding.top + chartHeight}" x2="${width - padding.right}" y2="${padding.top + chartHeight}" stroke="#CBD5E1" stroke-width="1"/>
      <polyline fill="none" stroke="#F97316" stroke-width="3" points="${polyline}"></polyline>
      ${markers}
    </svg>
  `;
}

function renderPieChart(priorities = []) {
  if (!priorities.length) return chartEmpty("No priority data available.");
  const total = priorities.reduce((sum, item) => sum + item.count, 0);
  if (!total) return chartEmpty("No priority data available.");
  const colors = { High: "#EF4444", Medium: "#F97316", Low: "#22C55E" };
  let startAngle = 0;
  const arcs = priorities.map(item => {
    const angle = (item.count / total) * 360;
    const endAngle = startAngle + angle;
    const path = describeArc(70, 70, 52, startAngle, endAngle);
    const arc = `<path d="${path}" stroke="${colors[item.name] || "#6366F1"}" stroke-width="22" fill="none" stroke-linecap="round"></path>`;
    startAngle = endAngle;
    return arc;
  }).join("");

  const legend = priorities.map(item => `
    <div class="summary-pie-legend-item">
      <span class="summary-legend-swatch" style="background:${colors[item.name] || "#6366F1"}"></span>
      <span>${esc(item.name)} (${item.count})</span>
    </div>
  `).join("");

  return `
    <div class="summary-pie-wrap">
      <svg class="summary-svg" viewBox="0 0 140 140" style="max-width:180px" aria-label="Priority pie chart">
        <circle cx="70" cy="70" r="52" stroke="#E2E8F0" stroke-width="22" fill="none"></circle>
        ${arcs}
        <text x="70" y="66" text-anchor="middle" font-size="22" font-weight="800" fill="#0F172A">${total}</text>
        <text x="70" y="86" text-anchor="middle" font-size="11" fill="#64748B">tasks</text>
      </svg>
      <div class="summary-pie-legend">${legend}</div>
    </div>
  `;
}

/* ── Render: Header ─────────────────────────────────────────────── */
function renderHeader() {
  document.getElementById("monthName").textContent = monthName(state.month);
  document.getElementById("yearDisplay").textContent = state.year;
  document.getElementById("todayBtn").style.display = isCurrentMonth() ? "none" : "inline-block";
  const count = state.tasks.length;
  document.getElementById("taskSummary").textContent = `${count} task${count !== 1 ? "s" : ""}`;
}

/* ── Render: Board ──────────────────────────────────────────────── */
function renderBoard() {
  document.getElementById("board").innerHTML = COLUMNS.map(renderColumn).join("");
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
         <span>Drop tasks here</span>
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
  const pc   = PRIORITY_COLORS[task.priority] || "#F97316";
  const cc   = (task.comments || []).length;
  const tags = Array.isArray(task.tags) ? task.tags : [];

  const dueTxt = task.due_date
    ? `<span class="task-due" style="color:${dueColor(task.due_date)};background:${dueColor(task.due_date)}18">
         🔔 ${fmtDateTime(task.due_date)}
       </span>` : "";

  const cmtTxt = cc
    ? `<span class="task-comment-count">💬 ${cc}</span>` : "";

  const tagsTxt = tags.length
    ? `<div class="task-tags">${tags.slice(0,3).map(t =>
        `<span class="task-tag">${esc(t)}</span>`).join("")}${tags.length > 3 ? `<span class="task-tag">+${tags.length-3}</span>` : ""}</div>`
    : "";

  const creatorTxt = task.creator_name
    ? `<span class="task-creator">
         <span class="task-creator-avatar">${esc(task.creator_name[0].toUpperCase())}</span>
         ${esc(task.creator_name)}
       </span>` : "";

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
        ${tagsTxt}
        <div class="task-footer">
          ${dueTxt}
          ${creatorTxt}
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
    card.addEventListener("dragend", () => card.classList.remove("dragging"));
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
      try {
        await api.updateTask(taskId, { column_name: target });
        toast(`Moved to "${target}"`);
      } catch (err) {
        toast(err.message, "error");
        await loadTasks();
      }
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

  try {
    state.tasks = await api.getTasks(state.month, state.year) || [];
    renderHeader();
    renderBoard();
  } catch (err) {
    toast(`Failed to load tasks: ${err.message}`, "error");
  }
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
function getAddPriority() {
  const active = document.querySelector("#addPrioritySelector .priority-btn.active");
  return active ? active.dataset.priority : "Medium";
}

function openAddTask(column = COLUMNS[0]) {
  document.getElementById("addTaskTitle").value    = "";
  document.getElementById("addTaskDesc").value     = "";
  document.getElementById("addTaskTags").value     = "";
  document.getElementById("addColumnSelect").value = column;
  document.getElementById("addDueDateToggle").checked = false;
  document.getElementById("addDueDateRow").style.display = "none";
  // Reset priority selector to Medium
  document.querySelectorAll("#addPrioritySelector .priority-btn").forEach(btn => {
    btn.classList.remove("active");
    btn.style.cssText = "";
    if (btn.dataset.priority === "Medium") {
      btn.classList.add("active");
      btn.style.background  = "#F97316";
      btn.style.color       = "#fff";
      btn.style.borderColor = "#F97316";
    }
  });
  document.getElementById("addTaskModal").classList.add("open");
  setTimeout(() => document.getElementById("addTaskTitle").focus(), 60);
}

function closeAddTask() {
  document.getElementById("addTaskModal").classList.remove("open");
}

async function submitAddTask() {
  const title = document.getElementById("addTaskTitle").value.trim();
  if (!title) { document.getElementById("addTaskTitle").focus(); return; }

  const hasDue = document.getElementById("addDueDateToggle").checked;
  const dueVal = document.getElementById("addDueDate").value;
  const tagsRaw = document.getElementById("addTaskTags").value;
  const tags = tagsRaw.split(",").map(t => t.trim()).filter(Boolean);
  const btn  = document.getElementById("submitAddTask");
  btn.disabled = true;

  try {
    await api.createTask({
      title,
      description: document.getElementById("addTaskDesc").value,
      column:      document.getElementById("addColumnSelect").value,
      month:       state.month,
      year:        state.year,
      priority:    getAddPriority(),
      due_date:    hasDue && dueVal ? dueVal : null,
      tags,
    });
    closeAddTask();
    await loadTasks();
    toast("Task created");
  } catch (err) {
    toast(err.message, "error");
  } finally {
    btn.disabled = false;
  }
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
  const pc       = PRIORITY_COLORS[task.priority] || "#F97316";
  const cc       = COL_COLORS[task.column_name]   || "#6B7280";
  const comments = task.comments || [];
  const tags     = Array.isArray(task.tags) ? task.tags : [];

  const commentsHtml = comments.length
    ? comments.map(c => `
        <div class="comment-row">
          <div class="comment-content">
            <p>${esc(c.text)}</p>
            <div class="comment-meta">
              ${c.username ? `<span class="comment-author">@${esc(c.username)}</span>` : ""}
              <span class="comment-date">${fmtDate(c.created_at)}</span>
            </div>
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

  const tagsValue = tags.join(", ");

  document.getElementById("detailContent").innerHTML = `
    <input class="detail-title-input" id="detailTitle" type="text" value="${esc(task.title)}"/>

    <div class="detail-meta">
      <span class="priority-badge" style="color:${pc};background:${hexAlpha(pc,0.1)}">🚩 ${esc(task.priority)}</span>
      <span class="priority-badge" style="color:${cc};background:${hexAlpha(cc,0.1)}">${esc(task.column_name)}</span>
      ${task.creator_name
        ? `<span style="font-size:11px;color:var(--accent);font-weight:600">@${esc(task.creator_name)}</span>`
        : ""}
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

    <div class="form-group">
      <label>Tags</label>
      <input type="text" id="detailTags" value="${esc(tagsValue)}" placeholder="frontend, api, bug  (comma-separated)"/>
    </div>

    <div class="divider"></div>

    <div class="form-group">
      <label>Reminder / Due Date</label>
      <div class="toggle-row">
        <span class="toggle-label-text">Set due date</span>
        <label class="switch">
          <input type="checkbox" id="detailDueToggle" ${task.due_date ? "checked" : ""}/>
          <span class="slider"></span>
        </label>
      </div>
      <div id="detailDueDateRow" style="display:${task.due_date ? "block" : "none"}">
        <input type="datetime-local" id="detailDueDate" value="${task.due_date ? task.due_date.slice(0,16) : ""}"/>
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

  // Events
  document.getElementById("detailDueToggle").addEventListener("change", e => {
    document.getElementById("detailDueDateRow").style.display = e.target.checked ? "block" : "none";
  });

  document.querySelectorAll("#detailContent .priority-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#detailContent .priority-btn").forEach(b => {
        b.classList.remove("active"); b.style.cssText = "";
      });
      const color = PRIORITY_COLORS[btn.dataset.priority];
      btn.classList.add("active");
      btn.style.background  = color;
      btn.style.color       = "#fff";
      btn.style.borderColor = color;
    });
  });

  document.getElementById("saveDetailBtn").addEventListener("click", saveDetail);
  document.getElementById("deleteTaskBtn").addEventListener("click", deleteCurrentTask);
  document.getElementById("submitComment").addEventListener("click", submitComment);

  document.querySelectorAll(".comment-delete-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      try {
        await api.deleteComment(btn.dataset.commentId);
        await loadTasks();
        const updated = state.tasks.find(t => t.id === currentTaskId);
        if (updated) renderDetail(updated);
        toast("Comment deleted");
      } catch (err) {
        toast(err.message, "error");
      }
    });
  });
}

async function saveDetail() {
  if (!currentTaskId) return;
  const btn = document.getElementById("saveDetailBtn");
  btn.disabled = true;

  const hasDue    = document.getElementById("detailDueToggle").checked;
  const dueVal    = document.getElementById("detailDueDate").value;
  const activePri = document.querySelector("#detailContent .priority-btn.active");
  const tagsRaw   = document.getElementById("detailTags").value;
  const tags      = tagsRaw.split(",").map(t => t.trim()).filter(Boolean);

  try {
    await api.updateTask(currentTaskId, {
      title:       document.getElementById("detailTitle").value.trim(),
      description: document.getElementById("detailDesc").value,
      column_name: document.getElementById("detailColumn").value,
      priority:    activePri ? activePri.dataset.priority : "Medium",
      due_date:    hasDue && dueVal ? dueVal : null,
      tags,
    });
    await loadTasks();
    const updated = state.tasks.find(t => t.id === currentTaskId);
    if (updated) renderDetail(updated);
    toast("Changes saved");
  } catch (err) {
    toast(err.message, "error");
  } finally {
    btn.disabled = false;
  }
}

async function deleteCurrentTask() {
  if (!currentTaskId) return;
  if (!confirm("Delete this task and all its comments?")) return;
  try {
    await api.deleteTask(currentTaskId);
    closeDetail();
    await loadTasks();
    toast("Task deleted");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function submitComment() {
  const text = document.getElementById("newCommentText").value.trim();
  if (!text || !currentTaskId) return;
  const btn = document.getElementById("submitComment");
  btn.disabled = true;
  try {
    await api.addComment(currentTaskId, text);
    document.getElementById("newCommentText").value = "";
    await loadTasks();
    const updated = state.tasks.find(t => t.id === currentTaskId);
    if (updated) renderDetail(updated);
    toast("Comment added");
  } catch (err) {
    toast(err.message, "error");
  } finally {
    btn.disabled = false;
  }
}

/* ── Export Modal ───────────────────────────────────────────────── */
function openExport() {
  const total = state.tasks.length;
  document.getElementById("exportMonthLabel").textContent = `${monthName(state.month)} ${state.year}`;
  document.getElementById("exportCountLabel").textContent = `${total} task${total !== 1 ? "s" : ""}`;

  // Column breakdown preview
  const breakdown = document.getElementById("exportBreakdown");
  if (!total) {
    breakdown.innerHTML = `<span style="font-size:12px;color:var(--text-subtle)">No tasks this month.</span>`;
  } else {
    breakdown.innerHTML = COLUMNS
      .map(col => {
        const count = state.tasks.filter(t => t.column_name === col).length;
        if (!count) return "";
        const pct   = Math.round((count / total) * 100);
        const color = COL_COLORS[col];
        return `
          <div class="export-col-row">
            <span class="export-col-dot" style="background:${color}"></span>
            <span class="export-col-name">${esc(col)}</span>
            <div class="export-col-bar-track">
              <div class="export-col-bar" style="width:${pct}%;background:${color}"></div>
            </div>
            <span class="export-col-count">${count}</span>
          </div>`;
      })
      .join("");
  }

  document.getElementById("exportModal").classList.add("open");
}

function closeExport() {
  document.getElementById("exportModal").classList.remove("open");
}

function doExportCSV() {
  const label = `${monthName(state.month)}-${state.year}`;
  window.location.href = `/api/export/csv?month=${state.month}&year=${state.year}&label=${encodeURIComponent(label)}`;
  closeExport();
}

function doExportExcel() {
  const label = `${monthName(state.month)}-${state.year}`;
  window.location.href = `/api/export/excel?month=${state.month}&year=${state.year}&label=${encodeURIComponent(label)}`;
  closeExport();
}

async function openSummary() {
  const monthLabel = `${monthName(state.month)} ${state.year}`;
  document.getElementById("summaryMonthLabel").textContent = monthLabel;
  document.getElementById("summaryOverview").innerHTML = `<div class="summary-empty">Loading charts...</div>`;
  document.getElementById("heatmapMeta").textContent = "";
  document.getElementById("heatmapChart").innerHTML = "";
  document.getElementById("barChart").innerHTML = "";
  document.getElementById("pieChart").innerHTML = "";
  document.getElementById("lineChart").innerHTML = "";
  document.getElementById("summaryModal").classList.add("open");

  try {
    const summary = await api.getSummary(state.month, state.year);
    renderSummary(summary);
  } catch (err) {
    document.getElementById("summaryOverview").innerHTML = `<div class="summary-empty">Failed to load charts.</div>`;
    toast(err.message, "error");
  }
}

function closeSummary() {
  document.getElementById("summaryModal").classList.remove("open");
}

function renderSummary(summary) {
  const monthly = summary.monthly_summary || {};
  const weekly = summary.weekly_summary || [];

  document.getElementById("summaryMonthLabel").textContent = summary.month_label;
  document.getElementById("summaryOverview").innerHTML = [
    { label: "Tasks", value: monthly.task_count || 0 },
    { label: "Done", value: monthly.completed_count || 0 },
    { label: "In Progress", value: monthly.in_progress_count || 0 },
    { label: "High Priority", value: monthly.high_priority_count || 0 },
    { label: "Overdue", value: monthly.overdue_count || 0 },
    { label: "Comments", value: monthly.comment_count || 0 },
    { label: "Top Column", value: monthly.top_column || "No tasks" },
    { label: "Top Priority", value: monthly.top_priority || "No tasks" },
  ].map(item => `
    <div class="summary-pill"><strong>${esc(item.label)}:</strong> ${esc(item.value)}</div>
  `).join("");

  document.getElementById("heatmapMeta").textContent = monthly.date_span || "";
  document.getElementById("heatmapChart").innerHTML = renderHeatmapChart(monthly.daily_activity || []);
  document.getElementById("barChart").innerHTML = renderBarChart(monthly.columns || []);
  document.getElementById("pieChart").innerHTML = renderPieChart(monthly.priorities || []);
  document.getElementById("lineChart").innerHTML = renderLineChart(weekly);
}

function doExportSummary() {
  window.location.href = `/api/export/summary/txt?month=${state.month}&year=${state.year}&label=${encodeURIComponent(summaryExportLabel())}`;
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
  document.getElementById("summaryBtn").addEventListener("click", openSummary);
  document.getElementById("exportBtn").addEventListener("click", openExport);
  document.getElementById("closeSummaryModal").addEventListener("click", closeSummary);
  document.getElementById("exportSummaryBtn").addEventListener("click", doExportSummary);
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

  /* Priority selector in add-task modal */
  document.querySelectorAll("#addPrioritySelector .priority-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#addPrioritySelector .priority-btn").forEach(b => {
        b.classList.remove("active"); b.style.cssText = "";
      });
      const color = PRIORITY_COLORS[btn.dataset.priority];
      btn.classList.add("active");
      btn.style.background  = color;
      btn.style.color       = "#fff";
      btn.style.borderColor = color;
    });
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
