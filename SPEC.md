# KITT-TODO Specification

## System Overview

KITT-TODO is a Telegram-integrated task management system.

- Phase 1: Telegram bot using `python-telegram-bot` v22+
- Phase 2: Web UI, planned for a later phase
- Runtime language: Python 3.14
- Local database: SQLite at `./data/kitt_todo.db`
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
```

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
