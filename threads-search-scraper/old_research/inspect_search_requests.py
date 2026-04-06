from playwright.sync_api import sync_playwright

KEYWORD = "python"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(storage_state="auth.json")
    page = context.new_page()

    def on_response(response):
        url = response.url.lower()
        if any(x in url for x in ["graphql", "search", "barcelona", "api"]):
            print("STATUS:", response.status, "URL:", response.url)

    page.on("response", on_response)

    page.goto("https://www.threads.net/search", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    search_input = page.locator('input[placeholder="Search"]').first
    search_input.click()
    search_input.fill(KEYWORD)
    page.wait_for_timeout(2000)
    page.keyboard.press("Enter")

    page.wait_for_timeout(10000)

    input("Подивись у консоль, що прилетіло. Натисни Enter для завершення...")
    browser.close()