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
            if not isinstance(edge, dict):
                continue

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
        seen_ids = set()

        data_root = payload.get("data")
        if not isinstance(data_root, dict):
            return results

        tag_name = None
        tag_id = None

        search_results = data_root.get("searchResults")
        if isinstance(search_results, dict):
            tag_info = search_results.get("tag_info", {})
            if isinstance(tag_info, dict):
                tag_name = tag_info.get("display_name")
                tag_id = tag_info.get("id")

        nested_data = data_root.get("data")
        if isinstance(nested_data, dict):
            posts_list = nested_data.get("posts")
            if isinstance(posts_list, list):
                for post in posts_list:
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

                    parsed = ThreadsPost(
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

                    unique_id = parsed.post_id or parsed.post_pk
                    if unique_id in seen_ids:
                        continue

                    seen_ids.add(unique_id)
                    results.append(parsed)

        for node in self._walk(payload):
            if not isinstance(node, dict):
                continue

            if "thread_items" in node and isinstance(node.get("thread_items"), list):
                for thread_item in node.get("thread_items", []):
                    if not isinstance(thread_item, dict):
                        continue

                    post = thread_item.get("post")
                    parsed = self._extract_post_from_dict(
                        post,
                        tag_name=tag_name,
                        tag_id=tag_id,
                    )
                    if not parsed:
                        continue

                    unique_id = parsed.post_id or parsed.post_pk
                    if unique_id in seen_ids:
                        continue

                    seen_ids.add(unique_id)
                    results.append(parsed)
                continue

            if "post" in node and isinstance(node.get("post"), dict):
                parsed = self._extract_post_from_dict(
                    node.get("post"),
                    tag_name=tag_name,
                    tag_id=tag_id,
                )
                if not parsed:
                    continue

                unique_id = parsed.post_id or parsed.post_pk
                if unique_id in seen_ids:
                    continue

                seen_ids.add(unique_id)
                results.append(parsed)
                continue

        return results

    def parse_metric_blocks_from_payload(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        seen_ids = set()

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

            post_id = post.get("id") or ""
            post_pk = post.get("pk") or ""
            unique_id = post_id or post_pk

            if not unique_id or unique_id in seen_ids:
                continue

            seen_ids.add(unique_id)
            results.append(
                {
                    "post_pk": post_pk,
                    "post_id": post_id,
                    "like_count": int(post.get("like_count") or 0),
                    "reply_count": int(media_info.get("direct_reply_count") or 0),
                    "quote_count": int(media_info.get("quote_count") or 0),
                    "repost_count": int(media_info.get("repost_count") or 0),
                }
            )

        return results

    def _extract_post_from_dict(
        self,
        post: Any,
        tag_name: str = None,
        tag_id: str = None,
    ) -> ThreadsPost | None:
        if not isinstance(post, dict):
            return None

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

        return ThreadsPost(
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

    def _walk(self, obj: Any):
        if isinstance(obj, dict):
            yield obj
            for value in obj.values():
                yield from self._walk(value)
        elif isinstance(obj, list):
            for item in obj:
                yield from self._walk(item)