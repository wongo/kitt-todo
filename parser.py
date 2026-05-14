from __future__ import annotations

import re
from datetime import date, datetime, timedelta


QUICK_ADD_MARKERS = ("幫我記下", "記下", "新增待辦")


def _extract_priority(text: str) -> str:
    if "重要" in text or "急" in text:
        return "high"
    if "慢慢來" in text:
        return "low"
    return "medium"


def _extract_date(text: str, today: date | None = None) -> str | None:
    today = today or date.today()
    if "明天" in text:
        return (today + timedelta(days=1)).isoformat()
    if "下週" in text:
        return (today + timedelta(days=7)).isoformat()
    if "今天" in text:
        return today.isoformat()
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if match:
        return match.group(1)
    return None


def _extract_time(text: str) -> str | None:
    hhmm = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", text)
    if hhmm:
        return f"{int(hhmm.group(1)):02d}:{hhmm.group(2)}"

    zh = re.search(r"(上午|早上|下午|晚上)?\s*([0-2]?\d)點(?:([0-5]\d)分?)?", text)
    if not zh:
        return None

    meridiem, hour_text, minute_text = zh.groups()
    hour = int(hour_text)
    minute = int(minute_text or "0")
    if meridiem in {"下午", "晚上"} and hour < 12:
        hour += 12
    if meridiem in {"上午", "早上"} and hour == 12:
        hour = 0
    if hour > 23:
        return None
    return f"{hour:02d}:{minute:02d}"


def _strip_command_words(text: str) -> str:
    title = text.strip()
    for marker in QUICK_ADD_MARKERS:
        title = title.replace(marker, " ")
    for word in ("KITT", "重要", "急", "慢慢來", "今天", "明天", "下週"):
        title = title.replace(word, " ")
    title = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", title)
    title = re.sub(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", " ", title)
    title = re.sub(r"(上午|早上|下午|晚上)?\s*[0-2]?\d點(?:[0-5]\d分?)?", " ", title)
    title = re.sub(r"\s+", " ", title).strip(" ，,。")
    return title


def parse_quick_add(text: str) -> dict[str, str | None] | None:
    if not any(marker in text for marker in QUICK_ADD_MARKERS):
        return None

    title = _strip_command_words(text)
    if not title:
        return None

    return {
        "title": title,
        "priority": _extract_priority(text),
        "due_date": _extract_date(text),
        "due_time": _extract_time(text),
        "category": None,
    }
