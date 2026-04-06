from typing import Dict, Any, List
from models import ThreadsUser, ThreadsPost


def dedupe_users(users: List[ThreadsUser]) -> List[ThreadsUser]:
    seen = set()
    result = []

    for user in users:
        key = user.pk
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(user)

    return result


def dedupe_posts(posts: List[ThreadsPost]) -> List[ThreadsPost]:
    seen = set()
    result = []

    for post in posts:
        key = post.post_id
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(post)

    return result


def dedupe_metric_blocks(metric_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []

    for item in metric_blocks:
        key = item.get("post_id")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)

    return result


def dedupe_post_dicts(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []

    for post in posts:
        key = post.get("post_id")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(post)

    return result