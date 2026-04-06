#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

from playwright.sync_api import sync_playwright


DEFAULT_AUTH_FILE = "auth.json"
DEFAULT_OUTPUT_DIR = "output"


@dataclass
class ThreadsUser:
    username: str
    pk: str
    full_name: str
    profile_pic_url: Optional[str]
    is_private: bool
    is_verified: Optional[bool]
    has_threads: bool
    follower_count: Optional[int]


@dataclass
class ThreadsPost:
    post_pk: str
    post_code: Optional[str]
    post_id: str
    text: Optional[str]
    username: str
    user_pk: str
    full_name: str
    is_verified: bool
    like_count: int
    reply_count: int
    quote_count: int
    repost_count: int
    tag: Optional[str]
    tag_id: Optional[str]


class ThreadsScraper:
    def __init__(self, auth_file: str, output_dir: str):
        self.auth_file = auth_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.captured_responses: List[Dict[str, Any]] = []

    def _response_handler(self, response):
        url = response.url.lower()

        if "graphql/query" not in url:
            return

        try:
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" not in content_type:
                return

            body_text = response.text()

            try:
                parsed_json = json.loads(body_text)
            except Exception:
                parsed_json = None

            self.captured_responses.append({
                "status": response.status,
                "url": response.url,
                "content_type": content_type,
                "body_preview": body_text[:2000],
                "json": parsed_json,
            })

        except Exception:
            pass

    def _parse_users_from_payload(self, payload: Dict[str, Any]) -> List[ThreadsUser]:
        results = []

        data_root = payload.get("data")
        if not isinstance(data_root, dict):
            return results

        users_conn = data_root.get("xdt_api__v1__users__search_connection")
        if not isinstance(users_conn, dict):
            return results

        for edge in users_conn.get("edges", []):
            node = edge.get("node", {})
            if not isinstance(node, dict):
                continue

            results.append(
                ThreadsUser(
                    username=node.get("username") or "",
                    pk=node.get("pk") or "",
                    full_name=node.get("full_name") or "",
                    profile_pic_url=node.get("profile_pic_url"),
                    is_private=bool(node.get("text_post_app_is_private", False)),
                    is_verified=node.get("is_verified"),
                    has_threads=bool(node.get("has_onboarded_to_text_post_app", False)),
                    follower_count=node.get("follower_count"),
                )
            )

        return results

    def _parse_posts_from_payload(self, payload: Dict[str, Any]) -> List[ThreadsPost]:
        results = []

        data_root = payload.get("data")
        if not isinstance(data_root, dict):
            return results

        search_results = data_root.get("searchResults")
        if not isinstance(search_results, dict):
            return results

        tag_info = search_results.get("tag_info", {})
        tag_name = tag_info.get("display_name") if isinstance(tag_info, dict) else None
        tag_id = tag_info.get("id") if isinstance(tag_info, dict) else None

        for edge in search_results.get("edges", []):
            node = edge.get("node", {})
            if not isinstance(node, dict):
                continue

            thread = node.get("thread", {})
            if not isinstance(thread, dict):
                continue

            thread_items = thread.get("thread_items", [])
            if not isinstance(thread_items, list):
                continue

            for thread_item in thread_items:
                if not isinstance(thread_item, dict):
                    continue

                post = thread_item.get("post", {})
                if not isinstance(post, dict):
                    continue

                user = post.get("user", {})
                if not isinstance(user, dict):
                    user = {}

                media_info = post.get("text_post_app_info", {})
                if not isinstance(media_info, dict):
                    media_info = {}

                caption_text = None
                caption = post.get("caption")
                if isinstance(caption, dict):
                    caption_text = caption.get("text")

                results.append(
                    ThreadsPost(
                        post_pk=post.get("pk") or "",
                        post_code=post.get("code"),
                        post_id=post.get("id") or "",
                        text=caption_text,
                        username=user.get("username") or "",
                        user_pk=user.get("pk") or "",
                        full_name=user.get("full_name") or "",
                        is_verified=bool(user.get("is_verified", False)),
                        like_count=int(post.get("like_count") or 0),
                        reply_count=int(media_info.get("direct_reply_count") or 0),
                        quote_count=int(media_info.get("quote_count") or 0),
                        repost_count=int(media_info.get("repost_count") or 0),
                        tag=tag_name,
                        tag_id=tag_id,
                    )
                )

        return results

    def _parse_metric_blocks_from_payload(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []

        data_root = payload.get("data")
        if not isinstance(data_root, dict):
            return results

        nested_data = data_root.get("data")
        if not isinstance(nested_data, dict):
            return results

        posts = nested_data.get("posts")
        if not isinstance(posts, list):
            return results

        for post in posts:
            if not isinstance(post, dict):
                continue

            media_info = post.get("text_post_app_info", {})
            if not isinstance(media_info, dict):
                media_info = {}

            results.append({
                "post_pk": post.get("pk") or "",
                "post_id": post.get("id") or "",
                "like_count": int(post.get("like_count") or 0),
                "reply_count": int(media_info.get("direct_reply_count") or 0),
                "quote_count": int(media_info.get("quote_count") or 0),
                "repost_count": int(media_info.get("repost_count") or 0),
            })

        return results

    def _dedupe_users(self, users: List[ThreadsUser]) -> List[ThreadsUser]:
        seen = set()
        result = []

        for user in users:
            key = user.pk
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(user)

        return result

    def _dedupe_posts(self, posts: List[ThreadsPost]) -> List[ThreadsPost]:
        seen = set()
        result = []

        for post in posts:
            key = post.post_id
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(post)

        return result

    def _dedupe_metric_blocks(self, metric_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        result = []

        for item in metric_blocks:
            key = item.get("post_id")
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(item)

        return result

    def search(self, keyword: str) -> Dict[str, Any]:
        self.captured_responses = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(storage_state=self.auth_file)
            page = context.new_page()

            page.on("response", self._response_handler)

            page.goto("https://www.threads.net/search", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            search_input = page.locator('input[placeholder="Search"]').first
            search_input.click()
            search_input.fill(keyword)
            page.wait_for_timeout(1500)
            page.keyboard.press("Enter")

            page.wait_for_timeout(8000)

            try:
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(3000)
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(3000)
            except Exception:
                pass

            browser.close()

        raw_file = self.output_dir / f"threads_search_raw_{keyword}.json"
        raw_file.write_text(
            json.dumps(self.captured_responses, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        users: List[ThreadsUser] = []
        posts: List[ThreadsPost] = []
        metric_blocks: List[Dict[str, Any]] = []

        for item in self.captured_responses:
            payload = item.get("json")
            if not isinstance(payload, dict):
                continue

            users.extend(self._parse_users_from_payload(payload))
            posts.extend(self._parse_posts_from_payload(payload))
            metric_blocks.extend(self._parse_metric_blocks_from_payload(payload))

        users = self._dedupe_users(users)
        posts = self._dedupe_posts(posts)
        metric_blocks = self._dedupe_metric_blocks(metric_blocks)

        result = {
            "keyword": keyword,
            "users_count": len(users),
            "posts_count": len(posts),
            "metric_blocks_count": len(metric_blocks),
            "users": [asdict(x) for x in users],
            "posts": [asdict(x) for x in posts],
            "metric_blocks": metric_blocks,
        }

        result_file = self.output_dir / f"threads_search_{keyword}.json"
        result_file.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        return {
            "raw_file": str(raw_file),
            "result_file": str(result_file),
            "result": result,
        }


def main():
    parser = argparse.ArgumentParser(description="Threads keyword search scraper")
    parser.add_argument("--keyword", required=True, help="Keyword to search in Threads")
    parser.add_argument("--auth", default=DEFAULT_AUTH_FILE, help="Path to auth.json")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    auth_path = Path(args.auth)
    if not auth_path.exists():
        print(f"Auth file not found: {auth_path}")
        raise SystemExit(1)

    scraper = ThreadsScraper(auth_file=str(auth_path), output_dir=args.output)
    data = scraper.search(args.keyword)

    result = data["result"]

    print("=" * 80)
    print(f"keyword: {result['keyword']}")
    print(f"users_count: {result['users_count']}")
    print(f"posts_count: {result['posts_count']}")
    print(f"metric_blocks_count: {result['metric_blocks_count']}")
    print(f"raw_file: {data['raw_file']}")
    print(f"result_file: {data['result_file']}")

    if result["users"]:
        print("\nFIRST USER:")
        print(json.dumps(result["users"][0], ensure_ascii=False, indent=2))

    if result["posts"]:
        print("\nFIRST POST:")
        print(json.dumps(result["posts"][0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()