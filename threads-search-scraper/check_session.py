from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(storage_state="auth.json")
    page = context.new_page()

    page.goto("https://www.threads.net/", wait_until="domcontentloaded")
    page.wait_for_timeout(8000)

    print("URL:", page.url)
    print("TITLE:", page.title())

    input("Перевір у вікні браузера, що ти вже авторизований. Натисни Enter для завершення... ")
    browser.close()