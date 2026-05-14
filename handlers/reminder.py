from __future__ import annotations

from datetime import datetime

import api_client

try:
    from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters
except ImportError:  # pragma: no cover
    CommandHandler = ConversationHandler = MessageHandler = filters = None


REMIND_TASK_ID, REMIND_TIME = range(2)


def reminder_iso_for_today(hhmm: str) -> str:
    datetime.strptime(hhmm, "%H:%M")
    today = datetime.now().date().isoformat()
    return f"{today}T{hhmm}:00"


async def _save_reminder(update, task_id: str, hhmm: str) -> None:
    # Check task exists via API
    task = api_client.get_task(task_id)
    if task is None:
        await update.message.reply_text("Task not found.")
        return
    reminder = api_client.create_reminder(task_id, reminder_iso_for_today(hhmm), chat_id=str(update.effective_chat.id))
    if reminder is None:
        await update.message.reply_text("Could not set reminder. Please try again.")
        return
    await update.message.reply_text(f"Reminder set for {reminder['remind_at'][11:16]}.")


async def remind_start(update, context):
    if len(context.args) >= 2:
        await _save_reminder(update, context.args[0], context.args[1])
        return ConversationHandler.END
    if len(context.args) == 1:
        context.user_data["remind_task_id"] = context.args[0]
        await update.message.reply_text("Send reminder time as HH:MM.")
        return REMIND_TIME
    await update.message.reply_text("Send the task ID to remind.")
    return REMIND_TASK_ID


async def remind_receive_task_id(update, context):
    context.user_data["remind_task_id"] = update.message.text.strip()
    await update.message.reply_text("Send reminder time as HH:MM.")
    return REMIND_TIME


async def remind_receive_time(update, context):
    task_id = context.user_data.pop("remind_task_id", "")
    try:
        await _save_reminder(update, task_id, update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Use HH:MM, for example 09:30.")
    return ConversationHandler.END


async def cancel(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


def remind_conversation_handler():
    if ConversationHandler is None:
        return None
    return ConversationHandler(
        entry_points=[CommandHandler("remind", remind_start)],
        states={
            REMIND_TASK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, remind_receive_task_id)],
            REMIND_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, remind_receive_time)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
