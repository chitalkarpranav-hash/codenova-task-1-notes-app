# NoteNest - Full-Stack Notes Application

A responsive notes application built for CodeNova Task 1. It supports creating, editing, deleting, and instantly searching notes while persisting every change in a SQLite database.

## Features

- Create notes with a title and content
- Edit notes in place through the composer
- Delete notes with a confirmation prompt
- Search title and content instantly, case-insensitively
- SQLite-backed REST API: data survives server restarts
- Responsive card layout for mobile and desktop
- Friendly status notifications for validation, network, and server errors

## Tech stack

- **Client:** Vanilla HTML, CSS, and JavaScript
- **Server:** Python standard-library HTTP server
- **Database:** SQLite (Python `sqlite3`)

No third-party package installation is required.

## Project structure

```text
client/                 # Responsive browser application
  index.html
  app.js
  styles.css
server/                 # API and database layer
  app.py
  schema.sql
  tests/test_api.py
```

## Run locally

1. Make sure Python 3.10+ is available.
2. From this repository's root, start the application:

   ```bash
   python server/app.py
   ```

3. Open [http://localhost:8000](http://localhost:8000) in a browser.

The server creates `server/data/notes.db` automatically and initializes its schema from `server/schema.sql`.

## API contract

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/notes?q=term` | List notes, optionally matching title or content |
| `POST` | `/api/notes` | Create a note |
| `PUT` | `/api/notes/:id` | Update a note |
| `DELETE` | `/api/notes/:id` | Delete a note |

### Example create request

```json
{
  "title": "Project idea",
  "content": "Build a full-stack notes app."
}
```

Both fields are required. The API returns structured JSON errors for invalid data, missing records, malformed JSON, and unexpected server failures.

## Architecture

The client owns its display state and always refreshes it from the API after a mutation. The server validates incoming data, performs SQLite operations, and returns the database's authoritative records. This prevents the interface from drifting away from persisted data.

## Test the API

```bash
python -m unittest discover -s server/tests -v
```

The test suite uses an isolated temporary SQLite database and covers CRUD, search, validation, and missing-note behavior.

## Suggested screenshots for submission

Run the app locally and capture:

1. The empty state and note composer.
2. Several created notes with a search query active.
3. The edit flow and a success notification.

