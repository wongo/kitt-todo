#!/usr/bin/env python3
"""
KITT-TODO Backup Script
Exports all tasks/categories/reminders to JSON and backs up to GitHub.
Run via cron: /Users/nickwengsoocii/.hermes/scripts/kitt_todo_backup.sh
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path("/Users/nickwengsoocii/kitt-todo")
API_BASE = os.environ.get("KITT_TODO_API", "https://kitt-todo-api.onrender.com")
BACKUP_DIR = REPO_ROOT / "backups"


def api_get(endpoint: str) -> list | dict:
    import urllib.request

    url = f"{API_BASE}{endpoint}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read())


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result


def main() -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] KITT-TODO backup starting...")

    BACKUP_DIR.mkdir(exist_ok=True)

    try:
        data: dict[str, object] = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "tasks": api_get("/api/tasks"),
            "categories": api_get("/api/categories"),
            "reminders": api_get("/api/reminders/due"),
        }
    except Exception as exc:
        print(f"  Failed to fetch from API: {exc}")
        sys.exit(1)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    backup_file = BACKUP_DIR / f"kitt-todo-backup-{timestamp}.json"
    backup_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"  Wrote {backup_file.name} ({len(data['tasks'])} tasks)")

    latest = BACKUP_DIR / "latest.json"
    latest.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    git = ["git", "-C", str(REPO_ROOT)]
    git_config = ["-c", "user.name=Nick Weng", "-c", "user.email=wongo.w@gmail.com"]

    run(git + ["add", "backups/"])
    status = run(git + git_config + ["status", "--porcelain"])

    if status.stdout.strip():
        msg = f"Auto-backup {timestamp}"
        run(git + git_config + ["commit", "-m", msg])
        print("  Committed.")
        result = run(git + ["push", "origin", "main"])
        if result.returncode == 0:
            print("  Pushed to GitHub.")
        else:
            print(f"  Push failed: {result.stderr[:300]}")
            sys.exit(1)
    else:
        print("  No changes to commit.")


if __name__ == "__main__":
    main()