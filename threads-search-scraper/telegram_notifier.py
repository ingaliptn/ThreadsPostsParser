import html
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

THREADS_POST_URL = "https://www.threads.net/@{username}/post/{code}"
THREADS_PROFILE_URL = "https://www.threads.net/@{username}"
MAX_TEXT_LEN = 900


def escape_html(text: Optional[str]) -> str:
    return html.escape(text or "", quote=False)


def build_post_url(post: Dict[str, Any]) -> Optional[str]:
    username = post.get("username")
    code = post.get("post_code")
    if username and code:
        return THREADS_POST_URL.format(username=username, code=code)
    return None


def build_profile_url(post: Dict[str, Any]) -> Optional[str]:
    username = post.get("username")
    if username:
        return THREADS_PROFILE_URL.format(username=username)
    return None


def shorten_text(text: Optional[str], max_len: int = MAX_TEXT_LEN) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "…"


def format_post_html(post: Dict[str, Any], keyword: str) -> str:
    username = escape_html(post.get("username") or "unknown")
    full_name = escape_html(post.get("full_name") or post.get("username") or "unknown")
    text = escape_html(shorten_text(post.get("text")))
    likes = post.get("like_count", 0)
    replies = post.get("reply_count", 0)
    quotes = post.get("quote_count", 0)
    reposts = post.get("repost_count", 0)
    verified = " ✅" if post.get("is_verified") else ""

    parts = [
        "🔍 <b>Нове співпадіння в Threads</b>",
        f"🗝 <b>Ключ:</b> {escape_html(keyword)}",
        f"👤 <b>Автор:</b> {full_name} (@{username}){verified}",
    ]

    if text:
        parts.append("")
        parts.append(f"<blockquote>{text}</blockquote>")

    parts.append("")
    parts.append(
        f"📊 <b>Метрики:</b> ❤️ {likes} | 💬 {replies} | 🔁 {reposts} | 🗨 {quotes}"
    )

    return "\n".join(parts)


def build_post_keyboard(post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    buttons = []

    post_url = build_post_url(post)
    profile_url = build_profile_url(post)

    row = []
    if post_url:
        row.append({"text": "🔗 Відкрити пост", "url": post_url})
    if profile_url:
        row.append({"text": "👤 Профіль", "url": profile_url})

    if row:
        buttons.append(row)

    if not buttons:
        return None

    return {"inline_keyboard": buttons}


def send_message(
    token: str,
    chat_id: str,
    text: str,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        resp = httpx.post(url, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return bool(data.get("ok"))
    except Exception as e:
        logger.error("Telegram send error: %s", e)
        return False


def send_post(token: str, chat_id: str, post: Dict[str, Any], keyword: str) -> bool:
    text = format_post_html(post, keyword)
    keyboard = build_post_keyboard(post)
    return send_message(token, chat_id, text, reply_markup=keyboard)


def send_posts(token: str, chat_id: str, posts: List[Dict[str, Any]], keyword: str) -> int:
    sent = 0
    for post in posts:
        if send_post(token, chat_id, post, keyword):
            sent += 1
    return sent


def send_summary(token: str, chat_id: str, summary: Dict[str, Any]) -> bool:
    lines = [
        "📦 <b>Підсумок сканування Threads</b>",
        f"🔢 <b>Ключових слів:</b> {summary.get('keywords_count', 0)}",
        f"📬 <b>Усього нових постів:</b> {summary.get('all_new_posts_count', 0)}",
        "",
    ]

    for item in summary.get("results", []):
        keyword = escape_html(item.get("keyword", ""))
        if item.get("error"):
            lines.append(f"❌ <b>{keyword}</b> — помилка: {escape_html(str(item['error']))}")
        else:
            lines.append(
                f"• <b>{keyword}</b>: нових {item.get('posts_count_new', 0)}, "
                f"усього побачено {item.get('posts_count_total_seen', 0)}"
            )

    return send_message(token, chat_id, "\n".join(lines))