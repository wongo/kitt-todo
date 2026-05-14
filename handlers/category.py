from __future__ import annotations

from handlers.task import _parse_flags, _split_command_text

import api_client

try:
    from telegram.ext import CommandHandler
except ImportError:  # pragma: no cover
    CommandHandler = None


async def category(update, context) -> None:
    tokens = _split_command_text(update.message.text)[1:]
    if len(tokens) < 2 or tokens[0] != "add":
        await update.message.reply_text("Usage: /category add <name> [--icon emoji]")
        return
    words, flags = _parse_flags(tokens[1:])
    item = api_client.add_category(" ".join(words), icon=flags.get("icon", "📂"))
    if item is None:
        await update.message.reply_text("Service temporarily unavailable.")
        return
    await update.message.reply_text(f"Category saved: {item['icon']} {item['name']}")


async def tag(update, context) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /tag <task_id> <category>")
        return
    task_id, category_name = context.args[0], " ".join(context.args[1:])
    if api_client.get_category(category_name) is None:
        api_client.add_category(category_name)
    result = api_client.set_task_category(task_id, category_name)
    if result is not None:
        await update.message.reply_text("Tagged.")
    else:
        await update.message.reply_text("Task not found or service unavailable.")


async def categories(update, context) -> None:
    items = api_client.list_categories()
    if items is None:
        await update.message.reply_text("Service temporarily unavailable.")
        return
    if not items:
        await update.message.reply_text("No categories.")
        return
    await update.message.reply_text("\n".join(f"{item['icon']} {item['name']}" for item in items))


def category_handlers() -> list:
    if CommandHandler is None:
        return []
    return [
        CommandHandler("category", category),
        CommandHandler("tag", tag),
        CommandHandler("categories", categories),
    ]
