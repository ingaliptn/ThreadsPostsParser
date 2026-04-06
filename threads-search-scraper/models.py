from dataclasses import dataclass
from typing import Optional


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