"""Task persistence, validation, and dashboard aggregation."""

from __future__ import annotations

import copy
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from pymongo import MongoClient
except ImportError:  # pragma: no cover
    MongoClient = None

VALID_STATUSES = ("todo", "in-progress", "done")
VALID_PRIORITIES = ("low", "medium", "high")
PRIORITY_COLORS = {"low": "#10b981", "medium": "#f59e0b", "high": "#ef4444"}
SEED_TASKS: List[Dict[str, Any]] = [
    {
        "id": "11111111-1111-4111-8111-111111111111",
        "title": "Design user onboarding flow",
        "description": "Create wireframes and user journey maps for the sign-up and initial walkthrough experience.",
        "status": "todo",
        "priority": "high",
        "created_at": "2026-09-18T09:00:00Z",
        "updated_at": "2026-09-18T09:00:00Z",
        "due_date": "2026-10-20",
        "tags": ["design", "product"],
        "assignee": "Maya",
        "color": "#ef4444",
    },
    {
        "id": "22222222-2222-4222-8222-222222222222",
        "title": "Implement authentication endpoints",
        "description": "Add JWT-based session management, token refresh mechanism, and rate limiting.",
        "status": "todo",
        "priority": "medium",
        "created_at": "2026-09-18T10:15:00Z",
        "updated_at": "2026-09-18T10:15:00Z",
        "due_date": "2026-10-24",
        "tags": ["backend", "security"],
        "assignee": "Noah",
        "color": "#f59e0b",
    },
    {
        "id": "33333333-3333-4333-8333-333333333333",
        "title": "Build Kanban board UI",
        "description": "Construct responsive drag-and-drop column layout with Tailwind CSS and HTML5 drag events.",
        "status": "in-progress",
        "priority": "high",
        "created_at": "2026-09-18T11:30:00Z",
        "updated_at": "2026-09-22T11:30:00Z",
        "due_date": "2026-10-18",
        "tags": ["frontend", "design"],
        "assignee": "Maya",
        "color": "#3b82f6",
    },
    {
        "id": "44444444-4444-4444-8444-444444444444",
        "title": "Develop REST API integration tests",
        "description": "Write comprehensive unit and integration tests covering CRUD operations and error codes.",
        "status": "in-progress",
        "priority": "medium",
        "created_at": "2026-09-18T13:00:00Z",
        "updated_at": "2026-09-23T13:00:00Z",
        "due_date": "2026-10-22",
        "tags": ["backend", "testing"],
        "assignee": "Ava",
        "color": "#8b5cf6",
    },
    {
        "id": "55555555-5555-4555-8555-555555555555",
        "title": "Initialize Git repository",
        "description": "Configure directory structure, branch protection rules, .gitignore, and environment templates.",
        "status": "done",
        "priority": "low",
        "created_at": "2026-09-17T14:20:00Z",
        "updated_at": "2026-09-20T14:20:00Z",
        "due_date": "2026-09-20",
        "tags": ["devops"],
        "assignee": "Noah",
        "color": "#10b981",
    },
    {
        "id": "66666666-6666-4666-8666-666666666666",
        "title": "Configure CI/CD automated pipeline",
        "description": "Set up GitHub Actions workflow for automated lint checks, pytest suites, and artifact builds.",
        "status": "done",
        "priority": "low",
        "created_at": "2026-09-17T16:45:00Z",
        "updated_at": "2026-09-21T16:45:00Z",
        "due_date": "2026-09-21",
        "tags": ["devops", "testing"],
        "assignee": "Ava",
        "color": "#06b6d4",
    },
]

_TASKS = {task["id"]: copy.deepcopy(task) for task in SEED_TASKS}
_mongo_collection = None
_mongo_uri = ""


def configure_store(uri: Optional[str] = None, database: Optional[str] = None) -> None:
    global _mongo_collection, _mongo_uri
    _mongo_uri = (uri or "").strip()
    _mongo_collection = None
    if _mongo_uri and MongoClient is not None:
        client = MongoClient(_mongo_uri, serverSelectionTimeoutMS=2500)
        db = database or os.environ.get("MONGO_DB_NAME", "taskflow")
        _mongo_collection = client[db]["tasks"]


def storage_info() -> Dict[str, Any]:
    return {
        "provider": "mongodb" if _mongo_collection is not None else "memory",
        "database_configured": bool(_mongo_uri),
    }


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_mongo_seed() -> None:
    if (
        _mongo_collection is not None
        and _mongo_collection.count_documents({}, limit=1) == 0
    ):
        _mongo_collection.insert_many(copy.deepcopy(SEED_TASKS))


def _mongo_call(action: Any, fallback: Any) -> Any:
    try:
        _ensure_mongo_seed()
        return action()
    except Exception:
        return fallback()


def _clean_task(task: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if task is None:
        return None
    task = copy.deepcopy(task)
    task.pop("_id", None)
    task.setdefault("description", "")
    task.setdefault("tags", [])
    task.setdefault("assignee", "")
    task.setdefault("due_date", "")
    task.setdefault("estimated_minutes", 30)
    task.setdefault("updated_at", task.get("created_at", _now()))
    return task


def reset_tasks() -> None:
    global _TASKS
    _TASKS = {task["id"]: copy.deepcopy(task) for task in SEED_TASKS}
    if _mongo_collection is not None:
        try:
            _mongo_collection.delete_many({})
            _mongo_collection.insert_many(copy.deepcopy(SEED_TASKS))
        except Exception:
            pass


def _validate(
    data: Dict[str, Any], existing: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    title = data.get("title", existing.get("title") if existing else None)
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Task 'title' is required and cannot be empty.")
    status = data.get("status", existing.get("status", "todo") if existing else "todo")
    priority = data.get(
        "priority", existing.get("priority", "medium") if existing else "medium"
    )
    if not isinstance(status, str) or status.strip().lower() not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}."
        )
    if (
        not isinstance(priority, str)
        or priority.strip().lower() not in VALID_PRIORITIES
    ):
        raise ValueError(
            f"Invalid priority '{priority}'. Must be one of: {', '.join(VALID_PRIORITIES)}."
        )
    tags = data.get("tags", existing.get("tags", []) if existing else [])
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    if not isinstance(tags, list):
        raise ValueError("Task 'tags' must be an array of labels.")
    tags = [str(tag).strip() for tag in tags if str(tag).strip()][:8]
    due_date = (
        data.get("due_date", existing.get("due_date", "") if existing else "") or ""
    )
    if due_date and (
        not isinstance(due_date, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", due_date)
    ):
        raise ValueError("Task 'due_date' must use YYYY-MM-DD format.")
    estimated_minutes = data.get(
        "estimated_minutes", existing.get("estimated_minutes", 30) if existing else 30
    )
    try:
        estimated_minutes = int(estimated_minutes)
    except (TypeError, ValueError) as error:
        raise ValueError("Task 'estimated_minutes' must be a whole number.") from error
    if estimated_minutes < 5 or estimated_minutes > 600:
        raise ValueError("Task 'estimated_minutes' must be between 5 and 600 minutes.")
    color = data.get("color", existing.get("color") if existing else None)
    if not isinstance(color, str) or not color.strip():
        color = PRIORITY_COLORS[priority.strip().lower()]
    return {
        "title": title.strip(),
        "description": str(
            data.get("description", existing.get("description", "") if existing else "")
            or ""
        ).strip(),
        "status": status.strip().lower(),
        "priority": priority.strip().lower(),
        "color": color.strip(),
        "tags": tags,
        "assignee": str(
            data.get("assignee", existing.get("assignee", "") if existing else "") or ""
        ).strip()[:80],
        "due_date": due_date,
        "estimated_minutes": estimated_minutes,
    }


def get_all_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if _mongo_collection is not None:

        def read() -> List[Dict[str, Any]]:
            query: Dict[str, Any] = {}
            if status:
                query["status"] = status.strip().lower()
            if priority:
                query["priority"] = priority.strip().lower()
            if search:
                query["$or"] = [
                    {"title": {"$regex": re.escape(search), "$options": "i"}},
                    {"description": {"$regex": re.escape(search), "$options": "i"}},
                    {"tags": {"$regex": re.escape(search), "$options": "i"}},
                ]
            return [
                _clean_task(task)
                for task in _mongo_collection.find(query).sort("created_at", 1)
            ]

        return _mongo_call(read, lambda: get_all_tasks_memory(status, priority, search))
    return get_all_tasks_memory(status, priority, search)


def get_all_tasks_memory(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    tasks = list(_TASKS.values())
    needle = search.strip().lower() if search else ""
    return copy.deepcopy(
        [
            _clean_task(task)
            for task in tasks
            if (not status or task["status"] == status.strip().lower())
            and (not priority or task["priority"] == priority.strip().lower())
            and (
                not needle
                or needle in task["title"].lower()
                or needle in task.get("description", "").lower()
                or any(needle in tag.lower() for tag in task.get("tags", []))
            )
        ]
    )


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    if _mongo_collection is not None:
        return _mongo_call(
            lambda: _clean_task(_mongo_collection.find_one({"id": task_id})),
            lambda: copy.deepcopy(_TASKS.get(task_id)),
        )
    return copy.deepcopy(_TASKS.get(task_id))


def create_task(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Task data must be a dictionary.")
    task = _validate(data)
    task.update({"id": str(uuid.uuid4()), "created_at": _now(), "updated_at": _now()})
    if _mongo_collection is not None:
        return _mongo_call(
            lambda: (
                _mongo_collection.insert_one(copy.deepcopy(task)),
                _clean_task(task),
            )[1],
            lambda: _create_memory(task),
        )
    return _create_memory(task)


def _create_memory(task: Dict[str, Any]) -> Dict[str, Any]:
    _TASKS[task["id"]] = copy.deepcopy(task)
    return copy.deepcopy(task)


def update_task(task_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    existing = get_task(task_id)
    if existing is None:
        return None
    task = _validate(data, existing)
    task["updated_at"] = _now()
    if "priority" in data and "color" not in data:
        task["color"] = PRIORITY_COLORS[task["priority"]]
    if _mongo_collection is not None:
        return _mongo_call(
            lambda: (
                _mongo_collection.update_one({"id": task_id}, {"$set": task}),
                _clean_task({**existing, **task}),
            )[1],
            lambda: _update_memory(task_id, task),
        )
    return _update_memory(task_id, task)


def _update_memory(task_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    _TASKS[task_id].update(copy.deepcopy(task))
    return copy.deepcopy(_TASKS[task_id])


def delete_task(task_id: str) -> bool:
    if _mongo_collection is not None:
        return _mongo_call(
            lambda: _mongo_collection.delete_one({"id": task_id}).deleted_count > 0,
            lambda: _delete_memory(task_id),
        )
    return _delete_memory(task_id)


def _delete_memory(task_id: str) -> bool:
    return _TASKS.pop(task_id, None) is not None


def get_stats() -> Dict[str, Any]:
    tasks = get_all_tasks()
    by_status = {status: 0 for status in VALID_STATUSES}
    by_priority = {priority: 0 for priority in VALID_PRIORITIES}
    overdue = 0
    today = datetime.now(timezone.utc).date().isoformat()
    for task in tasks:
        if task.get("status") in by_status:
            by_status[task["status"]] += 1
        if task.get("priority") in by_priority:
            by_priority[task["priority"]] += 1
        if (
            task.get("due_date")
            and task["due_date"] < today
            and task.get("status") != "done"
        ):
            overdue += 1
    return {
        "total": len(tasks),
        "by_status": by_status,
        "by_priority": by_priority,
        "overdue": overdue,
        "completion_rate": (
            round((by_status["done"] / len(tasks)) * 100) if tasks else 0
        ),
        "storage": storage_info(),
    }


configure_store(os.environ.get("MONGO_URI"), os.environ.get("MONGO_DB_NAME"))
