import json
from pathlib import Path

INPUT_FILE = Path("output/captured_search_responses.json")

if not INPUT_FILE.exists():
    print(f"Файл не знайдено: {INPUT_FILE}")
    raise SystemExit(1)

data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

user_results = []
tag_results = []
post_metric_blocks = []

for item in data:
    payload = item.get("json")
    if not isinstance(payload, dict):
        continue

    data_root = payload.get("data")
    if not isinstance(data_root, dict):
        continue

    # 1. User search results
    users_conn = data_root.get("xdt_api__v1__users__search_connection")
    if isinstance(users_conn, dict):
        for edge in users_conn.get("edges", []):
            node = edge.get("node", {})
            user_results.append({
                "username": node.get("username"),
                "pk": node.get("pk"),
                "full_name": node.get("full_name"),
                "is_verified": node.get("is_verified"),
                "is_private": node.get("text_post_app_is_private"),
                "has_threads": node.get("has_onboarded_to_text_post_app"),
                "profile_pic_url": node.get("profile_pic_url"),
                "follower_count": node.get("follower_count"),
            })

    # 2. Keyword/tag search results
    search_results = data_root.get("searchResults")
    if isinstance(search_results, dict):
        tag_info = search_results.get("tag_info", {})
        edges = search_results.get("edges", [])

        for edge in edges:
            node = edge.get("node", {})
            thread = node.get("thread", {})
            thread_items = thread.get("thread_items", [])

            for thread_item in thread_items:
                post = thread_item.get("post", {})
                user = post.get("user", {})
                media_info = post.get("text_post_app_info", {})

                caption = None
                if isinstance(post.get("caption"), dict):
                    caption = post["caption"].get("text")

                tag_results.append({
                    "tag": tag_info.get("display_name"),
                    "tag_id": tag_info.get("id"),
                    "post_pk": post.get("pk"),
                    "post_code": post.get("code"),
                    "post_id": post.get("id"),
                    "text": caption,
                    "username": user.get("username"),
                    "user_pk": user.get("pk"),
                    "full_name": user.get("full_name"),
                    "is_verified": user.get("is_verified"),
                    "like_count": post.get("like_count"),
                    "reply_count": media_info.get("direct_reply_count"),
                    "quote_count": media_info.get("quote_count"),
                    "repost_count": media_info.get("repost_count"),
                })

    # 3. Post metrics blocks
    nested_data = data_root.get("data")
    if isinstance(nested_data, dict) and isinstance(nested_data.get("posts"), list):
        for post in nested_data["posts"]:
            media_info = post.get("text_post_app_info", {})
            post_metric_blocks.append({
                "post_pk": post.get("pk"),
                "post_id": post.get("id"),
                "like_count": post.get("like_count"),
                "reply_count": media_info.get("direct_reply_count"),
                "quote_count": media_info.get("quote_count"),
                "repost_count": media_info.get("repost_count"),
            })

print("=" * 80)
print("USER RESULTS")
print("=" * 80)
for row in user_results[:10]:
    print(json.dumps(row, ensure_ascii=False, indent=2))

print("\n" + "=" * 80)
print("TAG RESULTS")
print("=" * 80)
for row in tag_results[:10]:
    print(json.dumps(row, ensure_ascii=False, indent=2))

print("\n" + "=" * 80)
print("POST METRIC BLOCKS")
print("=" * 80)
for row in post_metric_blocks[:10]:
    print(json.dumps(row, ensure_ascii=False, indent=2))

print("\nSUMMARY")
print(f"user_results: {len(user_results)}")
print(f"tag_results: {len(tag_results)}")
print(f"post_metric_blocks: {len(post_metric_blocks)}")