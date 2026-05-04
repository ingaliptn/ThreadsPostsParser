#!/usr/bin/env python3

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any

import httpx

from constants import (
    DEFAULT_AUTH_FILE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_MAX_POSTS_NEW_KEYWORD,
    DEFAULT_SCROLL_ATTEMPTS,
    KEYWORDS_FILE,
    TELEGRAM_BOT_TOKEN,
    LOG_CHAT_ID,
    SEND_RUN_LOG_TO_USER,
    SEND_SUMMARY_TO_USER,
)
from telegram_notifier import send_post, send_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
KEYWORDS_PATH = BASE_DIR / KEYWORDS_FILE
SCRAPER_PATH = BASE_DIR / "threads_scraper.py"
SUMMARY_PATH = BASE_DIR / DEFAULT_OUTPUT_DIR / "threads_search_summary.json"
API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

_pending_action: Dict[int, str] = {}


def load_keywords() -> List[str]:
    if KEYWORDS_PATH.exists():
        try:
            data = json.loads(KEYWORDS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [x.strip() for x in data if isinstance(x, str) and x.strip()]
        except Exception as e:
            logger.error("Failed to load keywords: %s", e)
    return []


def save_keywords(keywords: List[str]) -> None:
    KEYWORDS_PATH.write_text(
        json.dumps(keywords, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _post(method: str, **kwargs) -> dict:
    try:
        r = httpx.post(f"{API}/{method}", json=kwargs, timeout=35)
        data = r.json()
        if not data.get("ok", False):
            logger.error("Telegram API %s error: %s", method, data)
        return data
    except Exception as e:
        logger.error("%s failed: %s", method, e)
        return {}


def send(chat_id, text: str, reply_markup=None, parse_mode="HTML") -> None:
    payload = {
        "chat_id": str(chat_id),
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    _post("sendMessage", **payload)


def answer_callback(callback_query_id: str) -> None:
    _post("answerCallbackQuery", callback_query_id=callback_query_id)


def escape_html(text: Any) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


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


def load_last_summary() -> Dict[str, Any]:
    if not SUMMARY_PATH.exists():
        logger.error("Summary file not found: %s", SUMMARY_PATH)
        return {}
    try:
        return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("Failed to load summary: %s", e)
        return {}


def run_scraper(keywords: List[str]) -> Dict[str, Any]:
    if not keywords:
        return {
            "ok": False,
            "message": "Немає ключових слів для запуску.",
            "stdout_tail": "",
            "stderr_tail": "",
        }

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

        stdout_tail = "\n".join((result.stdout or "").splitlines()[-30:])
        stderr_tail = "\n".join((result.stderr or "").splitlines()[-30:])

        if result.returncode != 0:
            return {
                "ok": False,
                "message": "Скрейпер завершився з помилкою.",
                "stdout_tail": stdout_tail,
                "stderr_tail": stderr_tail,
            }

        return {
            "ok": True,
            "message": "Скрейпер завершився успішно.",
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
        }

    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "message": "Скрейпер перевищив таймаут.",
            "stdout_tail": "",
            "stderr_tail": "",
        }
    except Exception as e:
        return {
            "ok": False,
            "message": f"Помилка запуску: {e}",
            "stdout_tail": "",
            "stderr_tail": "",
        }


def send_log_message(text: str) -> None:
    if not LOG_CHAT_ID:
        return
    send(LOG_CHAT_ID, text)


def deliver_summary_to_chat(target_chat_id) -> int:
    summary = load_last_summary()
    if not summary:
        logger.error("Summary is empty after scraper run")
        send(target_chat_id, "❌ Не вдалося прочитати summary після запуску.")
        return 0

    sent_posts = 0
    total_new = summary.get("all_new_posts_count", 0)
    logger.info("Deliver summary: all_new_posts_count=%s", total_new)

    for item in summary.get("results", []):
        if item.get("error"):
            logger.error("Result item error for keyword=%s error=%s", item.get("keyword"), item.get("error"))
            continue

        keyword = item.get("keyword", "")
        posts_new = item.get("posts_new", [])
        logger.info("Deliver keyword=%s posts_new=%s", keyword, len(posts_new))

        for post in posts_new:
            try:
                ok = send_post(
                    token=TELEGRAM_BOT_TOKEN,
                    chat_id=str(target_chat_id),
                    post=post,
                    keyword=keyword,
                )
                if ok:
                    sent_posts += 1
                else:
                    logger.error("send_post returned False for keyword=%s post_id=%s", keyword, post.get("post_id"))
            except Exception as e:
                logger.exception("send_post crashed for keyword=%s: %s", keyword, e)

    if SEND_SUMMARY_TO_USER:
        try:
            send_summary(
                token=TELEGRAM_BOT_TOKEN,
                chat_id=str(target_chat_id),
                summary=summary,
            )
        except Exception as e:
            logger.exception("send_summary crashed: %s", e)

    logger.info("Delivered posts to chat_id=%s count=%s", target_chat_id, sent_posts)
    return sent_posts


def send_run_result(chat_id, run_result: Dict[str, Any], sent_posts: int) -> None:
    if run_result["ok"]:
        if SEND_RUN_LOG_TO_USER:
            text = (
                f"✅ <b>{escape_html(run_result['message'])}</b>\n"
                f"Надіслано постів: <b>{sent_posts}</b>\n"
                f"<pre>{escape_html(run_result.get('stdout_tail', ''))}</pre>"
            )
            send(chat_id, text)
        else:
            send(chat_id, f"✅ Готово. Надіслано постів: <b>{sent_posts}</b>")
    else:
        text = f"❌ <b>{escape_html(run_result['message'])}</b>"
        details = run_result.get("stderr_tail", "") or run_result.get("stdout_tail", "")
        if details:
            text += f"\n<pre>{escape_html(details)}</pre>"
        send(chat_id, text)


def send_run_log(chat_id, run_result: Dict[str, Any], sent_posts: int) -> None:
    if not LOG_CHAT_ID:
        return

    status = "success" if run_result["ok"] else "error"
    details = run_result.get("stderr_tail", "") or run_result.get("stdout_tail", "")

    text = (
        f"<b>Threads Parser Bot Log</b>\n"
        f"<b>Status:</b> {escape_html(status)}\n"
        f"<b>User chat:</b> {escape_html(chat_id)}\n"
        f"<b>Sent posts:</b> {escape_html(sent_posts)}\n"
        f"<b>Message:</b> {escape_html(run_result['message'])}"
    )

    if details:
        text += f"\n<pre>{escape_html(details)}</pre>"

    send_log_message(text)


def execute_run_for_chat(chat_id) -> None:
    keywords = load_keywords()
    send(chat_id, f"⏳ Запуск для {len(keywords)} keyword(ів)...")

    run_result = run_scraper(keywords)

    sent_posts = 0
    if run_result["ok"]:
        sent_posts = deliver_summary_to_chat(chat_id)

    send_run_result(chat_id, run_result, sent_posts)
    send_run_log(chat_id, run_result, sent_posts)
    send(
            chat_id,
            "⚙️ <b>Керування</b>\nОбери наступну дію:",
            reply_markup=main_menu_keyboard(),
        )

def handle_message(msg: dict) -> None:
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()
    action = _pending_action.get(chat_id)

    if action == "add" and text and not text.startswith("/"):
        keywords = load_keywords()
        if text not in keywords:
            keywords.append(text)
            save_keywords(keywords)
            send(chat_id, f"✅ Додано: <b>{escape_html(text)}</b>")
        else:
            send(chat_id, f"ℹ️ Уже є: <b>{escape_html(text)}</b>")
        _pending_action.pop(chat_id, None)
        return

    cmd = text.split(maxsplit=1)[0].lower() if text else ""

    if cmd in ("/start", "/menu"):
        send(chat_id, "👋 <b>Threads Monitor</b>\nОбери дію:", reply_markup=main_menu_keyboard())

    elif cmd == "/list":
        keywords = load_keywords()
        if keywords:
            body = "\n".join(f"• {escape_html(kw)}" for kw in keywords)
            send(chat_id, f"📋 <b>Ключові слова:</b>\n{body}")
        else:
            send(chat_id, "Список поки порожній.")

    elif cmd == "/add":
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            _pending_action[chat_id] = "add"
            send(chat_id, "Напиши keyword для додавання.")
            return

        kw = parts[1].strip()
        keywords = load_keywords()
        if kw not in keywords:
            keywords.append(kw)
            save_keywords(keywords)
            send(chat_id, f"✅ Додано: <b>{escape_html(kw)}</b>")
        else:
            send(chat_id, f"ℹ️ Уже є: <b>{escape_html(kw)}</b>")

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
            send(chat_id, f"🗑 Видалено: <b>{escape_html(kw)}</b>")
        else:
            send(chat_id, f"ℹ️ Не знайдено: <b>{escape_html(kw)}</b>")

    elif cmd == "/run":
        execute_run_for_chat(chat_id)

    elif cmd == "/status":
        summary = load_last_summary()
        if not summary:
            send(chat_id, "Ще не було запусків.")
            return
        send(
            chat_id,
            f"📊 <b>Останній запуск</b>\n"
            f"• Keywordів: {summary.get('keywords_count', 0)}\n"
            f"• Нових постів: {summary.get('all_new_posts_count', 0)}",
        )

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
            body = "\n".join(f"• {escape_html(kw)}" for kw in keywords)
            send(chat_id, f"📋 <b>Ключові слова:</b>\n{body}")
        else:
            send(chat_id, "Список порожній.")

    elif data == "run":
        execute_run_for_chat(chat_id)

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
            send(chat_id, f"🗑 Видалено: <b>{escape_html(kw)}</b>")
        else:
            send(chat_id, f"ℹ️ Не знайдено: <b>{escape_html(kw)}</b>")

    elif data == "status":
        summary = load_last_summary()
        if not summary:
            send(chat_id, "Ще не було запусків.")
            return
        send(
            chat_id,
            f"📊 <b>Останній запуск</b>\n"
            f"• Keywordів: {summary.get('keywords_count', 0)}\n"
            f"• Нових постів: {summary.get('all_new_posts_count', 0)}",
        )

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