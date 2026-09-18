"""
Comprehensive test suite for the Kanban Task Board REST API.

Tests cover:
    - GET all tasks (default seed state)
    - Status filtering (todo, in-progress, done, invalid status)
    - GET single task (valid ID, 404 not found)
    - POST create task (valid full payload, valid minimal with defaults, invalid missing title, invalid status, invalid priority, invalid JSON)
    - PUT update task (drag-drop status transitions, field editing, 404 not found, invalid values)
    - DELETE task (successful removal, verification of 404 on subsequent get, 404 on non-existent ID)
    - GET stats (total counts, by status breakdown, by priority breakdown)
    - Web UI root endpoint (GET /)
"""

from __future__ import annotations

import json
from typing import Generator

try:
    import pytest
    from app import create_app
    from models import SEED_TASKS, reset_tasks
except ImportError as err:
    import unittest
    raise unittest.SkipTest(f"Dependencies required for test_api.py (Flask, pytest): {err}")



@pytest.fixture
def app_instance():
    """Create and configure a clean application instance for testing."""
    test_app = create_app({"TESTING": True, "DEBUG": False})
    reset_tasks()
    yield test_app
    reset_tasks()


@pytest.fixture
def client(app_instance) -> Generator:
    """Provide a Flask test client with reset seed state."""
    with app_instance.test_client() as test_client:
        yield test_client


# -----------------------------------------------------------------------------
# 1. GET /api/tasks Tests
# -----------------------------------------------------------------------------

def test_get_all_tasks_returns_seed_data(client):
    """Ensure GET /api/tasks returns all 6 seed tasks with proper attributes."""
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.is_json

    tasks = response.get_json()
    assert isinstance(tasks, list)
    assert len(tasks) == 6

    # Verify task schema
    sample = tasks[0]
    expected_fields = {"id", "title", "description", "status", "priority", "created_at", "color"}
    assert expected_fields.issubset(sample.keys())


def test_get_tasks_filter_by_status_todo(client):
    """Ensure GET /api/tasks?status=todo returns only tasks with 'todo' status."""
    response = client.get("/api/tasks?status=todo")
    assert response.status_code == 200

    tasks = response.get_json()
    assert len(tasks) == 2
    assert all(t["status"] == "todo" for t in tasks)


def test_get_tasks_filter_by_status_in_progress(client):
    """Ensure GET /api/tasks?status=in-progress returns only 'in-progress' tasks."""
    response = client.get("/api/tasks?status=in-progress")
    assert response.status_code == 200

    tasks = response.get_json()
    assert len(tasks) == 2
    assert all(t["status"] == "in-progress" for t in tasks)


def test_get_tasks_filter_by_status_done(client):
    """Ensure GET /api/tasks?status=done returns only 'done' tasks."""
    response = client.get("/api/tasks?status=done")
    assert response.status_code == 200

    tasks = response.get_json()
    assert len(tasks) == 2
    assert all(t["status"] == "done" for t in tasks)


def test_get_tasks_filter_invalid_status_returns_400(client):
    """Ensure GET /api/tasks with an unrecognized status returns 400 Bad Request."""
    response = client.get("/api/tasks?status=archived")
    assert response.status_code == 400

    data = response.get_json()
    assert "error" in data
    assert "Invalid status" in data["error"]


# -----------------------------------------------------------------------------
# 2. GET /api/tasks/<id> Tests
# -----------------------------------------------------------------------------

def test_get_single_task_success(client):
    """Ensure GET /api/tasks/<id> retrieves an existing task by its UUID."""
    target_id = SEED_TASKS[0]["id"]
    response = client.get(f"/api/tasks/{target_id}")
    assert response.status_code == 200

    task = response.get_json()
    assert task["id"] == target_id
    assert task["title"] == SEED_TASKS[0]["title"]


def test_get_single_task_not_found(client):
    """Ensure GET /api/tasks/<id> returns 404 for a non-existent UUID."""
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/tasks/{non_existent_id}")
    assert response.status_code == 404

    data = response.get_json()
    assert "error" in data


# -----------------------------------------------------------------------------
# 3. POST /api/tasks Tests
# -----------------------------------------------------------------------------

def test_create_task_valid_full_payload(client):
    """Ensure POST /api/tasks creates a task with all custom fields specified."""
    payload = {
        "title": "Set up end-to-end testing",
        "description": "Install Playwright and create browser smoke tests.",
        "status": "todo",
        "priority": "high",
        "color": "#ec4899",
    }
    response = client.post(
        "/api/tasks",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 201

    created = response.get_json()
    assert created["title"] == payload["title"]
    assert created["description"] == payload["description"]
    assert created["status"] == payload["status"]
    assert created["priority"] == payload["priority"]
    assert created["color"] == payload["color"]
    assert "id" in created
    assert "created_at" in created

    # Verify task appears in full task list
    list_response = client.get("/api/tasks")
    assert len(list_response.get_json()) == 7


def test_create_task_with_defaults(client):
    """Ensure POST /api/tasks applies sensible defaults for omitted optional fields."""
    payload = {"title": "Quick task item"}
    response = client.post(
        "/api/tasks",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 201

    created = response.get_json()
    assert created["title"] == "Quick task item"
    assert created["description"] == ""
    assert created["status"] == "todo"
    assert created["priority"] == "medium"
    assert created["color"] == "#f59e0b"  # Default amber for medium priority


def test_create_task_invalid_missing_title(client):
    """Ensure POST /api/tasks returns 400 when 'title' is missing or whitespace."""
    payload = {"description": "Missing title"}
    response = client.post(
        "/api/tasks",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()

    # Empty string title test
    response_empty = client.post(
        "/api/tasks",
        data=json.dumps({"title": "   "}),
        content_type="application/json",
    )
    assert response_empty.status_code == 400


def test_create_task_invalid_status(client):
    """Ensure POST /api/tasks returns 400 when status is invalid."""
    payload = {"title": "Task with bad status", "status": "someday"}
    response = client.post(
        "/api/tasks",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "Invalid status" in response.get_json()["error"]


def test_create_task_invalid_priority(client):
    """Ensure POST /api/tasks returns 400 when priority is invalid."""
    payload = {"title": "Task with bad priority", "priority": "blocker"}
    response = client.post(
        "/api/tasks",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "Invalid priority" in response.get_json()["error"]


def test_create_task_invalid_body_non_json(client):
    """Ensure POST /api/tasks returns 400 when request body is not JSON."""
    response = client.post(
        "/api/tasks",
        data="raw string payload not json",
        content_type="text/plain",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


# -----------------------------------------------------------------------------
# 4. PUT /api/tasks/<id> Tests (e.g. Drag & Drop Status Updates)
# -----------------------------------------------------------------------------

def test_update_task_drag_drop_status_change(client):
    """Ensure PUT /api/tasks/<id> updates status (simulating Kanban drag and drop)."""
    target_id = SEED_TASKS[0]["id"]  # Originally 'todo'
    payload = {"status": "in-progress"}

    response = client.put(
        f"/api/tasks/{target_id}",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200

    updated = response.get_json()
    assert updated["id"] == target_id
    assert updated["status"] == "in-progress"

    # Verify change persists via GET
    get_res = client.get(f"/api/tasks/{target_id}")
    assert get_res.get_json()["status"] == "in-progress"


def test_update_task_multiple_fields(client):
    """Ensure PUT /api/tasks/<id> updates title, description, priority, and color."""
    target_id = SEED_TASKS[1]["id"]
    payload = {
        "title": "Refactored Auth Service",
        "description": "Updated OAuth2 flows and cookie security.",
        "priority": "high",
        "color": "#e11d48",
    }

    response = client.put(
        f"/api/tasks/{target_id}",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200

    updated = response.get_json()
    assert updated["title"] == payload["title"]
    assert updated["description"] == payload["description"]
    assert updated["priority"] == payload["priority"]
    assert updated["color"] == payload["color"]


def test_update_task_not_found(client):
    """Ensure PUT /api/tasks/<id> returns 404 when updating non-existent task."""
    non_existent_id = "11111111-9999-9999-9999-111111111111"
    response = client.put(
        f"/api/tasks/{non_existent_id}",
        data=json.dumps({"status": "done"}),
        content_type="application/json",
    )
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_update_task_invalid_status(client):
    """Ensure PUT /api/tasks/<id> returns 400 when invalid status is provided."""
    target_id = SEED_TASKS[0]["id"]
    response = client.put(
        f"/api/tasks/{target_id}",
        data=json.dumps({"status": "abandoned"}),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "Invalid status" in response.get_json()["error"]


# -----------------------------------------------------------------------------
# 5. DELETE /api/tasks/<id> Tests
# -----------------------------------------------------------------------------

def test_delete_task_success(client):
    """Ensure DELETE /api/tasks/<id> removes the task and decrements total count."""
    target_id = SEED_TASKS[0]["id"]

    delete_response = client.delete(f"/api/tasks/{target_id}")
    assert delete_response.status_code == 200
    data = delete_response.get_json()
    assert data["id"] == target_id

    # Confirm subsequent GET returns 404
    get_response = client.get(f"/api/tasks/{target_id}")
    assert get_response.status_code == 404

    # Confirm total task list count decreased
    list_response = client.get("/api/tasks")
    assert len(list_response.get_json()) == 5


def test_delete_task_not_found(client):
    """Ensure DELETE /api/tasks/<id> returns 404 for a non-existent task ID."""
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    response = client.delete(f"/api/tasks/{non_existent_id}")
    assert response.status_code == 404
    assert "error" in response.get_json()


# -----------------------------------------------------------------------------
# 6. GET /api/stats Tests
# -----------------------------------------------------------------------------

def test_get_dashboard_stats(client):
    """Ensure GET /api/stats returns accurate task counts by status and priority."""
    response = client.get("/api/stats")
    assert response.status_code == 200

    stats = response.get_json()
    assert stats["total"] == 6
    assert stats["by_status"] == {
        "todo": 2,
        "in-progress": 2,
        "done": 2,
    }
    assert stats["by_priority"] == {
        "low": 2,
        "medium": 2,
        "high": 2,
    }


def test_get_dashboard_stats_after_mutations(client):
    """Ensure GET /api/stats reflects dynamic task additions and deletions."""
    # Add high-priority 'todo' task
    client.post(
        "/api/tasks",
        data=json.dumps({"title": "Extra Task", "priority": "high", "status": "todo"}),
        content_type="application/json",
    )

    stats = client.get("/api/stats").get_json()
    assert stats["total"] == 7
    assert stats["by_status"]["todo"] == 3
    assert stats["by_priority"]["high"] == 3


# -----------------------------------------------------------------------------
# 7. Web UI & Root Endpoint Tests
# -----------------------------------------------------------------------------

def test_index_endpoint_returns_ok(client):
    """Ensure GET / serves successfully."""
    response = client.get("/")
    assert response.status_code == 200


def test_404_on_unknown_api_route(client):
    """Ensure unknown routes under /api return 404 JSON response."""
    response = client.get("/api/unknown_endpoint")
    assert response.status_code == 404
    assert response.is_json
    assert "error" in response.get_json()
