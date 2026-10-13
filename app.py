"""
Flask REST API for Kanban Task Board application.

Endpoints:
    - GET    /api/tasks       : List all tasks, with optional ?status= filter
    - POST   /api/tasks       : Create a new task
    - GET    /api/tasks/<id>  : Retrieve details for a single task
    - PUT    /api/tasks/<id>  : Update a task (title, description, status, priority, color)
    - DELETE /api/tasks/<id>  : Delete a task
    - GET    /api/stats       : Retrieve aggregated task metrics
    - GET    /                : Serve the Kanban web interface
    - GET    /static/<path>   : Serve static frontend assets
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_from_directory,
    Response,
)
from flask_cors import CORS

from models import (
    VALID_PRIORITIES,
    VALID_STATUSES,
    create_task,
    configure_store,
    delete_task,
    get_all_tasks,
    get_stats,
    get_task,
    reset_tasks,
    storage_info,
    update_task,
)


def load_local_environment(base_dir: str) -> None:
    """Load simple KEY=value entries from a local .env without overriding the shell."""
    env_path = os.path.join(base_dir, ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """Create and configure an instance of the Flask application.

    Args:
        test_config: Optional dictionary containing configuration overrides for testing.

    Returns:
        Configured Flask application instance.
    """
    base_dir = os.path.abspath(os.path.dirname(__file__))
    load_local_environment(base_dir)
    template_dir = os.path.join(base_dir, "templates")
    static_dir = os.path.join(base_dir, "static")

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir,
    )

    # Enable Cross-Origin Resource Sharing (CORS) for all /api/ endpoints
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    # Configuration defaults
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "kanban-secret-key-dev"),
        MONGO_URI=os.environ.get("MONGO_URI", ""),
        MONGO_DB_NAME=os.environ.get("MONGO_DB_NAME", "taskflow"),
        JSON_SORT_KEYS=False,
    )

    if test_config:
        app.config.update(test_config)
    if app.config.get("TESTING") and not (test_config and "MONGO_URI" in test_config):
        app.config["MONGO_URI"] = ""

    configure_store(app.config.get("MONGO_URI"), app.config.get("MONGO_DB_NAME"))

    # -------------------------------------------------------------------------
    # REST API Endpoints
    # -------------------------------------------------------------------------

    @app.route("/api/tasks", methods=["GET"])
    def list_tasks() -> Tuple[Response, int]:
        """List all tasks, with optional ?status= filter.

        Query Parameters:
            status (str, optional): Filter tasks by 'todo', 'in-progress', or 'done'.

        Returns:
            JSON array of task objects and 200 HTTP status code, or 400 on invalid status.
        """
        status_filter = request.args.get("status")
        priority_filter = request.args.get("priority")
        search_filter = request.args.get("q", "").strip()

        if priority_filter and priority_filter.strip().lower() not in VALID_PRIORITIES:
            return (
                jsonify(
                    {
                        "error": f"Invalid priority '{priority_filter}'. Valid options are: {', '.join(VALID_PRIORITIES)}."
                    }
                ),
                400,
            )

        if status_filter:
            status_clean = status_filter.strip().lower()
            if status_clean not in VALID_STATUSES:
                return (
                    jsonify(
                        {
                            "error": (
                                f"Invalid status '{status_filter}'. "
                                f"Valid options are: {', '.join(VALID_STATUSES)}."
                            )
                        }
                    ),
                    400,
                )
            tasks = get_all_tasks(
                status=status_clean, priority=priority_filter, search=search_filter
            )
        else:
            tasks = get_all_tasks(priority=priority_filter, search=search_filter)

        return jsonify(tasks), 200

    @app.route("/api/tasks", methods=["POST"])
    def add_task() -> Tuple[Response, int]:
        """Create a new task.

        Request Body (JSON):
            - title (str, required): Task title.
            - description (str, optional): Task description.
            - status (str, optional): One of 'todo', 'in-progress', 'done'. Defaults to 'todo'.
            - priority (str, optional): One of 'low', 'medium', 'high'. Defaults to 'medium'.
            - color (str, optional): Hex color code.

        Returns:
            Created task JSON and 201 HTTP status code, or 400 on validation failure.
        """
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return (
                jsonify({"error": "Request body must be a valid JSON object."}),
                400,
            )

        try:
            created = create_task(data)
            return jsonify(created), 201
        except ValueError as err:
            return jsonify({"error": str(err)}), 400

    @app.route("/api/tasks/<string:task_id>", methods=["GET"])
    def get_single_task(task_id: str) -> Tuple[Response, int]:
        """Retrieve a single task by ID.

        Args:
            task_id (str): The unique identifier of the task.

        Returns:
            Task JSON and 200 status code, or 404 if not found.
        """
        task = get_task(task_id)
        if task is None:
            return jsonify({"error": f"Task with id '{task_id}' not found."}), 404

        return jsonify(task), 200

    @app.route("/api/tasks/<string:task_id>", methods=["PUT"])
    def update_single_task(task_id: str) -> Tuple[Response, int]:
        """Update an existing task by ID (used for drag-drop status updates and editing).

        Args:
            task_id (str): The unique identifier of the task.

        Request Body (JSON):
            One or more of: title, description, status, priority, color.

        Returns:
            Updated task JSON and 200 status code, 404 if not found, or 400 on invalid data.
        """
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return (
                jsonify({"error": "Request body must be a valid JSON object."}),
                400,
            )

        existing = get_task(task_id)
        if existing is None:
            return jsonify({"error": f"Task with id '{task_id}' not found."}), 404

        try:
            updated = update_task(task_id, data)
            if updated is None:
                return jsonify({"error": f"Task with id '{task_id}' not found."}), 404
            return jsonify(updated), 200
        except ValueError as err:
            return jsonify({"error": str(err)}), 400

    @app.route("/api/tasks/<string:task_id>", methods=["DELETE"])
    def delete_single_task(task_id: str) -> Tuple[Response, int]:
        """Delete a task by ID.

        Args:
            task_id (str): The unique identifier of the task.

        Returns:
            Confirmation message and 200 status code, or 404 if not found.
        """
        success = delete_task(task_id)
        if not success:
            return jsonify({"error": f"Task with id '{task_id}' not found."}), 404

        return (
            jsonify(
                {
                    "message": f"Task '{task_id}' deleted successfully.",
                    "id": task_id,
                }
            ),
            200,
        )

    @app.route("/api/stats", methods=["GET"])
    def get_dashboard_stats() -> Tuple[Response, int]:
        """Retrieve aggregated task metrics for the dashboard.

        Returns:
            JSON object with total counts, counts by status, and counts by priority.
        """
        stats = get_stats()
        return jsonify(stats), 200

    @app.route("/api/health", methods=["GET"])
    def health() -> Tuple[Response, int]:
        """Return a lightweight service and storage status for deployment checks."""
        return (
            jsonify(
                {"status": "healthy", "service": "taskflow", "storage": storage_info()}
            ),
            200,
        )

    # -------------------------------------------------------------------------
    # Web UI & Static File Serving
    # -------------------------------------------------------------------------

    @app.route("/", methods=["GET"])
    def index() -> Response | str:
        """Serve the Kanban frontend interface from templates/."""
        index_path = os.path.join(app.template_folder, "index.html")
        if os.path.isfile(index_path):
            return render_template("index.html")

        return jsonify(
            {
                "name": "Kanban Task Board API",
                "version": "1.0.0",
                "status": "healthy",
                "documentation": "/api/docs",
                "endpoints": {
                    "list_tasks": "GET /api/tasks",
                    "filter_tasks": "GET /api/tasks?status=<todo|in-progress|done>",
                    "create_task": "POST /api/tasks",
                    "get_task": "GET /api/tasks/<id>",
                    "update_task": "PUT /api/tasks/<id>",
                    "delete_task": "DELETE /api/tasks/<id>",
                    "dashboard_stats": "GET /api/stats",
                },
            }
        )

    @app.route("/static/<path:filename>", methods=["GET"])
    def serve_static(filename: str) -> Response:
        """Serve static files from the static directory."""
        return send_from_directory(app.static_folder, filename)

    # -------------------------------------------------------------------------
    # HTTP Error Handlers
    # -------------------------------------------------------------------------

    @app.errorhandler(400)
    def handle_bad_request(error: Any) -> Tuple[Response, int]:
        """Handle 400 Bad Request error."""
        message = getattr(error, "description", "Bad Request")
        return jsonify({"error": message}), 400

    @app.errorhandler(404)
    def handle_not_found(error: Any) -> Tuple[Response, int]:
        """Handle 404 Not Found error."""
        message = getattr(error, "description", "Resource not found.")
        return jsonify({"error": message}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error: Any) -> Tuple[Response, int]:
        """Handle 405 Method Not Allowed error."""
        return jsonify({"error": "HTTP method not allowed for this endpoint."}), 405

    @app.errorhandler(500)
    def handle_internal_server_error(error: Any) -> Tuple[Response, int]:
        """Handle 500 Internal Server Error."""
        return jsonify({"error": "An unexpected internal server error occurred."}), 500

    return app


# Module-level application instance for WSGI servers and direct execution
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"🚀 Kanban Task Board Server starting at http://{host}:{port}")
    app.run(host=host, port=port, debug=True)
