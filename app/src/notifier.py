"""Telegram notifications."""
from __future__ import annotations

import os
import httpx

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def notify(message: str) -> None:
    if not TOKEN or not CHAT_ID:
        print(f"[notify] {message}")
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as e:
        print(f"[notifier] failed: {e}")


def notify_error(title: str, exc: Exception) -> None:
    notify(f"*{title}*\n```\n{exc}\n```")
