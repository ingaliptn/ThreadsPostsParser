#!/usr/bin/env python3

import argparse
from pathlib import Path

from collector import SearchCollector
from constants import (
    DEFAULT_AUTH_FILE,
    DEFAULT_MAX_POSTS_NEW_KEYWORD,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SCROLL_ATTEMPTS,
    DEFAULT_STATE_FILE,
)
from file_store import FileStore
from page_actions import PageActions
from payload_parser import PayloadParser
from scraper import ThreadsScraper
from state_manager import StateManager


def main():
    parser = argparse.ArgumentParser(
        description="Threads keyword search scraper with queue + state"
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        required=True,
        help="List of keywords to search in Threads",
    )
    parser.add_argument(
        "--auth",
        default=DEFAULT_AUTH_FILE,
        help="Path to auth.json",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory",
    )
    parser.add_argument(
        "--max-posts-new",
        type=int,
        default=DEFAULT_MAX_POSTS_NEW_KEYWORD,
        help="Max posts for a new keyword",
    )
    parser.add_argument(
        "--scroll-attempts",
        type=int,
        default=DEFAULT_SCROLL_ATTEMPTS,
        help="Scroll attempts per keyword",
    )
    args = parser.parse_args()

    auth_path = Path(args.auth)
    if not auth_path.exists():
        print(f"Auth file not found: {auth_path}")
        raise SystemExit(1)

    state_manager = StateManager(
        output_dir=args.output,
        state_file_name=DEFAULT_STATE_FILE,
    )
    payload_parser = PayloadParser()
    collector = SearchCollector(
        parser=payload_parser,
        state_manager=state_manager,
    )
    page_actions = PageActions()
    file_store = FileStore(output_dir=args.output)

    scraper = ThreadsScraper(
        auth_file=str(auth_path),
        collector=collector,
        page_actions=page_actions,
        file_store=file_store,
    )

    summary = scraper.search_keywords(
        keywords=args.keywords,
        max_posts_new_keyword=args.max_posts_new,
        scroll_attempts=args.scroll_attempts,
    )

    print("=" * 80)
    print(f"keywords_count: {summary['keywords_count']}")
    print(f"all_new_posts_count: {summary['all_new_posts_count']}")
    print(f"summary_file: {summary['summary_file']}")
    print(f"state_file: {summary['state_file']}")

    for item in summary["results"]:
        print("\n" + "-" * 80)
        print(f"keyword: {item.get('keyword')}")

        if item.get("error"):
            print(f"error: {item.get('error')}")
            print(f"raw_file: {item.get('raw_file')}")
            print(f"request_file: {item.get('request_file')}")
            print(f"result_file: {item.get('result_file')}")
            continue

        print(f"mode: {item.get('mode')}")
        print(f"recent_switched: {item.get('recent_switched')} ({item.get('recent_reason')})")
        print(f"is_new_keyword: {item.get('is_new_keyword')}")
        print(f"users_count: {item.get('users_count')}")
        print(f"posts_count_total_seen: {item.get('posts_count_total_seen')}")
        print(f"posts_count_new: {item.get('posts_count_new')}")
        print(f"previous_last_seen_post_id: {item.get('previous_last_seen_post_id')}")
        print(f"current_last_seen_post_id: {item.get('current_last_seen_post_id')}")
        print(f"result_file: {item.get('result_file')}")


if __name__ == "__main__":
    main()