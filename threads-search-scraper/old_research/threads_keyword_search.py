import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright

KEYWORD = "python"
AUTH_FILE = "auth.json"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

class ThreadsSearchParser:
    def __init__(self):
        self.captured_responses: List[Dict[str, Any]] = []

    def response_handler(self, response):
        url = response.url.lower()
        if "graphql/query" not in url:
            return

        try:
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" not in content_type:
                return

            text = response.text()
            payload = None
            try:
                payload = json.loads(text)
            except Exception:
                pass

            self.captured_responses.append({
                "status": response.status,
                "url": response.url,
                "json": payload,
                "body_preview": text[:2000]
            })
        except Exception:
            pass

    def parse_users_from_item(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        result = []
        payload = item.get("json")
        if not isinstance(payload, dict):
            return result

        data_root = payload.get("data")
        if not isinstance(data_root, dict):
            return result

        users_conn = data_root.get("xdt_api__v1__users__search_connection")
        if not isinstance(users_conn, dict):
            return result

        for edge in users_conn.get("edges", []):
            node = edge.get("node", {})
            result.append({
                "username": node.get("username"),
                "pk": node.get("pk"),
                "full_name": node.get("full_name"),
                "is_verified": node.get("is_verified"),
                "is_private": node.get("text_post_app_is_private"),
                "has_threads": node.get("has_onboarded_to_text_post_app"),
                "profile_pic_url": node.get("profile_pic_url"),
                "follower_count": node.get("follower_count"),
            })

        return result

    def parse_posts_from_item(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        result = []
        payload = item.get("json")
        if not isinstance(payload, dict):
            return result

        data_root = payload.get("data")
        if not isinstance(data_root, dict):
            return result

        search_results = data_root.get("searchResults")
        if not isinstance(search_results, dict):
            return result

        tag_info = search_results.get("tag_info", {})
        tag_name = tag_info.get("display_name")
        tag_id = tag_info.get("id")

        for edge in search_results.get("edges", []):
            node = edge.get("node", {})
            thread = node.get("thread", {})
            thread_items = thread.get("thread_items", [])

            for thread_item in thread_items:
                post = thread_item.get("post", {})
                user = post.get("user", {})
                media_info = post.get("text_post_app_info", {})

                caption_text: Optional[str] = None
                caption = post.get("caption")
                if isinstance(caption, dict):
                    caption_text = caption.get("text")

                result.append({
                    "tag": tag_name,
                    "tag_id": tag_id,
                    "post_pk": post.get("pk"),
                    "post_code": post.get("code"),
                    "post_id": post.get("id"),
                    "text": caption_text,
                    "username": user.get("username"),
                    "user_pk": user.get("pk"),
                    "full_name": user.get("full_name"),
                    "is_verified": user.get("is_verified"),
                    "like_count": post.get("like_count"),
                    "reply_count": media_info.get("direct_reply_count"),
                    "quote_count": media_info.get("quote_count"),
                    "repost_count": media_info.get("repost_count"),
                })

        return result

    def parse_metric_blocks_from_item(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        result = []
        payload = item.get("json")
        if not isinstance(payload, dict):
            return result

        data_root = payload.get("data")
        if not isinstance(data_root, dict):
            return result

        nested_data = data_root.get("data")
        if not isinstance(nested_data, dict):
            return result

        posts = nested_data.get("posts")
        if not isinstance(posts, list):
            return result

        for post in posts:
            media_info = post.get("text_post_app_info", {})
            result.append({
                "post_pk": post.get("pk"),
                "post_id": post.get("id"),
                "like_count": post.get("like_count"),
                "reply_count": media_info.get("direct_reply_count"),
                "quote_count": media_info.get("quote_count"),
                "repost_count": media_info.get("repost_count"),
            })

        return result

    def dedupe_dicts(self, rows: List[Dict[str, Any]], key_fields: List[str]) -> List[Dict[str, Any]]:
        seen = set()
        result = []

        for row in rows:
            key = tuple(row.get(k) for k in key_fields)
            if key in seen:
                continue
            seen.add(key)
            result.append(row)

        return result


def run_search(keyword: str):
    parser = ThreadsSearchParser()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=AUTH_FILE)
        page = context.new_page()

        page.on("response", parser.response_handler)

        page.goto("https://www.threads.net/search", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        search_input = page.locator('input[placeholder="Search"]').first
        search_input.click()
        search_input.fill(keyword)
        page.wait_for_timeout(1500)
        page.keyboard.press("Enter")

        page.wait_for_timeout(10000)

        try:
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(4000)
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(4000)
        except Exception:
            pass

        raw_file = OUTPUT_DIR / f"threads_search_raw_{keyword}.json"
        raw_file.write_text(
            json.dumps(parser.captured_responses, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        users = []
        posts = []
        metric_blocks = []

        for item in parser.captured_responses:
            users.extend(parser.parse_users_from_item(item))
            posts.extend(parser.parse_posts_from_item(item))
            metric_blocks.extend(parser.parse_metric_blocks_from_item(item))

        users = parser.dedupe_dicts(users, ["pk"])
        posts = parser.dedupe_dicts(posts, ["post_id"])
        metric_blocks = parser.dedupe_dicts(metric_blocks, ["post_id"])

        result = {
            "keyword": keyword,
            "users_count": len(users),
            "posts_count": len(posts),
            "metric_blocks_count": len(metric_blocks),
            "users": users,
            "posts": posts,
            "metric_blocks": metric_blocks,
        }

        result_file = OUTPUT_DIR / f"threads_search_result_{keyword}.json"
        result_file.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print("=" * 80)
        print(f"keyword: {keyword}")
        print(f"users_count: {len(users)}")
        print(f"posts_count: {len(posts)}")
        print(f"metric_blocks_count: {len(metric_blocks)}")
        print(f"raw_file: {raw_file}")
        print(f"result_file: {result_file}")

        if users:
            print("\nFIRST USER:")
            print(json.dumps(users[0], ensure_ascii=False, indent=2))

        if posts:
            print("\nFIRST POST:")
            print(json.dumps(posts[0], ensure_ascii=False, indent=2))

        input("\nНатисни Enter для завершення...")
        browser.close()


if __name__ == "__main__":
    run_search(KEYWORD)