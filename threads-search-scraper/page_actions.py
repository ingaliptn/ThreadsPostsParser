import re
from typing import Tuple

from playwright.sync_api import Page

from constants import THREADS_SEARCH_URL


class PageActions:
    def open_search_page(self, page: Page) -> None:
        page.goto(THREADS_SEARCH_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

    def get_search_input(self, page: Page):
        search_input = page.locator('input[placeholder="Search"]').first
        search_input.wait_for(timeout=15000)
        return search_input

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
        candidates = [
            page.get_by_role("tab", name=re.compile(r"recent", re.I)).first,
            page.get_by_role("button", name=re.compile(r"recent", re.I)).first,
            page.get_by_text(re.compile(r"recent", re.I)).first,
        ]

        for locator in candidates:
            try:
                if locator.count() == 0:
                    continue
                locator.click(timeout=3000)
                page.wait_for_timeout(3500)
                return True, "clicked_recent_ui"
            except Exception:
                continue

        return False, "recent_ui_not_found"