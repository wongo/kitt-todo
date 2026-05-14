#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$ROOT_DIR/data"
BACKUP_FILE="$DATA_DIR/backup.json"
GIST_ID_FILE="$DATA_DIR/.gist_id"
CRON_MARKER="# KITT-TODO backup"
CRON_LINE="*/30 * * * * $ROOT_DIR/scripts/backup_to_gist.sh $CRON_MARKER"

mkdir -p "$DATA_DIR"

cd "$ROOT_DIR"
python3 - <<'PY'
import db

db.export_backup()
PY

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required for GitHub Gist backup" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "gh CLI is not authenticated. Run: gh auth login" >&2
  exit 1
fi

GIST_ID=""
if [[ -s "$GIST_ID_FILE" ]]; then
  GIST_ID="$(tr -d '[:space:]' < "$GIST_ID_FILE")"
fi

if [[ -z "$GIST_ID" ]]; then
  GIST_ID="$(gh gist create "$BACKUP_FILE" -f backup.json -d "KITT-TODO backup" | awk -F/ '{print $NF}')"
  echo "$GIST_ID" > "$GIST_ID_FILE"
else
  CONTENT_JSON="$(python3 - <<'PY'
import json
from pathlib import Path

print(json.dumps(Path("data/backup.json").read_text(encoding="utf-8")))
PY
)"
  gh api --method PATCH "gists/$GIST_ID" \
    --input - >/dev/null <<JSON
{"files":{"backup.json":{"content":$CONTENT_JSON}}}
JSON
fi

if ! (crontab -l 2>/dev/null || true) | grep -F "$CRON_MARKER" >/dev/null; then
  (crontab -l 2>/dev/null || true; echo "$CRON_LINE") | crontab -
  echo "Installed cron entry: $CRON_LINE"
fi

echo "Backup complete: $BACKUP_FILE"
