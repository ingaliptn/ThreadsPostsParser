from typing import Any, Dict, List
from models import ThreadsUser, ThreadsPost


class PayloadParser:
    def parse_users_from_payload(self, payload: Dict[str, Any]) -> List[ThreadsUser]:
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

    def parse_posts_from_payload(self, payload: Dict[str, Any]) -> List[ThreadsPost]:
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

    def parse_metric_blocks_from_payload(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
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