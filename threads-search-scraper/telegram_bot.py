#!/usr/bin/env python3

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import List

import httpx

from constants import (
    DEFAULT_AUTH_FILE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_MAX_POSTS_NEW_KEYWORD,
    DEFAULT_SCROLL_ATTEMPTS,
    KEYWORDS_FILE,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
KEYWORDS_PATH = BASE_DIR / KEYWORDS_FILE
SCRAPER_PATH = BASE_DIR / "threads_scraper.py"
API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

_pending_action = {}


def load_keywords() -> List[str]:
    if KEYWORDS_PATH.exists():
        try:
            data = json.loads(KEYWORDS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [x.strip() for x in data if isinstance(x, str) and x.strip()]
        except Exception:
            pass
    return []


def save_keywords(keywords: List[str]) -> None:
    KEYWORDS_PATH.write_text(
        json.dumps(keywords, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _post(method: str, **kwargs) -> dict:
    try:
        r = httpx.post(f"{API}/{method}", json=kwargs, timeout=30)
        return r.json()
    except Exception as e:
        logger.error("%s failed: %s", method, e)
        return {}


def send(chat_id, text: str, reply_markup=None, parse_mode="HTML") -> None:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    _post("sendMessage", **payload)


def answer_callback(callback_query_id: str) -> None:
    _post("answerCallbackQuery", callback_query_id=callback_query_id)


def main_menu_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "📋 Ключові слова", "callback_data": "list"},
                {"text": "▶️ Запустити", "callback_data": "run"},
            ],
            [
                {"text": "➕ Додати", "callback_data": "add_prompt"},
                {"text": "➖ Видалити", "callback_data": "remove_prompt"},
            ],
            [
                {"text": "📊 Статус", "callback_data": "status"},
            ],
        ]
    }


def remove_keyboard(keywords: List[str]):
    rows = [[{"text": f"❌ {kw}", "callback_data": f"del:{kw}"}] for kw in keywords]
    rows.append([{"text": "⬅️ Назад", "callback_data": "back"}])
    return {"inline_keyboard": rows}


def run_scraper(keywords: List[str]) -> str:
    if not keywords:
        return "Немає ключових слів для запуску."

    cmd = [
        sys.executable,
        str(SCRAPER_PATH),
        "--keywords",
        *keywords,
        "--auth",
        str(BASE_DIR / DEFAULT_AUTH_FILE),
        "--output",
        str(BASE_DIR / DEFAULT_OUTPUT_DIR),
        "--max-posts-new",
        str(DEFAULT_MAX_POSTS_NEW_KEYWORD),
        "--scroll-attempts",
        str(DEFAULT_SCROLL_ATTEMPTS),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(BASE_DIR),
        )
        if result.returncode != 0:
            tail = "\n".join((result.stderr or result.stdout).splitlines()[-15:])
            return f"❌ Скрейпер завершився з помилкою:\n<pre>{tail}</pre>"

        tail = "\n".join((result.stdout or "").splitlines()[-20:])
        return f"✅ Скрейпер завершився успішно:\n<pre>{tail}</pre>"
    except subprocess.TimeoutExpired:
        return "⏱ Скрейпер перевищив таймаут."
    except Exception as e:
        return f"❌ Помилка запуску: {e}"


def handle_message(msg: dict) -> None:
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()
    action = _pending_action.get(chat_id)

    if action == "add" and text and not text.startswith("/"):
        keywords = load_keywords()
        if text not in keywords:
            keywords.append(text)
            save_keywords(keywords)
            send(chat_id, f"✅ Додано: <b>{text}</b>")
        else:
            send(chat_id, f"ℹ️ Уже є: <b>{text}</b>")
        _pending_action.pop(chat_id, None)
        return

    if action == "remove" and text and not text.startswith("/"):
        keywords = load_keywords()
        if text in keywords:
            keywords.remove(text)
            save_keywords(keywords)
            send(chat_id, f"🗑 Видалено: <b>{text}</b>")
        else:
            send(chat_id, f"ℹ️ Не знайдено: <b>{text}</b>")
        _pending_action.pop(chat_id, None)
        return

    cmd = text.split(maxsplit=1)[0].lower() if text else ""

    if cmd in ("/start", "/menu"):
        send(
            chat_id,
            "👋 <b>Threads Monitor</b>\nОбери дію:",
            reply_markup=main_menu_keyboard(),
        )

    elif cmd == "/list":
        keywords = load_keywords()
        if keywords:
            body = "\n".join(f"• {kw}" for kw in keywords)
            send(chat_id, f"📋 <b>Ключові слова:</b>\n{body}")
        else:
            send(chat_id, "Список поки порожній.")

    elif cmd == "/add":
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            _pending_action[chat_id] = "add"
            send(chat_id, "Напиши keyword одним повідомленням.")
            return
        kw = parts[1].strip()
        keywords = load_keywords()
        if kw not in keywords:
            keywords.append(kw)
            save_keywords(keywords)
        send(chat_id, f"✅ Додано: <b>{kw}</b>")

    elif cmd == "/remove":
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            kws = load_keywords()
            if kws:
                send(chat_id, "Обери keyword для видалення:", reply_markup=remove_keyboard(kws))
            else:
                send(chat_id, "Список порожній.")
            return
        kw = parts[1].strip()
        keywords = load_keywords()
        if kw in keywords:
            keywords.remove(kw)
            save_keywords(keywords)
        send(chat_id, f"🗑 Видалено: <b>{kw}</b>")

    elif cmd == "/run":
        keywords = load_keywords()
        send(chat_id, f"⏳ Запуск для {len(keywords)} keyword(ів)...")
        result_msg = run_scraper(keywords)
        send(chat_id, result_msg)

    elif cmd == "/status":
        summary_path = BASE_DIR / DEFAULT_OUTPUT_DIR / "threads_search_summary.json"
        if not summary_path.exists():
            send(chat_id, "Ще не було запусків.")
            return
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            send(
                chat_id,
                f"📊 <b>Останній запуск</b>\n"
                f"• Keywordів: {data.get('keywords_count', 0)}\n"
                f"• Нових постів: {data.get('all_new_posts_count', 0)}",
            )
        except Exception:
            send(chat_id, "Не вдалося прочитати summary.")

    else:
        if text and not text.startswith("/"):
            send(chat_id, "Напиши /start, щоб відкрити меню.")


def handle_callback(cb: dict) -> None:
    chat_id = cb["message"]["chat"]["id"]
    data = cb.get("data", "")
    answer_callback(cb["id"])

    if data == "list":
        keywords = load_keywords()
        if keywords:
            body = "\n".join(f"• {kw}" for kw in keywords)
            send(chat_id, f"📋 <b>Ключові слова:</b>\n{body}")
        else:
            send(chat_id, "Список порожній.")

    elif data == "run":
        keywords = load_keywords()
        send(chat_id, f"⏳ Запуск для {len(keywords)} keyword(ів)...")
        result_msg = run_scraper(keywords)
        send(chat_id, result_msg)

    elif data == "add_prompt":
        _pending_action[chat_id] = "add"
        send(chat_id, "Напиши keyword для додавання.")

    elif data == "remove_prompt":
        kws = load_keywords()
        if kws:
            send(chat_id, "Обери keyword для видалення:", reply_markup=remove_keyboard(kws))
        else:
            send(chat_id, "Список порожній.")

    elif data.startswith("del:"):
        kw = data[4:]
        keywords = load_keywords()
        if kw in keywords:
            keywords.remove(kw)
            save_keywords(keywords)
        send(chat_id, f"🗑 Видалено: <b>{kw}</b>")

    elif data == "status":
        summary_path = BASE_DIR / DEFAULT_OUTPUT_DIR / "threads_search_summary.json"
        if not summary_path.exists():
            send(chat_id, "Ще не було запусків.")
            return
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            send(
                chat_id,
                f"📊 <b>Останній запуск</b>\n"
                f"• Keywordів: {data.get('keywords_count', 0)}\n"
                f"• Нових постів: {data.get('all_new_posts_count', 0)}",
            )
        except Exception:
            send(chat_id, "Не вдалося прочитати summary.")

    elif data == "back":
        send(chat_id, "👋 <b>Threads Monitor</b>\nОбери дію:", reply_markup=main_menu_keyboard())


def run_polling():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is empty")

    logger.info("Bot started...")
    offset = 0

    while True:
        try:
            resp = _post(
                "getUpdates",
                offset=offset,
                timeout=30,
                allowed_updates=["message", "callback_query"],
            )
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