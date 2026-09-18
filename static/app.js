/**
 * @file app.js
 * @description Production-quality Vanilla JavaScript controller for TaskFlow Kanban Board.
 * Handles state management, REST API synchronization, drag-and-drop interactions,
 * modal dialogs, real-time metrics, theme persistence, and toast messaging.
 */

'use strict';

/**
 * @typedef {Object} Task
 * @property {string} id - Unique identifier (UUID).
 * @property {string} title - Task title.
 * @property {string} description - Task detailed description.
 * @property {'todo'|'in-progress'|'done'} status - Current task status.
 * @property {'low'|'medium'|'high'} priority - Task priority level.
 * @property {string} color - Hex color code for accent border.
 * @property {string} [created_at] - ISO timestamp string of task creation.
 */

/* ==========================================================================
   Application State
   ========================================================================== */
const state = {
  /** @type {Task[]} */
  tasks: [],
  /** @type {string|null} */
  activeDragTaskId: null,
  /** @type {string|null} */
  editingTaskId: null,
  /** @type {string|null} */
  taskPendingDeletionId: null,
  /** @type {'light'|'dark'} */
  theme: 'light',
};

/* ==========================================================================
   DOM Element Selectors Cache
   ========================================================================== */
const elements = {
  // Theme
  html: document.documentElement,
  themeToggle: document.getElementById('theme-toggle'),
  themeIcon: document.getElementById('theme-icon'),

  // Stats
  statTotal: document.getElementById('stat-total'),
  statTodo: document.getElementById('stat-todo'),
  statInProgress: document.getElementById('stat-in-progress'),
  statDone: document.getElementById('stat-done'),

  // Column Task Lists & Counts
  listTodo: document.getElementById('list-todo'),
  listInProgress: document.getElementById('list-in-progress'),
  listDone: document.getElementById('list-done'),
  countTodo: document.getElementById('count-todo'),
  countInProgress: document.getElementById('count-in-progress'),
  countDone: document.getElementById('count-done'),
  columns: document.querySelectorAll('.kanban-column'),

  // Modals & Forms
  btnAddTask: document.getElementById('btn-add-task'),
  taskModal: document.getElementById('task-modal'),
  modalTitle: document.getElementById('modal-title'),
  modalCloseBtn: document.getElementById('modal-close-btn'),
  btnCancel: document.getElementById('btn-cancel'),
  btnSubmitText: document.getElementById('btn-submit-text'),
  taskForm: document.getElementById('task-form'),
  inputTaskId: document.getElementById('task-id'),
  inputTaskTitle: document.getElementById('task-title'),
  inputTaskDesc: document.getElementById('task-desc'),
  selectTaskStatus: document.getElementById('task-status'),
  selectTaskPriority: document.getElementById('task-priority'),
  inputTaskColor: document.getElementById('task-color'),
  labelColorHex: document.getElementById('color-hex-label'),
  colorSwatches: document.getElementById('color-swatches'),
  titleError: document.getElementById('title-error'),

  // Delete Confirmation Modal
  deleteModal: document.getElementById('delete-modal'),
  deleteModalCloseBtn: document.getElementById('delete-modal-close-btn'),
  btnDeleteCancel: document.getElementById('btn-delete-cancel'),
  btnDeleteConfirm: document.getElementById('btn-delete-confirm'),
  deleteTaskTitle: document.getElementById('delete-task-title'),

  // Toasts
  toastContainer: document.getElementById('toast-container'),
};

/* ==========================================================================
   Utility Helpers
   ========================================================================== */

/**
 * Escapes unsafe characters for HTML injection prevention.
 * @param {string} str - Raw string.
 * @returns {string} Sanitized string safe for HTML insertion.
 */
function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Normalizes various status formats into standard canonical strings: 'todo', 'in-progress', 'done'.
 * @param {string} status - Raw status string.
 * @returns {'todo'|'in-progress'|'done'} Canonical status.
 */
function normalizeStatus(status) {
  if (!status) return 'todo';
  const clean = String(status).toLowerCase().trim().replace(/_/g, '-').replace(/\s+/g, '-');
  if (clean === 'in-progress' || clean === 'inprogress') {
    return 'in-progress';
  }
  if (clean === 'done') {
    return 'done';
  }
  return 'todo';
}

/**
 * Formats a canonical status into human-readable text.
 * @param {'todo'|'in-progress'|'done'} status 
 * @returns {string} Display string.
 */
function formatStatusLabel(status) {
  const norm = normalizeStatus(status);
  switch (norm) {
    case 'in-progress':
      return 'In Progress';
    case 'done':
      return 'Done';
    case 'todo':
    default:
      return 'To Do';
  }
}

/* ==========================================================================
   Toast Notification System
   ========================================================================== */

/**
 * Displays a toast notification sliding in from top-right.
 * @param {string} message - Text to show in toast.
 * @param {'success'|'error'|'info'} [type='info'] - Severity variant.
 * @param {number} [duration=3000] - Duration in milliseconds before auto-dismissal.
 */
function showToast(message, type = 'info', duration = 3000) {
  if (!elements.toastContainer) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.setAttribute('role', 'alert');

  let icon = 'ℹ️';
  if (type === 'success') icon = '✅';
  if (type === 'error') icon = '⚠️';

  toast.innerHTML = `
    <div class="toast-content">
      <span class="toast-icon">${icon}</span>
      <span class="toast-message">${escapeHtml(message)}</span>
    </div>
    <button class="toast-close" aria-label="Dismiss">&times;</button>
  `;

  const removeToast = () => {
    toast.classList.add('toast-leave');
    toast.addEventListener('transitionend', () => {
      if (toast.parentElement) {
        toast.parentElement.removeChild(toast);
      }
    }, { once: true });
  };

  // Close button trigger
  const closeBtn = toast.querySelector('.toast-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', removeToast);
  }

  elements.toastContainer.appendChild(toast);

  // Auto-dismiss timeout
  if (duration > 0) {
    setTimeout(removeToast, duration);
  }
}

/* ==========================================================================
   REST API Communication Layer
   ========================================================================== */

const api = {
  /**
   * Fetch all tasks from server.
   * @returns {Promise<Task[]>}
   */
  async getTasks() {
    const res = await fetch('/api/tasks');
    if (!res.ok) {
      throw new Error(`Failed to load tasks: ${res.statusText}`);
    }
    const data = await res.json();
    return Array.isArray(data) ? data : (data.tasks || []);
  },

  /**
   * Create a new task.
   * @param {Partial<Task>} taskData 
   * @returns {Promise<Task>}
   */
  async createTask(taskData) {
    const res = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(taskData),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || `Error creating task (${res.status})`);
    }
    return data;
  },

  /**
   * Update an existing task.
   * @param {string} taskId 
   * @param {Partial<Task>} taskData 
   * @returns {Promise<Task>}
   */
  async updateTask(taskId, taskData) {
    const res = await fetch(`/api/tasks/${encodeURIComponent(taskId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(taskData),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || `Error updating task (${res.status})`);
    }
    return data;
  },

  /**
   * Delete a task by ID.
   * @param {string} taskId 
   * @returns {Promise<void>}
   */
  async deleteTask(taskId) {
    const res = await fetch(`/api/tasks/${encodeURIComponent(taskId)}`, {
      method: 'DELETE',
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || `Error deleting task (${res.status})`);
    }
  },
};

/* ==========================================================================
   Theme Management
   ========================================================================== */

/**
 * Initializes and binds the theme toggle functionality.
 */
function initTheme() {
  const savedTheme = localStorage.getItem('taskflow-theme');
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  const initialTheme = savedTheme || (prefersDark ? 'dark' : 'light');
  applyTheme(initialTheme);

  if (elements.themeToggle) {
    elements.themeToggle.addEventListener('click', () => {
      const newTheme = state.theme === 'dark' ? 'light' : 'dark';
      applyTheme(newTheme);
      localStorage.setItem('taskflow-theme', newTheme);
      showToast(`Switched to ${newTheme} mode`, 'info', 2000);
    });
  }
}

/**
 * Applies the selected theme to DOM and updates icon.
 * @param {'light'|'dark'} theme 
 */
function applyTheme(theme) {
  state.theme = theme;
  elements.html.setAttribute('data-theme', theme);
  if (elements.themeIcon) {
    elements.themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
  }
}

/* ==========================================================================
   Board Rendering & DOM Operations
   ========================================================================== */

/**
 * Renders the entire Kanban board based on current state.tasks.
 */
function renderBoard() {
  // Clear lists
  elements.listTodo.innerHTML = '';
  elements.listInProgress.innerHTML = '';
  elements.listDone.innerHTML = '';

  const columnsMap = {
    'todo': elements.listTodo,
    'in-progress': elements.listInProgress,
    'done': elements.listDone,
  };

  // Group tasks
  const grouped = {
    'todo': [],
    'in-progress': [],
    'done': [],
  };

  state.tasks.forEach((task) => {
    const norm = normalizeStatus(task.status);
    if (grouped[norm]) {
      grouped[norm].push(task);
    } else {
      grouped['todo'].push(task);
    }
  });

  // Render cards into respective columns
  Object.keys(grouped).forEach((statusKey) => {
    const container = columnsMap[statusKey];
    const tasksInCol = grouped[statusKey];

    if (tasksInCol.length === 0) {
      container.innerHTML = `
        <div class="empty-column-placeholder">
          <span class="empty-placeholder-icon">📥</span>
          <span>No tasks here yet</span>
        </div>
      `;
    } else {
      tasksInCol.forEach((task) => {
        const cardNode = createTaskCardElement(task);
        container.appendChild(cardNode);
      });
    }
  });

  updateStats();
}

/**
 * Generates an interactive DOM Element for a task card.
 * @param {Task} task 
 * @returns {HTMLElement}
 */
function createTaskCardElement(task) {
  const card = document.createElement('article');
  card.className = 'task-card';
  card.id = `task-card-${task.id}`;
  card.draggable = true;
  card.dataset.taskId = task.id;
  card.dataset.status = normalizeStatus(task.status);

  // Apply custom left border accent color
  const accentColor = task.color || '#6366f1';
  card.style.borderLeftColor = accentColor;
  card.style.setProperty('--task-color', accentColor);

  const priority = (task.priority || 'medium').toLowerCase();
  const priorityBadgeClass = `badge-${priority}`;

  card.innerHTML = `
    <div class="card-header">
      <h3 class="card-title">${escapeHtml(task.title)}</h3>
      <div class="card-actions">
        <button class="card-action-btn edit-btn" title="Edit Task" aria-label="Edit Task">
          <svg viewBox="0 0 20 20" fill="currentColor" width="15" height="15">
            <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
          </svg>
        </button>
        <button class="card-action-btn delete-btn" title="Delete Task" aria-label="Delete Task">
          <svg viewBox="0 0 20 20" fill="currentColor" width="15" height="15">
            <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>
    ${
      task.description
        ? `<p class="card-description">${escapeHtml(task.description)}</p>`
        : ''
    }
    <div class="card-footer">
      <div class="card-meta">
        <span class="badge-priority ${priorityBadgeClass}">${escapeHtml(priority)}</span>
      </div>
    </div>
  `;

  // Attach Drag Event Handlers
  card.addEventListener('dragstart', handleDragStart);
  card.addEventListener('dragend', handleDragEnd);

  // Attach Button Handlers
  const editBtn = card.querySelector('.edit-btn');
  if (editBtn) {
    editBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      openEditTaskModal(task.id);
    });
  }

  const deleteBtn = card.querySelector('.delete-btn');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      promptDeleteTask(task.id);
    });
  }

  // Double clicking card opens edit modal
  card.addEventListener('dblclick', () => {
    openEditTaskModal(task.id);
  });

  return card;
}

/**
 * Updates stats summary bar and individual column counter badges.
 */
function updateStats() {
  const total = state.tasks.length;
  let todoCount = 0;
  let inProgressCount = 0;
  let doneCount = 0;

  state.tasks.forEach((task) => {
    const s = normalizeStatus(task.status);
    if (s === 'todo') todoCount++;
    else if (s === 'in-progress') inProgressCount++;
    else if (s === 'done') doneCount++;
  });

  if (elements.statTotal) elements.statTotal.textContent = String(total);
  if (elements.statTodo) elements.statTodo.textContent = String(todoCount);
  if (elements.statInProgress) elements.statInProgress.textContent = String(inProgressCount);
  if (elements.statDone) elements.statDone.textContent = String(doneCount);

  if (elements.countTodo) elements.countTodo.textContent = String(todoCount);
  if (elements.countInProgress) elements.countInProgress.textContent = String(inProgressCount);
  if (elements.countDone) elements.countDone.textContent = String(doneCount);
}

/* ==========================================================================
   HTML5 Drag and Drop Handlers
   ========================================================================== */

/**
 * Handles card dragstart event.
 * @param {DragEvent} e 
 */
function handleDragStart(e) {
  const card = e.currentTarget;
  state.activeDragTaskId = card.dataset.taskId;
  
  if (e.dataTransfer) {
    e.dataTransfer.setData('text/plain', card.dataset.taskId);
    e.dataTransfer.effectAllowed = 'move';
  }

  // Slight timeout so the dragged ghost image maintains full opacity before class applies
  setTimeout(() => {
    card.classList.add('is-dragging');
  }, 0);
}

/**
 * Handles card dragend event.
 * @param {DragEvent} e 
 */
function handleDragEnd(e) {
  const card = e.currentTarget;
  card.classList.remove('is-dragging');
  state.activeDragTaskId = null;

  // Clean up any remaining hover classes
  elements.columns.forEach((col) => {
    col.classList.remove('drag-over');
  });
}

/**
 * Initializes drop zone handlers on all Kanban columns.
 */
function initDragAndDrop() {
  elements.columns.forEach((column) => {
    const targetStatus = column.dataset.status;

    column.addEventListener('dragover', (e) => {
      e.preventDefault();
      if (e.dataTransfer) {
        e.dataTransfer.dropEffect = 'move';
      }
      column.classList.add('drag-over');
    });

    column.addEventListener('dragenter', (e) => {
      e.preventDefault();
      column.classList.add('drag-over');
    });

    column.addEventListener('dragleave', (e) => {
      // Ensure we only clear if leaving the column itself, not entering a child element
      if (!column.contains(e.relatedTarget)) {
        column.classList.remove('drag-over');
      }
    });

    column.addEventListener('drop', async (e) => {
      e.preventDefault();
      column.classList.remove('drag-over');

      const taskId = e.dataTransfer ? e.dataTransfer.getData('text/plain') : state.activeDragTaskId;
      if (!taskId) return;

      const taskIndex = state.tasks.findIndex((t) => String(t.id) === String(taskId));
      if (taskIndex === -1) return;

      const task = state.tasks[taskIndex];
      const previousStatus = normalizeStatus(task.status);
      const newStatus = normalizeStatus(targetStatus);

      // If dropped in the same column, do nothing
      if (previousStatus === newStatus) return;

      // Optimistic UI Update
      task.status = newStatus;
      renderBoard();

      try {
        await api.updateTask(task.id, {
          title: task.title,
          description: task.description || '',
          status: newStatus,
          priority: task.priority || 'medium',
          color: task.color || '#6366f1',
        });
        showToast(`Moved "${task.title}" to ${formatStatusLabel(newStatus)}`, 'success', 2500);
      } catch (err) {
        // Rollback on failure
        task.status = previousStatus;
        renderBoard();
        showToast(`Failed to move task: ${err.message}`, 'error', 4000);
      }
    });
  });
}

/* ==========================================================================
   Modal Dialog Management (Add / Edit / Delete)
   ========================================================================== */

/**
 * Opens modal configured for creating a new task.
 * @param {'todo'|'in-progress'|'done'} [defaultStatus='todo'] 
 */
function openCreateTaskModal(defaultStatus = 'todo') {
  state.editingTaskId = null;
  elements.modalTitle.textContent = 'Add New Task';
  elements.btnSubmitText.textContent = 'Create Task';
  elements.taskForm.reset();
  elements.inputTaskId.value = '';
  elements.selectTaskStatus.value = normalizeStatus(defaultStatus);
  elements.selectTaskPriority.value = 'medium';

  // Default color: Indigo
  setColorPickerValue('#6366f1');
  clearFormErrors();

  elements.taskModal.classList.remove('hidden');
  setTimeout(() => elements.inputTaskTitle.focus(), 100);
}

/**
 * Opens modal configured for editing an existing task.
 * @param {string} taskId 
 */
function openEditTaskModal(taskId) {
  const task = state.tasks.find((t) => String(t.id) === String(taskId));
  if (!task) return;

  state.editingTaskId = task.id;
  elements.modalTitle.textContent = 'Edit Task';
  elements.btnSubmitText.textContent = 'Save Changes';
  clearFormErrors();

  elements.inputTaskId.value = task.id;
  elements.inputTaskTitle.value = task.title || '';
  elements.inputTaskDesc.value = task.description || '';
  elements.selectTaskStatus.value = normalizeStatus(task.status);
  elements.selectTaskPriority.value = (task.priority || 'medium').toLowerCase();

  setColorPickerValue(task.color || '#6366f1');

  elements.taskModal.classList.remove('hidden');
  setTimeout(() => elements.inputTaskTitle.focus(), 100);
}

/**
 * Closes the Add/Edit task modal dialog.
 */
function closeTaskModal() {
  elements.taskModal.classList.add('hidden');
  state.editingTaskId = null;
  clearFormErrors();
}

/**
 * Clears form validation errors.
 */
function clearFormErrors() {
  if (elements.titleError) {
    elements.titleError.textContent = '';
  }
}

/**
 * Sets color picker and swatches state.
 * @param {string} hex 
 */
function setColorPickerValue(hex) {
  const cleanHex = hex.toLowerCase();
  elements.inputTaskColor.value = hex;
  elements.labelColorHex.textContent = hex.toUpperCase();

  const swatches = elements.colorSwatches.querySelectorAll('.color-swatch');
  swatches.forEach((swatch) => {
    if (swatch.dataset.color.toLowerCase() === cleanHex) {
      swatch.classList.add('active');
    } else {
      swatch.classList.remove('active');
    }
  });
}

/**
 * Handles submission of Add/Edit task form.
 * @param {SubmitEvent} e 
 */
async function handleTaskFormSubmit(e) {
  e.preventDefault();

  const title = elements.inputTaskTitle.value.trim();
  if (!title) {
    if (elements.titleError) elements.titleError.textContent = 'Task title is required.';
    elements.inputTaskTitle.focus();
    return;
  }

  const description = elements.inputTaskDesc.value.trim();
  const status = normalizeStatus(elements.selectTaskStatus.value);
  const priority = elements.selectTaskPriority.value.toLowerCase();
  const color = elements.inputTaskColor.value;

  const payload = {
    title,
    description,
    status,
    priority,
    color,
  };

  const isEditing = Boolean(state.editingTaskId);

  try {
    if (isEditing) {
      const updated = await api.updateTask(state.editingTaskId, payload);
      const index = state.tasks.findIndex((t) => String(t.id) === String(state.editingTaskId));
      if (index !== -1) {
        state.tasks[index] = updated;
      }
      showToast('Task updated successfully!', 'success');
    } else {
      const created = await api.createTask(payload);
      state.tasks.push(created);
      showToast('Task created successfully!', 'success');
    }

    closeTaskModal();
    renderBoard();
  } catch (err) {
    showToast(err.message || 'Operation failed', 'error');
  }
}

/**
 * Prompts confirmation before task deletion.
 * @param {string} taskId 
 */
function promptDeleteTask(taskId) {
  const task = state.tasks.find((t) => String(t.id) === String(taskId));
  if (!task) return;

  state.taskPendingDeletionId = task.id;
  if (elements.deleteTaskTitle) {
    elements.deleteTaskTitle.textContent = `"${task.title}"`;
  }
  elements.deleteModal.classList.remove('hidden');
}

/**
 * Closes delete confirmation modal.
 */
function closeDeleteModal() {
  elements.deleteModal.classList.add('hidden');
  state.taskPendingDeletionId = null;
}

/**
 * Confirms deletion of the pending task.
 */
async function confirmDeleteTask() {
  if (!state.taskPendingDeletionId) return;
  const taskId = state.taskPendingDeletionId;
  const task = state.tasks.find((t) => String(t.id) === String(taskId));
  const title = task ? task.title : 'Task';

  try {
    await api.deleteTask(taskId);
    state.tasks = state.tasks.filter((t) => String(t.id) !== String(taskId));
    closeDeleteModal();
    renderBoard();
    showToast(`Deleted "${title}"`, 'info');
  } catch (err) {
    showToast(err.message || 'Failed to delete task', 'error');
  }
}

/* ==========================================================================
   Event Binding & Initialization
   ========================================================================== */

/**
 * Attaches click and change listeners to interactive DOM elements.
 */
function bindEvents() {
  // Add Task Button in Header
  if (elements.btnAddTask) {
    elements.btnAddTask.addEventListener('click', () => openCreateTaskModal('todo'));
  }

  // Column header Quick Add buttons (+)
  const colAddButtons = document.querySelectorAll('.btn-column-add');
  colAddButtons.forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const status = e.currentTarget.dataset.status || 'todo';
      openCreateTaskModal(status);
    });
  });

  // Modal Close & Cancel
  if (elements.modalCloseBtn) {
    elements.modalCloseBtn.addEventListener('click', closeTaskModal);
  }
  if (elements.btnCancel) {
    elements.btnCancel.addEventListener('click', closeTaskModal);
  }

  // Close modal when clicking on backdrop
  if (elements.taskModal) {
    elements.taskModal.addEventListener('click', (e) => {
      if (e.target === elements.taskModal) {
        closeTaskModal();
      }
    });
  }

  // Form Submit
  if (elements.taskForm) {
    elements.taskForm.addEventListener('submit', handleTaskFormSubmit);
  }

  // Delete Modal Buttons
  if (elements.deleteModalCloseBtn) {
    elements.deleteModalCloseBtn.addEventListener('click', closeDeleteModal);
  }
  if (elements.btnDeleteCancel) {
    elements.btnDeleteCancel.addEventListener('click', closeDeleteModal);
  }
  if (elements.btnDeleteConfirm) {
    elements.btnDeleteConfirm.addEventListener('click', confirmDeleteTask);
  }
  if (elements.deleteModal) {
    elements.deleteModal.addEventListener('click', (e) => {
      if (e.target === elements.deleteModal) {
        closeDeleteModal();
      }
    });
  }

  // Color Swatches Selection
  if (elements.colorSwatches) {
    elements.colorSwatches.addEventListener('click', (e) => {
      const swatch = e.target.closest('.color-swatch');
      if (swatch) {
        const color = swatch.dataset.color;
        setColorPickerValue(color);
      }
    });
  }

  // Custom Color Input Change
  if (elements.inputTaskColor) {
    elements.inputTaskColor.addEventListener('input', (e) => {
      setColorPickerValue(e.target.value);
    });
  }

  // Keyboard Shortcuts: Escape key closes modals
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (!elements.taskModal.classList.contains('hidden')) {
        closeTaskModal();
      }
      if (!elements.deleteModal.classList.contains('hidden')) {
        closeDeleteModal();
      }
    }
  });
}

/**
 * Initializes the entire application: theme, events, drag-and-drop, and initial task fetch.
 */
async function initApp() {
  initTheme();
  bindEvents();
  initDragAndDrop();

  try {
    const tasks = await api.getTasks();
    state.tasks = tasks;
    renderBoard();
  } catch (err) {
    console.error('Initial tasks loading failed:', err);
    showToast('Failed to load tasks from server', 'error', 5000);
    renderBoard();
  }
}

// Kick off initialization on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}
