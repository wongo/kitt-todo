import os

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

BOT_TOKEN = os.getenv("KITT_TODO_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
GIST_ID_FILE = os.path.join(DATA_DIR, ".gist_id")
DB_PATH = os.path.join(DATA_DIR, "kitt_todo.db")
BACKUP_JSON_PATH = os.path.join(DATA_DIR, "backup.json")
