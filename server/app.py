"""SQLite-backed Notes REST API and static-file server."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
CLIENT_DIR = ROOT / "client"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DATABASE_PATH = Path(__file__).with_name("data") / "notes.db"


class NotesRepository:
    def __init__(self, database_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def serialize(row: sqlite3.Row) -> dict[str, object]:
        return dict(row)

    def list(self, query: str = "") -> list[dict[str, object]]:
        pattern = f"%{query.strip()}%"
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, title, content, created_at, updated_at
                FROM notes
                WHERE title LIKE ? COLLATE NOCASE OR content LIKE ? COLLATE NOCASE
                ORDER BY updated_at DESC, id DESC
                """,
                (pattern, pattern),
            ).fetchall()
        return [self.serialize(row) for row in rows]

    def create(self, title: str, content: str) -> dict[str, object]:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.connection() as connection:
            cursor = connection.execute(
                "INSERT INTO notes (title, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (title, content, now, now),
            )
            row = connection.execute(
                "SELECT id, title, content, created_at, updated_at FROM notes WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return self.serialize(row)

    def update(self, note_id: int, title: str, content: str) -> dict[str, object] | None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.connection() as connection:
            cursor = connection.execute(
                "UPDATE notes SET title = ?, content = ?, updated_at = ? WHERE id = ?",
                (title, content, now, note_id),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                "SELECT id, title, content, created_at, updated_at FROM notes WHERE id = ?",
                (note_id,),
            ).fetchone()
        return self.serialize(row)

    def delete(self, note_id: int) -> bool:
        with self.connection() as connection:
            cursor = connection.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        return cursor.rowcount > 0


def validate_note(payload: object) -> tuple[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("Send a JSON object with title and content.")
    title = payload.get("title")
    content = payload.get("content")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("A note title is required.")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Note content is required.")
    if len(title.strip()) > 120:
        raise ValueError("Title must be 120 characters or fewer.")
    if len(content.strip()) > 10_000:
        raise ValueError("Content must be 10,000 characters or fewer.")
    return title.strip(), content.strip()


class NotesHandler(SimpleHTTPRequestHandler):
    repository: NotesRepository

    def __init__(self, *args, directory: str | None = None, **kwargs) -> None:
        super().__init__(*args, directory=str(CLIENT_DIR), **kwargs)

    def send_json(self, status: HTTPStatus, data: object) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> object:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError("Request body must contain valid JSON.") from error

    @staticmethod
    def note_id(path: str) -> int | None:
        parts = path.strip("/").split("/")
        if len(parts) != 3 or parts[:2] != ["api", "notes"]:
            return None
        try:
            return int(parts[2])
        except ValueError:
            return None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/notes":
            query = parse_qs(parsed.query).get("q", [""])[0]
            self.send_json(HTTPStatus.OK, {"notes": self.repository.list(query)})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/notes":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})
            return
        try:
            title, content = validate_note(self.read_json())
            self.send_json(HTTPStatus.CREATED, {"note": self.repository.create(title, content)})
        except ValueError as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception:
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Could not save the note."})

    def do_PUT(self) -> None:
        note_id = self.note_id(urlparse(self.path).path)
        if note_id is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})
            return
        try:
            title, content = validate_note(self.read_json())
            note = self.repository.update(note_id, title, content)
            if note is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Note not found."})
                return
            self.send_json(HTTPStatus.OK, {"note": note})
        except ValueError as error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception:
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Could not update the note."})

    def do_DELETE(self) -> None:
        note_id = self.note_id(urlparse(self.path).path)
        if note_id is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})
            return
        if not self.repository.delete(note_id):
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Note not found."})
            return
        self.send_json(HTTPStatus.OK, {"message": "Note deleted."})

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")


def create_server(database_path: Path = DEFAULT_DATABASE_PATH, port: int = 8000) -> ThreadingHTTPServer:
    NotesHandler.repository = NotesRepository(database_path)
    return ThreadingHTTPServer(("127.0.0.1", port), NotesHandler)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    server = create_server(port=port)
    print(f"NoteNest is running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()

