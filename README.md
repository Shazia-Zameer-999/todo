# ◈ Studyflow

A polished personal study planner and REST API powered by **Python**, **Flask**, and **MongoDB**. It includes persistent task management, drag-and-drop workflows, focus sprints, due-soon and focus views, study-time estimates, course labels, completion momentum, search, sorting, themes, and automated test coverage.

---

## 🖼️ Interface & Screenshot Description

```
+-----------------------------------------------------------------------------------------------+
|  📋 Kanban Task Board        [ Search tasks... 🔍 ]   [ All Priorities ▾ ]    [ + New Task ]  |
+-----------------------------------------------------------------------------------------------+
|   [ 📊 Total: 6 ]      [ 📝 To Do: 2 ]       [ ⚡ In Progress: 2 ]      [ ✅ Done: 2 ]         |
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|   TO DO (2)                  IN PROGRESS (2)                DONE (2)                          |
|  +------------------------+ +----------------------------+ +-------------------------------+  |
|  | 🔴 [High]              | | 🔵 [High]                  | | 🟢 [Low]                      |  |
|  | Design user onboarding | | Build Kanban board UI      | | Initialize Git repository     |  |
|  | Wireframe sign-up and  | | Construct drag-and-drop    | | Configure structure, .git...  |  |
|  | walkthrough flow       | | columns in Tailwind CSS    | |                               |  |
|  | Sep 18            ✎ 🗑 | | Sep 18                ✎ 🗑 | | Sep 17                   ✎ 🗑 |  |
|  +------------------------+ +----------------------------+ +-------------------------------+  |
|  | 🟡 [Medium]            | | 🟣 [Medium]                | | 🩵 [Low]                      |  |
|  | Implement auth endpoints| | Develop REST API tests     | | Configure CI/CD automated...  |  |
|  | JWT session management | | Comprehensive unit tests   | | Set up GitHub Actions work... |  |
|  | Sep 18            ✎ 🗑 | | Sep 18                ✎ 🗑 | | Sep 17                   ✎ 🗑 |  |
|  +------------------------+ +----------------------------+ +-------------------------------+  |
|                                                                                               |
+-----------------------------------------------------------------------------------------------+
```

### Visual Overview:

- **Navigation Bar**: Displays branding, search bar with live filtering, priority selector dropdown, and the "+ New Task" modal trigger button.
- **Metrics Dashboard**: Top counter tiles showing real-time task counts for Total Tasks, To Do, In Progress, and Done.
- **Three Kanban Columns**:
  - 📝 **To Do**: Tasks awaiting commencement.
  - ⚡ **In Progress**: Tasks actively being worked on.
  - ✅ **Done**: Completed tasks.
- **Task Cards**: Feature color-accented left borders (hex color coded), title, description, priority badge (`High`, `Medium`, `Low`), formatted creation date, and quick action buttons (Edit, Delete).
- **Drag-and-Drop Interaction**: Native HTML5 drag-and-drop allows moving cards between columns, automatically triggering `PUT /api/tasks/<id>` to persist column status changes.

---

## ✨ Features

- **MongoDB Persistence**: Configure `MONGO_URI` to persist tasks in the `taskflow.tasks` collection. If no URI is configured, the app uses the deterministic in-memory seed store for tests and offline development.
- **Full RESTful CRUD API**:
  - Create, read, update, and delete tasks with validated input schemas.
  - Filter tasks via query parameters (`?status=todo`, `in-progress`, `done`).
  - Aggregate dashboard statistics endpoint (`/api/stats`).
- **Drag-and-Drop Board**: Smooth HTML5 drag-and-drop card status updates with optimistic UI rendering.
- **Study Planning**: Search title, description, and tags; filter by priority; add a course or subject; set due dates; estimate study time; sort by deadline, priority, or newest; and organize with up to eight tags.
- **Focus & Momentum**: Run a 25-minute focus sprint, switch to Focus mode for unfinished work, view Due soon tasks, and track completion momentum at a glance.
- **Gentle Feedback**: Optional Web Audio completion chimes for focus sprints and completed tasks, plus explicit browser reminder permission. Sound preferences are stored locally and never require an audio file or external service.
- **Input Validation & Error Handling**: Comprehensive validation for required fields, enum statuses, priorities, and standard JSON HTTP error payloads (`400`, `404`, `405`, `500`).
- **CORS Enabled**: Cross-Origin Resource Sharing enabled on all `/api/*` routes for seamless decoupled frontend or mobile clients.
- **Polished Responsive UI**: Built with Tailwind CSS and responsive design supporting desktop, tablet, and mobile browsers.
- **Automated Test Suite**: Pytest test suite with 20+ test scenarios covering all endpoints, query filters, validations, and edge cases.

---

## 🛠️ Tech Stack

- **Backend Framework**: [Flask 3.1.1](https://palletsprojects.com/p/flask/)
- **CORS Support**: [Flask-CORS 5.0.1](https://flask-cors.readthedocs.io/)
- **Testing Frameworks**: [Pytest](https://docs.pytest.org/) & Python `unittest`
- **Frontend**: HTML5, Modern Vanilla JavaScript (Fetch API & Drag-and-Drop API), custom responsive CSS
- **Runtime**: Python 3.10+ (tested on Python 3.13)

---

## 🚀 Setup & Installation

### 1. Prerequisites

Ensure you have Python 3.10 or newer installed:

```bash
python3 --version
```

### 2. Configure MongoDB

Create a local environment file from the template, then set your MongoDB connection string without committing credentials:

```bash
cp .env.example .env
export MONGO_URI='mongodb+srv://<username>:<password>@<cluster>/<database>'
export MONGO_DB_NAME=taskflow
```

The application creates the `tasks` collection and seeds it only when it is empty. Never commit `.env` or expose the URI in frontend code.

### 3. Navigate to Project Directory

```bash
cd /Users/shaziazameer/.gemini/antigravity/scratch/task-kanban
```

### 4. Create and Activate Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate on macOS / Linux
source venv/bin/activate

# (On Windows PowerShell: .\venv\Scripts\Activate.ps1)
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt pytest
```

### 6. Run the Application

```bash
python app.py
```

The server will start at:

```
http://localhost:5000
```

Open [http://localhost:5000](http://localhost:5000) in your browser to view the interactive Kanban Board.

---

## 🧪 Running the Tests

To run the comprehensive test suite with `pytest`:

```bash
pytest tests/test_api.py -v
```

To run model unit tests with Python's built-in test runner:

```bash
python -m unittest tests/test_models.py
```

---

## 📚 REST API Documentation

Base URL: `http://localhost:5000/api`

| Method     | Endpoint          | Description            | Request Body / Query                                 |        Status Code         | Example Response                                         |
| :--------- | :---------------- | :--------------------- | :--------------------------------------------------- | :------------------------: | :------------------------------------------------------- |
| **GET**    | `/api/tasks`      | List all tasks         | Query: `?status=todo` _(optional)_                   |          `200 OK`          | `[{"id": "...", "title": "Design UI", ...}]`             |
| **POST**   | `/api/tasks`      | Create a new task      | JSON `{title, description, status, priority, color}` |       `201 Created`        | `{"id": "...", "title": "New Task", ...}`                |
| **GET**    | `/api/tasks/<id>` | Retrieve a single task | None                                                 | `200 OK` / `404 Not Found` | `{"id": "...", "title": "...", ...}`                     |
| **PUT**    | `/api/tasks/<id>` | Update task attributes | JSON `{status: "done", ...}`                         | `200 OK` / `404 Not Found` | `{"id": "...", "status": "done", ...}`                   |
| **DELETE** | `/api/tasks/<id>` | Delete a task          | None                                                 | `200 OK` / `404 Not Found` | `{"message": "Task deleted successfully", "id": "..."}`  |
| **GET**    | `/api/stats`      | Dashboard metrics      | None                                                 |          `200 OK`          | `{"total": 6, "by_status": {...}, "by_priority": {...}}` |

### Allowed Enumeration Values:

- **`status`**: `"todo"`, `"in-progress"`, `"done"`
- **`priority`**: `"low"`, `"medium"`, `"high"`

### Example Request Payloads

#### Create Task (`POST /api/tasks`):

```json
{
  "title": "Set up payment gateway",
  "description": "Integrate Stripe Checkout and webhooks for subscriptions.",
  "status": "todo",
  "priority": "high",
  "color": "#ef4444"
}
```

#### Update Task Status on Drop (`PUT /api/tasks/<id>`):

```json
{
  "status": "in-progress"
}
```

#### Get Statistics (`GET /api/stats`):

```json
{
  "total": 6,
  "by_status": {
    "todo": 2,
    "in-progress": 2,
    "done": 2
  },
  "by_priority": {
    "low": 2,
    "medium": 2,
    "high": 2
  }
}
```

---

## 📁 Project Structure

```
task-kanban/
├── app.py                   # Flask REST API, CORS setup, routes, static file serving
├── models.py                # MongoDB/memory repository, seed tasks, validation, CRUD functions
├── requirements.txt         # Production dependencies (Flask, Flask-CORS)
├── requirements-dev.txt     # Development/testing dependencies (Pytest)
├── README.md                # Project documentation and API reference
├── templates/
│   └── index.html           # Full interactive Drag-and-Drop Kanban Board UI
├── static/                  # Static assets (CSS/JS/images)
└── tests/
    ├── __init__.py          # Test package marker
    ├── test_api.py          # Pytest test client suite (20+ tests covering all endpoints)
    └── test_models.py       # Standalone unittest suite for data store & validation
```

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
