import re
from typing import Tuple

from playwright.sync_api import Page

from constants import THREADS_SEARCH_URL


class PageActions:
    def open_search_page(self, page: Page) -> None:
        page.goto(THREADS_SEARCH_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

    def get_search_input(self, page: Page):
        candidates = [
            page.locator('input[placeholder="Search"]').first,
            page.locator('input[type="search"]').first,
            page.get_by_role("textbox").first,
        ]

        for locator in candidates:
            try:
                if locator.count() == 0:
                    continue
                locator.wait_for(timeout=5000)
                return locator
            except Exception:
                continue

        raise RuntimeError("search_input_not_found")

    def perform_search(self, page: Page, keyword: str) -> None:
        self.open_search_page(page)

        search_input = self.get_search_input(page)
        search_input.click()
        search_input.fill("")
        page.wait_for_timeout(300)
        search_input.fill(keyword)
        page.wait_for_timeout(1200)
        page.keyboard.press("Enter")
        page.wait_for_timeout(4000)

    def switch_to_recent(self, page: Page) -> Tuple[bool, str]:
        recent_patterns = [
            re.compile(r"^recent$", re.I),
            re.compile(r"^latest$", re.I),
            re.compile(r"нещодав", re.I),
            re.compile(r"останні", re.I),
        ]

        locators = []

        for pattern in recent_patterns:
            locators.extend(
                [
                    page.get_by_role("tab", name=pattern).first,
                    page.get_by_role("button", name=pattern).first,
                    page.get_by_text(pattern).first,
                    page.locator(f'text=/{pattern.pattern}/i').first,
                ]
            )

        for locator in locators:
            try:
                if locator.count() == 0:
                    continue

                locator.scroll_into_view_if_needed(timeout=2000)

                try:
                    locator.click(timeout=3000)
                except Exception:
                    try:
                        locator.click(timeout=3000, force=True)
                    except Exception:
                        page.evaluate("(el) => el.click()", locator.element_handle())

                page.wait_for_timeout(3500)
                return True, "clicked_recent_ui"
            except Exception:
                continue

        return False, "recent_ui_not_found"