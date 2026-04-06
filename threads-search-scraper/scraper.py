from typing import Any, Dict, List

from playwright.sync_api import sync_playwright

from dedupe import dedupe_post_dicts


class ThreadsScraper:
    def __init__(
        self,
        auth_file: str,
        collector,
        page_actions,
        file_store,
    ):
        self.auth_file = auth_file
        self.collector = collector
        self.page_actions = page_actions
        self.file_store = file_store

    def search_keywords(
        self,
        keywords: List[str],
        max_posts_new_keyword: int,
        scroll_attempts: int
    ) -> Dict[str, Any]:
        normalized_keywords = [x.strip() for x in keywords if x and x.strip()]
        if not normalized_keywords:
            raise ValueError("Keywords list is empty")

        results = []
        all_new_posts: List[Dict[str, Any]] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(storage_state=self.auth_file)

            for keyword in normalized_keywords:
                page = None
                try:
                    print(f"[{keyword}] new page")
                    page = context.new_page()

                    self.collector.reset_runtime_buffers()

                    page.on("response", self.collector.response_handler)
                    page.on("request", self.collector.request_handler)

                    print(f"[{keyword}] open search")
                    self.page_actions.perform_search(page, keyword)

                    print(f"[{keyword}] switch to recent")
                    recent_switched, recent_reason = self.page_actions.switch_to_recent(page)

                    users, posts, metric_blocks = self.collector.collect_parsed_data()
                    print(f"[{keyword}] initial posts: {len(posts)}")

                    previous_last_seen_post_id = self.collector.state_manager.get_keyword_state(keyword).get("last_seen_post_id")
                    is_new_keyword = not previous_last_seen_post_id

                    for i in range(scroll_attempts):
                        enough_for_new_keyword = is_new_keyword and len(posts) >= max_posts_new_keyword
                        found_old_post = previous_last_seen_post_id and any(p.post_id == previous_last_seen_post_id for p in posts)

                        if enough_for_new_keyword or found_old_post:
                            break

                        print(f"[{keyword}] scroll {i + 1}/{scroll_attempts}")
                        try:
                            page.mouse.wheel(0, 2500)
                            page.wait_for_timeout(2500)
                        except Exception:
                            break

                        users, posts, metric_blocks = self.collector.collect_parsed_data()
                        print(f"[{keyword}] posts after scroll: {len(posts)}")

                    result = self.collector.finalize_keyword_result(
                        keyword=keyword,
                        users=users,
                        posts=posts,
                        metric_blocks=metric_blocks,
                        recent_switched=recent_switched,
                        recent_reason=recent_reason,
                        max_posts_new_keyword=max_posts_new_keyword
                    )

                    saved_files = self.file_store.save_keyword_files(
                        keyword=keyword,
                        captured_responses=self.collector.captured_responses,
                        request_log=self.collector.request_log,
                        result=result
                    )

                    result["slug"] = saved_files["result_file"].split("threads_search_")[-1].replace(".json", "")
                    result["saved_files"] = saved_files
                    
                    result.update(saved_files)
                    results.append(result)
                    all_new_posts.extend(result["posts_new"])

                except Exception as e:
                    print(f"[{keyword}] ERROR: {e}")
                    results.append({
                        "keyword": keyword,
                        "error": str(e),
                        "raw_file": None,
                        "request_file": None,
                        "result_file": None,
                    })
                finally:
                    if page is not None:
                        try:
                            page.close()
                        except Exception:
                            pass

            browser.close()

        all_new_posts = dedupe_post_dicts(all_new_posts)

        summary = {
            "keywords": normalized_keywords,
            "keywords_count": len(normalized_keywords),
            "results": results,
            "all_new_posts_count": len(all_new_posts),
            "all_new_posts": all_new_posts,
            "state_file": str(self.collector.state_manager.state_file),
        }

        summary_file = self.file_store.save_summary(summary)
        summary["summary_file"] = summary_file

        return summary