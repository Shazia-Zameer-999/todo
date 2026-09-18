"""
Unit tests for models.py using Python standard library unittest.

Ensures core model logic, invariants, seed state, validation, and CRUD operations
can be verified independently of third-party testing frameworks.
"""

from __future__ import annotations

import unittest
from models import (
    SEED_TASKS,
    VALID_PRIORITIES,
    VALID_STATUSES,
    create_task,
    delete_task,
    get_all_tasks,
    get_stats,
    get_task,
    reset_tasks,
    update_task,
)


class TestTaskModels(unittest.TestCase):
    """Test suite for task store operations and validations."""

    def setUp(self) -> None:
        """Reset the in-memory task database before each test."""
        reset_tasks()

    def tearDown(self) -> None:
        """Reset after each test."""
        reset_tasks()

    def test_seed_tasks_loaded(self) -> None:
        """Verify the 6 initial seed tasks are correctly loaded."""
        tasks = get_all_tasks()
        self.assertEqual(len(tasks), 6)

        statuses = [t["status"] for t in tasks]
        self.assertEqual(statuses.count("todo"), 2)
        self.assertEqual(statuses.count("in-progress"), 2)
        self.assertEqual(statuses.count("done"), 2)

    def test_get_task_by_id(self) -> None:
        """Verify retrieving an individual task by its ID."""
        first_seed = SEED_TASKS[0]
        task = get_task(first_seed["id"])
        self.assertIsNotNone(task)
        self.assertEqual(task["title"], first_seed["title"])
        self.assertEqual(task["status"], first_seed["status"])

    def test_get_task_not_found(self) -> None:
        """Verify get_task returns None for unknown ID."""
        task = get_task("non-existent-uuid-12345")
        self.assertIsNone(task)

    def test_filter_tasks_by_status(self) -> None:
        """Verify status-based task filtering."""
        todos = get_all_tasks(status="todo")
        self.assertEqual(len(todos), 2)
        for t in todos:
            self.assertEqual(t["status"], "todo")

        in_progress = get_all_tasks(status="in-progress")
        self.assertEqual(len(in_progress), 2)
        for t in in_progress:
            self.assertEqual(t["status"], "in-progress")

        done = get_all_tasks(status="done")
        self.assertEqual(len(done), 2)
        for t in done:
            self.assertEqual(t["status"], "done")

    def test_create_task_success(self) -> None:
        """Verify creating a new task with full and partial attributes."""
        payload = {
            "title": "Write Architecture Documentation",
            "description": "Outline high-level system diagrams.",
            "status": "todo",
            "priority": "high",
            "color": "#e11d48",
        }
        created = create_task(payload)
        self.assertIn("id", created)
        self.assertIn("created_at", created)
        self.assertEqual(created["title"], payload["title"])
        self.assertEqual(created["priority"], "high")
        self.assertEqual(created["color"], "#e11d48")

        # Verify task is now present in the store
        retrieved = get_task(created["id"])
        self.assertIsNotNone(retrieved)
        self.assertEqual(len(get_all_tasks()), 7)

    def test_create_task_validation_errors(self) -> None:
        """Verify validation errors when required fields are invalid."""
        # Missing title
        with self.assertRaises(ValueError):
            create_task({"title": "", "status": "todo"})

        # Whitespace title
        with self.assertRaises(ValueError):
            create_task({"title": "   "})

        # Invalid status
        with self.assertRaises(ValueError):
            create_task({"title": "Valid Title", "status": "invalid_status"})

        # Invalid priority
        with self.assertRaises(ValueError):
            create_task({"title": "Valid Title", "priority": "super_urgent"})

    def test_update_task_success(self) -> None:
        """Verify updating task status, priority, title, and description."""
        target_id = SEED_TASKS[0]["id"]
        updated = update_task(
            target_id,
            {"status": "in-progress", "priority": "low", "title": "Updated Title"},
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated["status"], "in-progress")
        self.assertEqual(updated["priority"], "low")
        self.assertEqual(updated["title"], "Updated Title")

        # Verify persistence
        fetched = get_task(target_id)
        self.assertEqual(fetched["status"], "in-progress")

    def test_update_task_not_found(self) -> None:
        """Verify updating a non-existent task returns None."""
        result = update_task("fake-id", {"status": "done"})
        self.assertIsNone(result)

    def test_update_task_validation_errors(self) -> None:
        """Verify validation on update operations."""
        target_id = SEED_TASKS[0]["id"]
        with self.assertRaises(ValueError):
            update_task(target_id, {"title": "  "})

        with self.assertRaises(ValueError):
            update_task(target_id, {"status": "completed"})  # Should be 'done'

        with self.assertRaises(ValueError):
            update_task(target_id, {"priority": "none"})

    def test_delete_task_success(self) -> None:
        """Verify deleting a task removes it from the store."""
        target_id = SEED_TASKS[0]["id"]
        deleted = delete_task(target_id)
        self.assertTrue(deleted)
        self.assertIsNone(get_task(target_id))
        self.assertEqual(len(get_all_tasks()), 5)

    def test_delete_task_not_found(self) -> None:
        """Verify deleting non-existent task returns False."""
        deleted = delete_task("non-existent-uuid")
        self.assertFalse(deleted)

    def test_get_stats(self) -> None:
        """Verify statistics aggregation."""
        stats = get_stats()
        self.assertEqual(stats["total"], 6)
        self.assertEqual(stats["by_status"]["todo"], 2)
        self.assertEqual(stats["by_status"]["in-progress"], 2)
        self.assertEqual(stats["by_status"]["done"], 2)
        self.assertEqual(stats["by_priority"]["low"], 2)
        self.assertEqual(stats["by_priority"]["medium"], 2)
        self.assertEqual(stats["by_priority"]["high"], 2)


if __name__ == "__main__":
    unittest.main()
