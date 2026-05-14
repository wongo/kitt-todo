# KITT-TODO Specification

## System Overview

KITT-TODO is a Telegram-integrated task management system with a Phase 2 web UI.

- Phase 1: Telegram bot using `python-telegram-bot` v22+
- Phase 2: Full-stack web UI using FastAPI, Neon PostgreSQL, Astro, and React
- Runtime language: Python 3.14
- Local database: SQLite at `./data/kitt_todo.db`
- Web API database: shared Neon PostgreSQL using the separate `kitt_todo` schema
- Cloud backup: GitHub Gist JSON export through the `gh` CLI

## File Structure

```text
kitt-todo/
├── SPEC.md
├── .env
├── data/
│   ├── kitt_todo.db
│   ├── .gist_id
│   └── backup.json
├── scripts/
│   └── backup_to_gist.sh
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── db.py
│   └── routers/
│       ├── __init__.py
│       ├── tasks.py
│       └── categories.py
├── web/
│   ├── src/
│   │   ├── pages/
│   │   │   └── index.astro
│   │   ├── layouts/
│   │   │   └── Layout.astro
│   │   └── components/
│   │       ├── CategoryFilter.jsx
│   │       ├── DoneList.jsx
│   │       ├── TaskForm.jsx
│   │       ├── TaskItem.jsx
│   │       └── TaskList.jsx
│   ├── public/
│   ├── astro.config.mjs
│   ├── package.json
│   └── tailwind.config.js
├── render.yaml
├── vercel.json
├── bot.py
├── db.py
├── handlers/
│   ├── __init__.py
│   ├── task.py
│   ├── category.py
│   └── reminder.py
├── parser.py
├── config.py
└── requirements.txt
```

## Configuration

`config.py` defines the local filesystem paths and token environment variable:

```python
import os

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

BOT_TOKEN = os.getenv("KITT_TODO_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
GIST_ID_FILE = os.path.join(DATA_DIR, ".gist_id")
DB_PATH = os.path.join(DATA_DIR, "kitt_todo.db")
BACKUP_JSON_PATH = os.path.join(DATA_DIR, "backup.json")
```

`.env`:

```text
KITT_TODO_BOT_TOKEN=your_telegram_bot_token_here
DATABASE_URL=postgresql://neondb_owner:***@ep-jolly-shape-aq7e5ai7.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require
NEON_SCHEMA=kitt_todo
```

`DATABASE_URL` and `NEON_SCHEMA` are used by the Phase 2 FastAPI server. The Render deployment config sets them for the hosted API.

## Commands

### Task CRUD

- `/add <title> [--priority high|medium|low] [--due YYYY-MM-DD] [--category name] [--repeat daily|weekly]`
- `/list`
- `/list --category <name>`
- `/done <task_id>`
- `/delete <task_id>`
- `/edit <task_id> <new_title>`

`/edit` is also available as a multi-step conversation when called with no title.

### Categories

- `/category add <name> [--icon emoji]`
- `/tag <task_id> <category>`
- `/categories`

### Due Dates

Due dates support:

- `YYYY-MM-DD`
- `YYYY-MM-DD HH:MM`

`/list` marks tasks as `OVERDUE` when their due date/time is before the current local time. `/overdue` lists overdue tasks only.

### Repeating Tasks

Supported repeat values:

- `daily`
- `weekly`

When a repeating task is marked done, KITT-TODO marks the current occurrence complete and creates the next occurrence. The original `created_at` is preserved on generated occurrences.

### Reminders

- `/remind <task_id> <HH:MM>`

`/remind` is also available as a multi-step conversation when called with incomplete arguments.

Reminders are persisted in SQLite. `bot.py` starts a background reminder thread at bot startup. The thread checks pending reminders every minute and sends Telegram messages for due reminders.

The implementation stores `chat_id` in the `reminders` table in addition to the originally requested fields. This is required for reminders to survive bot restarts and still know which Telegram chat should receive the message.

### Quick Add

Natural-language quick add is handled by `parser.py`:

```python
def parse_quick_add(text: str) -> dict | None
```

The parser returns `None` unless text contains one of:

- `幫我記下`
- `記下`
- `新增待辦`

Priority keyword extraction:

- `重要` -> `high`
- `急` -> `high`
- `慢慢來` -> `low`
- default -> `medium`

Date keyword extraction:

- `今天` -> today
- `明天` -> tomorrow
- `下週` -> today + 7 days

Time parsing:

- `下午3點` -> `15:00`
- `3點` -> `03:00`
- `15:00` -> `15:00`

## Database Schema

### Phase 1 SQLite

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    priority TEXT DEFAULT 'medium',
    category TEXT,
    due_date TEXT,
    due_time TEXT,
    repeat_type TEXT,
    is_done INTEGER DEFAULT 0,
    done_at TEXT,
    created_at TEXT NOT NULL,
    next_due TEXT
);

CREATE TABLE categories (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    icon TEXT DEFAULT '📂'
);

CREATE TABLE reminders (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    remind_at TEXT NOT NULL,
    chat_id TEXT,
    sent INTEGER DEFAULT 0,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

All database operations are isolated in `db.py`.

### Phase 2 PostgreSQL

The web API uses Neon PostgreSQL and keeps its tables isolated in the `kitt_todo` schema:

```sql
CREATE SCHEMA IF NOT EXISTS kitt_todo;

CREATE TABLE kitt_todo.tasks (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    title TEXT NOT NULL,
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),
    category TEXT,
    due_date DATE,
    due_time TIME,
    repeat_type TEXT CHECK (repeat_type IS NULL OR repeat_type IN ('daily', 'weekly')),
    is_done BOOLEAN DEFAULT FALSE,
    done_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    next_due DATE
);

CREATE TABLE kitt_todo.categories (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name TEXT UNIQUE NOT NULL,
    icon TEXT DEFAULT '📂'
);
```

`api/main.py` initializes this schema on startup. `api/db.py` creates an asyncpg pool with `command_timeout=60` and sets `search_path` to `kitt_todo` for each connection.

## Phase 2 API

The API server is a FastAPI app deployed as a new Render service at:

```text
https://kitt-todo-api.onrender.com
```

All endpoints return JSON. Authentication is intentionally omitted for the current single-user deployment. CORS allows all origins for development and Vercel static hosting.

```text
GET  /api/health
GET  /api/tasks
POST /api/tasks
GET  /api/tasks/{id}
PUT  /api/tasks/{id}
DELETE /api/tasks/{id}
POST /api/tasks/{id}/done
GET  /api/categories
POST /api/categories
DELETE /api/categories/{id}
```

`GET /api/tasks` supports these query filters:

```text
status=pending|done
category=<name>
priority=high|medium|low
```

Task create payload:

```json
{
  "title": "Review tasks",
  "priority": "medium",
  "due_date": "2026-05-14",
  "due_time": "14:30",
  "category": "work",
  "repeat_type": "daily"
}
```

Category create payload:

```json
{
  "name": "work",
  "icon": "💼"
}
```

Marking a repeating task done sets `is_done=true` and `done_at=now()`, then creates the next pending occurrence. Daily repeats advance `due_date` by one day; weekly repeats advance it by seven days. Dates use ISO `YYYY-MM-DD`; times use `HH:MM`.

## Phase 2 Web UI

The frontend is an Astro static app with React components hydrated through `client:load`. It is deployed to Vercel from `web/`.

Key UI behavior:

- `TaskList` loads pending and completed tasks from the API.
- Pending tasks are grouped by priority: high, medium, low.
- Tasks are sorted by due date and time inside each priority group.
- `TaskForm` opens as a modal for creating and editing tasks.
- `TaskItem` shows a done checkbox, title, priority badge, due date/time, category tag, repeat tag, edit, and delete buttons.
- `CategoryFilter` shows `全部`, category filters, and overdue counts.
- `DoneList` shows completed tasks from the last seven days.
- Overdue tasks are highlighted in red.
- The visual style is dark, monospace, red-accented, responsive, and includes an ASCII-art header.

The default API base URL is:

```text
https://kitt-todo-api.onrender.com/api
```

Vercel also rewrites `/api/*` to the Render API:

```json
{
  "rewrites": [{ "source": "/api/(.*)", "destination": "https://kitt-todo-api.onrender.com/api/$1" }]
}
```

## Backup

Backup script:

```text
./scripts/backup_to_gist.sh
```

Behavior:

1. Initializes the database if needed.
2. Exports tasks and categories as JSON to `./data/backup.json`.
3. Uses `gh gist create --filename backup.json --description "KITT-TODO backup"` when `./data/.gist_id` is empty or missing.
4. Stores the created gist ID in `./data/.gist_id`.
5. Updates the existing gist through `gh api` when a gist ID already exists.
6. Installs this cron entry automatically on first run:

```text
*/30 * * * * ./scripts/backup_to_gist.sh
```

The script has a `#!/bin/bash` shebang and is executable.

## Runtime

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Telegram bot:

```bash
python3 bot.py
```

The bot module can be imported without `python-telegram-bot` installed. Running the bot without that dependency raises a clear setup error instead of failing at import time.

Run the API locally:

```bash
uvicorn api.main:app --reload
```

Run the web UI locally:

```bash
cd web
npm install
npm run dev
```

Build the web UI:

```bash
cd web
npm run build
```
