from dataclasses import asdict
from typing import Any, Dict, List, Tuple

from dedupe import dedupe_users, dedupe_posts, dedupe_metric_blocks
from models import ThreadsUser, ThreadsPost
from payload_parser import PayloadParser
from state_manager import StateManager
from utils import now_iso


class SearchCollector:
    def __init__(self, parser: PayloadParser, state_manager: StateManager):
        self.parser = parser
        self.state_manager = state_manager
        self.captured_responses: List[Dict[str, Any]] = []
        self.request_log: List[Dict[str, Any]] = []

    def reset_runtime_buffers(self) -> None:
        self.captured_responses = []
        self.request_log = []

    def response_handler(self, response):
        url = response.url.lower()

        if "graphql/query" not in url:
            return

        try:
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" not in content_type:
                return

            body_text = response.text()

            try:
                import json
                parsed_json = json.loads(body_text)
            except Exception:
                parsed_json = None

            self.captured_responses.append(
                {
                    "status": response.status,
                    "url": response.url,
                    "content_type": content_type,
                    "body_preview": body_text[:2000],
                    "json": parsed_json,
                }
            )
        except Exception:
            pass

    def request_handler(self, request):
        url = request.url.lower()
        if "graphql/query" not in url:
            return

        try:
            self.request_log.append(
                {
                    "method": request.method,
                    "url": request.url,
                    "post_data": request.post_data,
                }
            )
        except Exception:
            pass

    def collect_parsed_data(self) -> Tuple[List[ThreadsUser], List[ThreadsPost], List[Dict[str, Any]]]:
        users: List[ThreadsUser] = []
        posts: List[ThreadsPost] = []
        metric_blocks: List[Dict[str, Any]] = []

        for item in self.captured_responses:
            payload = item.get("json")
            if not isinstance(payload, dict):
                continue

            users.extend(self.parser.parse_users_from_payload(payload))
            posts.extend(self.parser.parse_posts_from_payload(payload))
            metric_blocks.extend(self.parser.parse_metric_blocks_from_payload(payload))

        users = dedupe_users(users)
        posts = dedupe_posts(posts)
        metric_blocks = dedupe_metric_blocks(metric_blocks)

        return users, posts, metric_blocks

    def finalize_keyword_result(
        self,
        keyword: str,
        users: List[ThreadsUser],
        posts: List[ThreadsPost],
        metric_blocks: List[Dict[str, Any]],
        recent_switched: bool,
        recent_reason: str,
        max_posts_new_keyword: int
    ) -> Dict[str, Any]:
        keyword_state = self.state_manager.get_keyword_state(keyword)
        previous_last_seen_post_id = keyword_state.get("last_seen_post_id")
        is_new_keyword = not previous_last_seen_post_id

        new_posts: List[ThreadsPost] = []
        previous_post_found = False

        if is_new_keyword:
            new_posts = posts[:max_posts_new_keyword]
        else:
            for post in posts:
                if post.post_id == previous_last_seen_post_id:
                    previous_post_found = True
                    break
                new_posts.append(post)

            if not previous_post_found:
                new_posts = []
                recent_reason = f"{recent_reason}|previous_last_seen_post_not_found"

        if posts:
            keyword_state["last_seen_post_id"] = posts[0].post_id

        if not keyword_state.get("first_seen_run_at"):
            keyword_state["first_seen_run_at"] = now_iso()

        keyword_state["last_seen_run_at"] = now_iso()
        keyword_state["mode"] = "recent"
        self.state_manager.save()

        return {
            "keyword": keyword,
            "mode": "recent",
            "recent_switched": recent_switched,
            "recent_reason": recent_reason,
            "is_new_keyword": is_new_keyword,
            "previous_last_seen_post_id": previous_last_seen_post_id,
            "previous_post_found": previous_post_found,
            "current_last_seen_post_id": keyword_state.get("last_seen_post_id"),
            "users_count": len(users),
            "posts_count_total_seen": len(posts),
            "posts_count_new": len(new_posts),
            "metric_blocks_count": len(metric_blocks),
            "users": [asdict(x) for x in users],
            "posts_all_seen": [asdict(x) for x in posts],
            "posts_new": [asdict(x) for x in new_posts],
            "metric_blocks": metric_blocks,
            "request_log": self.request_log,
            "captured_responses_count": len(self.captured_responses),
        }