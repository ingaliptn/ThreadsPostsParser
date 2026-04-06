from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(storage_state="auth.json")
    page = context.new_page()

    page.goto("https://www.threads.net/search", wait_until="domcontentloaded")
    page.wait_for_timeout(10000)

    print("URL:", page.url)
    print("TITLE:", page.title())

    input("Подивись, що відкрилось у браузері, і натисни Enter...")
    browser.close()