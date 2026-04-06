from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto("https://www.threads.net/", wait_until="domcontentloaded")

    print("Браузер відкрито.")
    print("1. Увійди в Threads через Instagram вручну.")
    print("2. Після успішного логіну повернись у консоль.")
    input("Коли вже залогінився і бачиш стрічку/інтерфейс Threads — натисни Enter... ")

    context.storage_state(path="auth.json")
    print("Сесію збережено в auth.json")

    browser.close()