from __future__ import annotations

import re
import shlex
from datetime import datetime

import api_client

try:
    from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters
except ImportError:  # pragma: no cover - lets modules import without optional bot deps.
    CommandHandler = ConversationHandler = MessageHandler = filters = None


EDIT_TASK_ID, EDIT_TITLE = range(2)
PRIORITY_ICON = {"high": "🔥", "medium": "⚡", "low": "💤"}


def _parse_flags(tokens: list[str]) -> tuple[list[str], dict[str, str]]:
    words: list[str] = []
    flags: dict[str, str] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("--") and index + 1 < len(tokens):
            key = token[2:]
            value = tokens[index + 1]
            if key == "due" and index + 2 < len(tokens) and re.fullmatch(r"\d{1,2}:\d{2}", tokens[index + 2]):
                value = f"{value} {tokens[index + 2]}"
                index += 3
            else:
                index += 2
            flags[key] = value
        else:
            words.append(token)
            index += 1
    return words, flags


def _split_command_text(text: str) -> list[str]:
    try:
        return shlex.split(text)
    except ValueError:
        return text.split()


def _parse_due(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    if " " in value:
        due_date, due_time = value.split(None, 1)
        return due_date, due_time[:5]
    return value, None


def _format_task(task: dict) -> str:
    due = ""
    if task.get("due_date"):
        due_text = task["due_date"]
        if task.get("due_time"):
            due_text += f" {task['due_time']}"
        try:
            due_dt = datetime.fromisoformat(due_text if task.get("due_time") else f"{due_text} 23:59")
            if due_dt < datetime.now():
                due_text += " OVERDUE"
        except ValueError:
            pass
        due = f" | due {due_text}"
    category = f" | #{task['category']}" if task.get("category") else ""
    repeat = f" | repeat {task['repeat_type']}" if task.get("repeat_type") else ""
    return f"{PRIORITY_ICON.get(task['priority'], '⚡')} `{task['id']}` {task['title']}{category}{due}{repeat}"


def format_task_list(tasks: list[dict]) -> str:
    if not tasks:
        return "No pending tasks."
    sections: list[str] = []
    for priority in ("high", "medium", "low"):
        items = [task for task in tasks if task["priority"] == priority]
        if items:
            sections.append(f"{PRIORITY_ICON[priority]} {priority.upper()}\n" + "\n".join(_format_task(task) for task in items))
    return "\n\n".join(sections)


async def add_task(update, context) -> None:
    tokens = _split_command_text(update.message.text)[1:]
    words, flags = _parse_flags(tokens)
    due_date, due_time = _parse_due(flags.get("due"))
    task = api_client.create_task(
        title=" ".join(words),
        priority=flags.get("priority", "medium"),
        category=flags.get("category"),
        due_date=due_date,
        due_time=due_time,
        repeat_type=flags.get("repeat"),
    )
    if task is None:
        await update.message.reply_text("Service temporarily unavailable.")
        return
    await update.message.reply_text(f"Added {_format_task(task)}", parse_mode="Markdown")


async def list_task_command(update, context) -> None:
    tokens = _split_command_text(update.message.text)[1:]
    _, flags = _parse_flags(tokens)
    tasks = api_client.list_tasks(category=flags.get("category"))
    if tasks is None:
        await update.message.reply_text("Service temporarily unavailable.")
        return
    await update.message.reply_text(format_task_list(tasks), parse_mode="Markdown")


async def overdue(update, context) -> None:
    tasks = api_client.list_tasks(status="pending")
    if tasks is None:
        await update.message.reply_text("Service temporarily unavailable.")
        return
    now = datetime.now()
    overdue = []
    for task in tasks:
        if not task.get("due_date"):
            continue
        try:
            due_dt = datetime.fromisoformat(f"{task['due_date']} {task.get('due_time', '23:59')}")
            if due_dt < now:
                overdue.append(task)
        except ValueError:
            pass
    await update.message.reply_text(format_task_list(overdue), parse_mode="Markdown")


async def done(update, context) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /done <task_id>")
        return
    task = api_client.mark_task_done(context.args[0])
    if task is None:
        await update.message.reply_text("Task not found or service unavailable.")
        return
    await update.message.reply_text(f"Done: {task['title']}")


async def delete(update, context) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /delete <task_id>")
        return
    if api_client.delete_task(context.args[0]):
        await update.message.reply_text("Deleted.")
    else:
        await update.message.reply_text("Task not found or service unavailable.")


async def edit_start(update, context):
    args = context.args
    if len(args) >= 2:
        result = api_client.update_task(args[0], title=" ".join(args[1:]))
        ok = result is not None
        await update.message.reply_text("Updated." if ok else "Task not found.")
        return ConversationHandler.END
    if len(args) == 1:
        context.user_data["edit_task_id"] = args[0]
        await update.message.reply_text("Send the new title.")
        return EDIT_TITLE
    await update.message.reply_text("Send the task ID to edit.")
    return EDIT_TASK_ID


async def edit_receive_task_id(update, context):
    context.user_data["edit_task_id"] = update.message.text.strip()
    await update.message.reply_text("Send the new title.")
    return EDIT_TITLE


async def edit_receive_title(update, context):
    task_id = context.user_data.pop("edit_task_id", "")
    result = api_client.update_task(task_id, title=update.message.text.strip())
    await update.message.reply_text("Updated." if result else "Task not found.")
    return ConversationHandler.END


async def cancel(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


def task_handlers() -> list:
    if CommandHandler is None:
        return []
    return [
        CommandHandler("add", add_task),
        CommandHandler("list", list_task_command),
        CommandHandler("overdue", overdue),
        CommandHandler("done", done),
        CommandHandler("delete", delete),
    ]


def edit_conversation_handler():
    if ConversationHandler is None:
        return None
    return ConversationHandler(
        entry_points=[CommandHandler("edit", edit_start)],
        states={
            EDIT_TASK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_task_id)],
            EDIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_title)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
