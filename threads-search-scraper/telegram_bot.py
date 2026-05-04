#!/usr/bin/env python3
"""
Telegram-бот для керування Threads-парсером.

Команди:
  /start        — головне меню з кнопками
  /list         — список ключових слів
  /add <слово>  — додати ключове слово
  /remove <слово> — видалити ключове слово
  /run          — запустити парсинг зараз
  /status       — статус останнього запуску
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import List

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------- config ----------
from constants import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    KEYWORDS_FILE,
    DEFAULT_AUTH_FILE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_MAX_POSTS_NEW_KEYWORD,
    DEFAULT_SCROLL_ATTEMPTS,
)

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is empty")

if not TELEGRAM_CHAT_ID:
    raise RuntimeError("TELEGRAM_CHAT_ID is empty")

if not KEYWORDS_FILE:
    raise RuntimeError("KEYWORDS_FILE is empty")

API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ---------- keywords store ----------

def load_keywords() -> List[str]:
    p = Path(KEYWORDS_FILE)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return []


def save_keywords(kws: List[str]) -> None:
    Path(KEYWORDS_FILE).write_text(
        json.dumps(kws, ensure_ascii=False, indent=2), encoding="utf-8"
    )

# ---------- Telegram helpers ----------

def _post(method: str, **kwargs) -> dict:
    try:
        r = httpx.post(f"{API}/{method}", json=kwargs, timeout=15)
        return r.json()
    except Exception as e:
        logger.error("API error %s: %s", method, e)
        return {}


def send(chat_id, text: str, reply_markup=None, parse_mode="MarkdownV2") -> None:
    params = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        params["reply_markup"] = reply_markup
    _post("sendMessage", **params)


def main_menu_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "📋 Ключові слова", "callback_data": "list"},
                {"text": "▶️ Запустити", "callback_data": "run"},
            ],
            [
                {"text": "➕ Додати слово", "callback_data": "add_prompt"},
                {"text": "➖ Видалити слово", "callback_data": "remove_prompt"},
            ],
            [
                {"text": "📊 Статус", "callback_data": "status"},
            ],
        ]
    }


def keywords_remove_keyboard(keywords: List[str]):
    """Inline-кнопки для видалення: одна кнопка = одне слово."""
    buttons = [
        [{"text": f"❌ {kw}", "callback_data": f"del:{kw}"}]
        for kw in keywords
    ]
    buttons.append([{"text": "« Назад", "callback_data": "back"}])
    return {"inline_keyboard": buttons}

# ---------- scraper runner ----------

def run_scraper(keywords: List[str]) -> str:
    if not keywords:
        return "⚠️ Немає ключових слів для пошуку\\."
    cmd = [
        sys.executable, "threads_scraper.py",
        "--keywords", *keywords,
        "--auth", DEFAULT_AUTH_FILE,
        "--output", DEFAULT_OUTPUT_DIR,
        "--max-posts-new", str(DEFAULT_MAX_POSTS_NEW_KEYWORD),
        "--scroll-attempts", str(DEFAULT_SCROLL_ATTEMPTS),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        last_lines = "\n".join(result.stdout.strip().splitlines()[-15:])
        return f"✅ Готово\\!\n```\n{last_lines}\n```"
    except subprocess.TimeoutExpired:
        return "⏱ Парсинг перевищив 5 хвилин — перевір вручну\\."
    except Exception as e:
        return f"❌ Помилка запуску: {e}"

# ---------- update handlers ----------

_pending_action: dict = {}   # chat_id -> "add" | "remove"


def handle_message(msg: dict) -> None:
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()

    # якщо очікуємо введення від юзера
    action = _pending_action.get(chat_id)
    if action == "add" and text and not text.startswith("/"):
        kws = load_keywords()
        if text not in kws:
            kws.append(text)
            save_keywords(kws)
            send(chat_id, f"✅ Додано: *{text}*", parse_mode="Markdown")
        else:
            send(chat_id, f"ℹ️ *{text}* вже є у списку\\.", parse_mode="MarkdownV2")
        _pending_action.pop(chat_id, None)
        return

    cmd = text.split()[0].lower() if text else ""

    if cmd in ("/start", "/menu"):
        send(chat_id, "👋 *Threads Monitor*\nОбери дію:", reply_markup=main_menu_keyboard())

    elif cmd == "/list":
        kws = load_keywords()
        if kws:
            body = "\n".join(f"• {kw}" for kw in kws)
            send(chat_id, f"📋 *Ключові слова:*\n{body}", parse_mode="Markdown")
        else:
            send(chat_id, "Список порожній\\. Додай слова через /add або кнопку\\.")

    elif cmd == "/add":
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            _pending_action[chat_id] = "add"
            send(chat_id, "✏️ Введи ключове слово для додавання:")
            return
        kw = parts[1].strip()
        kws = load_keywords()
        if kw not in kws:
            kws.append(kw)
            save_keywords(kws)
        send(chat_id, f"✅ Додано: *{kw}*", parse_mode="Markdown")

    elif cmd == "/remove":
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            kws = load_keywords()
            send(chat_id, "Обери слово для видалення:", reply_markup=keywords_remove_keyboard(kws))
            return
        kw = parts[1].strip()
        kws = load_keywords()
        if kw in kws:
            kws.remove(kw)
            save_keywords(kws)
            send(chat_id, f"🗑 Видалено: *{kw}*", parse_mode="Markdown")
        else:
            send(chat_id, f"ℹ️ *{kw}* не знайдено\\.")

    elif cmd == "/run":
        kws = load_keywords()
        send(chat_id, f"⏳ Запускаю парсинг для {len(kws)} слів\\.\\.\\.", parse_mode="MarkdownV2")
        result_msg = run_scraper(kws)
        send(chat_id, result_msg)

    elif cmd == "/status":
        summary_path = Path(DEFAULT_OUTPUT_DIR) / "threads_search_summary.json"
        if not summary_path.exists():
            send(chat_id, "📭 Ще не було запусків\\.")
            return
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        total = data.get("all_new_posts_count", 0)
        kw_count = data.get("keywords_count", 0)
        send(chat_id, f"📊 Останній запуск:\n*{kw_count}* ключових слів, *{total}* нових постів\\.", parse_mode="MarkdownV2")


def handle_callback(cb: dict) -> None:
    chat_id = cb["message"]["chat"]["id"]
    data = cb.get("data", "")
    _post("answerCallbackQuery", callback_query_id=cb["id"])

    if data == "list":
        kws = load_keywords()
        body = "\n".join(f"• {kw}" for kw in kws) if kws else "Список порожній"
        send(chat_id, f"📋 *Ключові слова:*\n{body}", parse_mode="Markdown")

    elif data == "run":
        kws = load_keywords()
        send(chat_id, f"⏳ Запускаю\\.\\.\\.", parse_mode="MarkdownV2")
        result_msg = run_scraper(kws)
        send(chat_id, result_msg)

    elif data == "add_prompt":
        _pending_action[chat_id] = "add"
        send(chat_id, "✏️ Введи ключове слово для додавання:")

    elif data == "remove_prompt":
        kws = load_keywords()
        if not kws:
            send(chat_id, "Список порожній\\.")
        else:
            send(chat_id, "Обери слово для видалення:", reply_markup=keywords_remove_keyboard(kws))

    elif data.startswith("del:"):
        kw = data[4:]
        kws = load_keywords()
        if kw in kws:
            kws.remove(kw)
            save_keywords(kws)
        send(chat_id, f"🗑 Видалено: *{kw}*", parse_mode="Markdown")

    elif data == "status":
        summary_path = Path(DEFAULT_OUTPUT_DIR) / "threads_search_summary.json"
        if not summary_path.exists():
            send(chat_id, "📭 Ще не було запусків\\.")
            return
        d = json.loads(summary_path.read_text(encoding="utf-8"))
        total = d.get("all_new_posts_count", 0)
        kw_count = d.get("keywords_count", 0)
        send(chat_id, f"📊 Останній запуск: *{kw_count}* слів, *{total}* постів\\.", parse_mode="MarkdownV2")

    elif data == "back":
        send(chat_id, "👋 *Threads Monitor*\nОбери дію:", reply_markup=main_menu_keyboard())


# ---------- polling loop ----------

def run_polling():
    logger.info("Bot started (long polling)...")
    offset = 0
    while True:
        try:
            resp = _post("getUpdates", offset=offset, timeout=30, allowed_updates=["message", "callback_query"])
            for update in resp.get("result", []):
                offset = update["update_id"] + 1
                if "message" in update:
                    handle_message(update["message"])
                elif "callback_query" in update:
                    handle_callback(update["callback_query"])
        except KeyboardInterrupt:
            logger.info("Stopped.")
            break
        except Exception as e:
            logger.error("Polling error: %s", e)


if __name__ == "__main__":
    run_polling()