from __future__ import annotations

import asyncio
import logging
import os
import threading
from datetime import datetime

import api_client
from parser import parse_quick_add

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    from handlers.category import category_handlers
    from handlers.reminder import remind_conversation_handler
    from handlers.task import edit_conversation_handler, task_handlers
except ImportError:  # pragma: no cover - importing bot.py should not require PTB.
    Application = CommandHandler = MessageHandler = filters = None
    category_handlers = remind_conversation_handler = task_handlers = edit_conversation_handler = None


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
LOGGER = logging.getLogger("kitt-todo")


async def start(update, context) -> None:
    await update.message.reply_text("KITT-TODO ready. Use /add, /list, /done, /category, /tag, or /remind.")


async def quick_add(update, context) -> None:
    parsed = parse_quick_add(update.message.text or "")
    if parsed is None:
        return
    task = api_client.create_task(**parsed)
    if task is None:
        await update.message.reply_text("Service temporarily unavailable. Please try again later.")
        return
    await update.message.reply_text(f"Added {task['id']}: {task['title']}")


def reminder_worker(application) -> None:
    stop_event: threading.Event = application.bot_data["reminder_stop_event"]
    loop = application.bot_data["event_loop"]
    while not stop_event.is_set():
        now = datetime.now().replace(microsecond=0).isoformat()
        reminders = api_client.get_due_reminders(now)
        if reminders is None:
            LOGGER.warning("Failed to fetch due reminders, will retry in 30s")
            stop_event.wait(30)
            continue
        for reminder in reminders:
            chat_id = reminder.get("chat_id")
            if not chat_id:
                api_client.mark_reminder_sent(reminder["id"])
                continue
            message = f"🔔 提醒：{reminder.get('title', '任務')}"
            future = asyncio.run_coroutine_threadsafe(
                application.bot.send_message(chat_id=chat_id, text=message),
                loop,
            )
            try:
                future.result(timeout=20)
                api_client.mark_reminder_sent(reminder["id"])
            except Exception:
                LOGGER.exception("Failed to send reminder %s", reminder["id"])
        stop_event.wait(30)


async def post_init(application) -> None:
    application.bot_data["event_loop"] = asyncio.get_running_loop()
    application.bot_data["reminder_stop_event"] = threading.Event()
    thread = threading.Thread(target=reminder_worker, args=(application,), daemon=True)
    application.bot_data["reminder_thread"] = thread
    thread.start()


async def post_shutdown(application) -> None:
    stop_event = application.bot_data.get("reminder_stop_event")
    if stop_event:
        stop_event.set()
    thread = application.bot_data.get("reminder_thread")
    if thread:
        thread.join(timeout=5)


def build_application():
    if load_dotenv:
        load_dotenv()
    if Application is None:
        raise RuntimeError("python-telegram-bot is not installed. Run: pip install -r requirements.txt")

    bot_token = os.getenv("KITT_TODO_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
    application = (
        Application.builder()
        .token(bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    application.add_handler(CommandHandler("start", start))

    for handler in task_handlers():
        application.add_handler(handler)
    edit_handler = edit_conversation_handler()
    if edit_handler:
        application.add_handler(edit_handler)
    for handler in category_handlers():
        application.add_handler(handler)
    remind_handler = remind_conversation_handler()
    if remind_handler:
        application.add_handler(remind_handler)

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, quick_add))
    return application


def main() -> None:
    app = build_application()
    app.run_polling()


if __name__ == "__main__":
    main()
