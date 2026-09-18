"""
In-memory data store for the Kanban Task Board application.

Provides lightweight model management without external database dependencies.
Includes data models, seed tasks, validation rules, and CRUD operations.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

# Valid enumeration values for task attributes
VALID_STATUSES = ("todo", "in-progress", "done")
VALID_PRIORITIES = ("low", "medium", "high")

# Default color mapping for priorities if not custom specified
PRIORITY_COLORS: Dict[str, str] = {
    "low": "#10b981",       # Emerald green
    "medium": "#f59e0b",    # Amber / Orange
    "high": "#ef4444",      # Crimson red
}

# Initial seed data with 6 sample tasks spread across statuses
SEED_TASKS: List[Dict[str, Any]] = [
    {
        "id": "11111111-1111-4111-8111-111111111111",
        "title": "Design user onboarding flow",
        "description": "Create wireframes and user journey maps for the sign-up and initial walkthrough experience.",
        "status": "todo",
        "priority": "high",
        "created_at": "2026-09-18T09:00:00Z",
        "color": "#ef4444",
    },
    {
        "id": "22222222-2222-4222-8222-222222222222",
        "title": "Implement authentication endpoints",
        "description": "Add JWT-based session management, token refresh mechanism, and rate limiting.",
        "status": "todo",
        "priority": "medium",
        "created_at": "2026-09-18T10:15:00Z",
        "color": "#f59e0b",
    },
    {
        "id": "33333333-3333-4333-8333-333333333333",
        "title": "Build Kanban board UI",
        "description": "Construct responsive drag-and-drop column layout with Tailwind CSS and HTML5 drag events.",
        "status": "in-progress",
        "priority": "high",
        "created_at": "2026-09-18T11:30:00Z",
        "color": "#3b82f6",
    },
    {
        "id": "44444444-4444-4444-8444-444444444444",
        "title": "Develop REST API integration tests",
        "description": "Write comprehensive unit and integration tests covering CRUD operations and error codes.",
        "status": "in-progress",
        "priority": "medium",
        "created_at": "2026-09-18T13:00:00Z",
        "color": "#8b5cf6",
    },
    {
        "id": "55555555-5555-4555-8555-555555555555",
        "title": "Initialize Git repository",
        "description": "Configure directory structure, branch protection rules, .gitignore, and environment templates.",
        "status": "done",
        "priority": "low",
        "created_at": "2026-09-17T14:20:00Z",
        "color": "#10b981",
    },
    {
        "id": "66666666-6666-4666-8666-666666666666",
        "title": "Configure CI/CD automated pipeline",
        "description": "Set up GitHub Actions workflow for automated lint checks, pytest suites, and artifact builds.",
        "status": "done",
        "priority": "low",
        "created_at": "2026-09-17T16:45:00Z",
        "color": "#06b6d4",
    },
]

# Internal in-memory store: Dict[task_id, task_dict]
_TASKS: Dict[str, Dict[str, Any]] = {task["id"]: copy.deepcopy(task) for task in SEED_TASKS}


def reset_tasks() -> None:
    """Reset the in-memory task repository to the original 6 seed tasks.

    Useful for isolating test suites and refreshing demo environments.
    """
    global _TASKS
    _TASKS = {task["id"]: copy.deepcopy(task) for task in SEED_TASKS}


def get_all_tasks(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all tasks from the store, optionally filtered by status.

    Args:
        status: Optional status string ('todo', 'in-progress', or 'done') to filter by.

    Returns:
        A list of task dictionaries ordered by creation time.
    """
    tasks = list(_TASKS.values())
    if status is not None:
        status_clean = status.strip().lower()
        tasks = [t for t in tasks if t["status"] == status_clean]

    # Return deep copies so external modifications do not affect store directly
    return copy.deepcopy(tasks)


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single task by its unique identifier.

    Args:
        task_id: The UUID string of the task.

    Returns:
        The task dictionary if found, otherwise None.
    """
    task = _TASKS.get(task_id)
    if task is None:
        return None
    return copy.deepcopy(task)


def create_task(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create and persist a new task in the store.

    Args:
        data: Dictionary containing task attributes:
            - title (required, non-empty string)
            - description (optional string, defaults to '')
            - status (optional string, defaults to 'todo')
            - priority (optional string, defaults to 'medium')
            - color (optional hex string, defaults to priority default)

    Returns:
        The newly created task dictionary including generated id and created_at.

    Raises:
        ValueError: If title is missing/empty, or if status/priority values are invalid.
    """
    if not isinstance(data, dict):
        raise ValueError("Task data must be a dictionary.")

    title = data.get("title")
    if not title or not isinstance(title, str) or not title.strip():
        raise ValueError("Task 'title' is required and cannot be empty.")

    status = data.get("status", "todo")
    if not isinstance(status, str) or status.strip().lower() not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}."
        )
    status = status.strip().lower()

    priority = data.get("priority", "medium")
    if not isinstance(priority, str) or priority.strip().lower() not in VALID_PRIORITIES:
        raise ValueError(
            f"Invalid priority '{priority}'. Must be one of: {', '.join(VALID_PRIORITIES)}."
        )
    priority = priority.strip().lower()

    description = data.get("description", "")
    if description is None:
        description = ""
    elif not isinstance(description, str):
        description = str(description)
    description = description.strip()

    # Determine card accent color
    color = data.get("color")
    if not color or not isinstance(color, str) or not color.strip():
        color = PRIORITY_COLORS.get(priority, "#3b82f6")
    else:
        color = color.strip()

    task_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    new_task: Dict[str, Any] = {
        "id": task_id,
        "title": title.strip(),
        "description": description,
        "status": status,
        "priority": priority,
        "created_at": created_at,
        "color": color,
    }

    _TASKS[task_id] = new_task
    return copy.deepcopy(new_task)


def update_task(task_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update attributes of an existing task.

    Args:
        task_id: The UUID string of the task to update.
        data: Dictionary of fields to update (title, description, status, priority, color).

    Returns:
        The updated task dictionary if found, otherwise None.

    Raises:
        ValueError: If any provided field value is invalid.
    """
    if not isinstance(data, dict):
        raise ValueError("Update data must be a dictionary.")

    task = _TASKS.get(task_id)
    if task is None:
        return None

    # Validate title if present
    if "title" in data:
        title = data["title"]
        if not title or not isinstance(title, str) or not title.strip():
            raise ValueError("Task 'title' cannot be empty.")
        task["title"] = title.strip()

    # Validate status if present
    if "status" in data:
        status = data["status"]
        if not isinstance(status, str) or status.strip().lower() not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}."
            )
        task["status"] = status.strip().lower()

    # Validate priority if present
    if "priority" in data:
        priority = data["priority"]
        if not isinstance(priority, str) or priority.strip().lower() not in VALID_PRIORITIES:
            raise ValueError(
                f"Invalid priority '{priority}'. Must be one of: {', '.join(VALID_PRIORITIES)}."
            )
        task["priority"] = priority.strip().lower()
        # If color wasn't explicitly provided, sync color with new priority
        if "color" not in data:
            task["color"] = PRIORITY_COLORS.get(task["priority"], task.get("color", "#3b82f6"))

    # Update description if present
    if "description" in data:
        desc = data["description"]
        task["description"] = "" if desc is None else str(desc).strip()

    # Update color if present
    if "color" in data:
        col = data["color"]
        if col and isinstance(col, str) and col.strip():
            task["color"] = col.strip()

    return copy.deepcopy(task)


def delete_task(task_id: str) -> bool:
    """Delete a task from the in-memory store by ID.

    Args:
        task_id: The UUID string of the task to delete.

    Returns:
        True if the task was found and deleted, False otherwise.
    """
    if task_id in _TASKS:
        del _TASKS[task_id]
        return True
    return False


def get_stats() -> Dict[str, Any]:
    """Calculate and return task metrics aggregated by status and priority.

    Returns:
        Dictionary containing total task count, counts by status, and counts by priority.
    """
    tasks = list(_TASKS.values())
    total = len(tasks)

    by_status: Dict[str, int] = {st: 0 for st in VALID_STATUSES}
    by_priority: Dict[str, int] = {pr: 0 for pr in VALID_PRIORITIES}

    for task in tasks:
        st = task.get("status", "")
        pr = task.get("priority", "")
        if st in by_status:
            by_status[st] += 1
        if pr in by_priority:
            by_priority[pr] += 1

    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
    }
