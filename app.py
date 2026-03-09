import html
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "tasks.db"
CSS_PATH = BASE_DIR / "static" / "styles.css"
HOST = "127.0.0.1"
PORT = 3000

DB_DIR.mkdir(exist_ok=True)


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )


def escape(value: str | None) -> str:
    return html.escape(value or "", quote=True)


def page_layout(title: str, content: str) -> str:
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(title)}</title>
  <link rel=\"stylesheet\" href=\"/styles.css\" />
</head>
<body>
  <main class=\"container\">
    <header class=\"header\">
      <h1>Task Manager</h1>
      <p>Python + SQLite CRUD backend</p>
    </header>
    {content}
  </main>
</body>
</html>"""


def render_list_page(tasks: list[sqlite3.Row], error_message: str = "", values: dict[str, str] | None = None) -> str:
    values = values or {}
    rows = ""

    for task in tasks:
        task_id = task["id"]
        status = task["status"] if task["status"] in {"pending", "done"} else "pending"
        rows += f"""
        <tr>
          <td>{task_id}</td>
          <td>{escape(task['title'])}</td>
          <td>{escape(task['description'])}</td>
          <td><span class=\"status {status}\">{escape(status)}</span></td>
          <td class=\"actions\">
            <a class=\"btn\" href=\"/tasks/{task_id}/edit\">Edit</a>
            <form method=\"post\" action=\"/tasks/{task_id}/delete\">
              <button class=\"btn danger\" type=\"submit\">Delete</button>
            </form>
          </td>
        </tr>
        """

    if not rows:
        rows = '<tr><td colspan="5">No tasks yet.</td></tr>'

    content = f"""
    <section class=\"card\">
      <h2>Add Task</h2>
      {f'<p class=\"error\">{escape(error_message)}</p>' if error_message else ''}
      <form method=\"post\" action=\"/tasks\" class=\"form-grid\">
        <label>
          Title
          <input name=\"title\" required maxlength=\"120\" value=\"{escape(values.get('title', ''))}\" />
        </label>
        <label>
          Description
          <textarea name=\"description\" rows=\"3\" maxlength=\"600\">{escape(values.get('description', ''))}</textarea>
        </label>
        <label>
          Status
          <select name=\"status\">
            <option value=\"pending\" {'selected' if values.get('status', 'pending') == 'pending' else ''}>Pending</option>
            <option value=\"done\" {'selected' if values.get('status') == 'done' else ''}>Done</option>
          </select>
        </label>
        <button type=\"submit\">Create</button>
      </form>
    </section>

    <section class=\"card\">
      <h2>Tasks</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Description</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </section>
    """

    return page_layout("Task Manager", content)


def render_edit_page(task: sqlite3.Row, error_message: str = "") -> str:
    status = task["status"] if task["status"] in {"pending", "done"} else "pending"
    task_id = task["id"]

    content = f"""
    <section class=\"card\">
      <h2>Edit Task #{task_id}</h2>
      {f'<p class=\"error\">{escape(error_message)}</p>' if error_message else ''}
      <form method=\"post\" action=\"/tasks/{task_id}/update\" class=\"form-grid\">
        <label>
          Title
          <input name=\"title\" required maxlength=\"120\" value=\"{escape(task['title'])}\" />
        </label>
        <label>
          Description
          <textarea name=\"description\" rows=\"3\" maxlength=\"600\">{escape(task['description'])}</textarea>
        </label>
        <label>
          Status
          <select name=\"status\">
            <option value=\"pending\" {'selected' if status == 'pending' else ''}>Pending</option>
            <option value=\"done\" {'selected' if status == 'done' else ''}>Done</option>
          </select>
        </label>
        <div class=\"actions-row\">
          <button type=\"submit\">Update</button>
          <a class=\"btn\" href=\"/tasks\">Back</a>
        </div>
      </form>
    </section>
    """
    return page_layout("Edit Task", content)


def render_error_page(status_code: int, title: str, message: str) -> str:
    content = f"""
    <section class=\"card\">
      <h2>{status_code} - {escape(title)}</h2>
      <p>{escape(message)}</p>
      <a class=\"btn\" href=\"/tasks\">Go to tasks</a>
    </section>
    """
    return page_layout(title, content)


def parse_form_data(raw_body: bytes) -> dict[str, str]:
    parsed = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    return {key: values[0] if values else "" for key, values in parsed.items()}


def normalize_task_input(payload: dict[str, str]) -> tuple[str | None, dict[str, str]]:
    title = payload.get("title", "").strip()
    description = payload.get("description", "").strip()
    status = "done" if payload.get("status") == "done" else "pending"

    if not title:
        return "Title is required.", {"title": title, "description": description, "status": status}

    return None, {"title": title, "description": description, "status": status}


class TaskHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.dispatch_request()

    def do_POST(self) -> None:
        self.dispatch_request()

    def dispatch_request(self) -> None:
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path

            if self.command == "GET" and path == "/styles.css":
                self.serve_css()
                return

            if self.command == "GET" and path in {"/", "/tasks"}:
                self.list_tasks()
                return

            edit_match = re.fullmatch(r"/tasks/(\d+)/edit", path)
            if self.command == "GET" and edit_match:
                self.show_edit_page(int(edit_match.group(1)))
                return

            if self.command == "POST" and path == "/tasks":
                self.create_task()
                return

            update_match = re.fullmatch(r"/tasks/(\d+)/update", path)
            if self.command == "POST" and update_match:
                self.update_task(int(update_match.group(1)))
                return

            delete_match = re.fullmatch(r"/tasks/(\d+)/delete", path)
            if self.command == "POST" and delete_match:
                self.delete_task(int(delete_match.group(1)))
                return

            self.send_html(404, render_error_page(404, "Not Found", "The requested route does not exist."))
        except Exception as error:
            print(f"Unhandled server error: {error}")
            self.send_html(500, render_error_page(500, "Server Error", "Something went wrong while processing your request."))

    def list_tasks(self, error_message: str = "", values: dict[str, str] | None = None) -> None:
        with get_connection() as connection:
            tasks = connection.execute(
                "SELECT id, title, description, status, created_at FROM tasks ORDER BY id DESC"
            ).fetchall()
        self.send_html(200, render_list_page(tasks, error_message, values))

    def show_edit_page(self, task_id: int, error_message: str = "", override_values: dict[str, str] | None = None) -> None:
        with get_connection() as connection:
            task = connection.execute(
                "SELECT id, title, description, status, created_at FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()

        if not task:
            self.send_html(404, render_error_page(404, "Not Found", "Task not found."))
            return

        if override_values:
            task = {
                "id": task["id"],
                "title": override_values.get("title", task["title"]),
                "description": override_values.get("description", task["description"]),
                "status": override_values.get("status", task["status"]),
            }

        self.send_html(200, render_edit_page(task, error_message))

    def create_task(self) -> None:
        payload = self.read_form_payload()
        error_message, data = normalize_task_input(payload)

        if error_message:
            self.list_tasks(error_message, data)
            return

        with get_connection() as connection:
            connection.execute(
                "INSERT INTO tasks (title, description, status) VALUES (?, ?, ?)",
                (data["title"], data["description"], data["status"]),
            )
            connection.commit()

        self.redirect("/tasks")

    def update_task(self, task_id: int) -> None:
        payload = self.read_form_payload()
        error_message, data = normalize_task_input(payload)

        with get_connection() as connection:
            existing = connection.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()

        if not existing:
            self.send_html(404, render_error_page(404, "Not Found", "Task not found."))
            return

        if error_message:
            self.show_edit_page(task_id, error_message, data)
            return

        with get_connection() as connection:
            connection.execute(
                "UPDATE tasks SET title = ?, description = ?, status = ? WHERE id = ?",
                (data["title"], data["description"], data["status"], task_id),
            )
            connection.commit()

        self.redirect("/tasks")

    def delete_task(self, task_id: int) -> None:
        with get_connection() as connection:
            existing = connection.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if not existing:
                self.send_html(404, render_error_page(404, "Not Found", "Task not found."))
                return

            connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            connection.commit()

        self.redirect("/tasks")

    def serve_css(self) -> None:
        if not CSS_PATH.exists():
            self.send_html(404, "<h1>404</h1>")
            return

        css = CSS_PATH.read_text(encoding="utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/css; charset=utf-8")
        self.end_headers()
        self.wfile.write(css.encode("utf-8"))

    def read_form_payload(self) -> dict[str, str]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        return parse_form_data(raw_body)

    def send_html(self, status_code: int, content: str) -> None:
        html_content = content.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_content)))
        self.end_headers()
        self.wfile.write(html_content)

    def redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()


if __name__ == "__main__":
    initialize_database()
    server = HTTPServer((HOST, PORT), TaskHandler)
    print(f"Server running at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
