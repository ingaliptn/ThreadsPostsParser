import json
from pathlib import Path
from playwright.sync_api import sync_playwright

KEYWORD = "python"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

captured = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(storage_state="auth.json")
    page = context.new_page()

    def on_response(response):
        url = response.url.lower()

        interesting = any(x in url for x in [
            "graphql",
            "search",
            "barcelona",
            "api"
        ])

        if not interesting:
            return

        try:
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type.lower():
                return

            body_text = response.text()

            item = {
                "status": response.status,
                "url": response.url,
                "content_type": content_type,
                "body_preview": body_text[:2000]
            }

            try:
                item["json"] = json.loads(body_text)
            except Exception:
                item["json"] = None

            captured.append(item)
            print(f"[CAPTURED] {response.status} {response.url}")

        except Exception as e:
            print(f"[ERROR] {response.url} -> {e}")

    page.on("response", on_response)

    page.goto("https://www.threads.net/search", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    search_input = page.locator('input[placeholder="Search"]').first
    search_input.click()
    search_input.fill(KEYWORD)
    page.wait_for_timeout(1500)
    page.keyboard.press("Enter")

    page.wait_for_timeout(10000)

    out_file = OUTPUT_DIR / "captured_search_responses.json"
    out_file.write_text(json.dumps(captured, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nЗбережено {len(captured)} response(s) у {out_file}")
    input("Натисни Enter для завершення...")
    browser.close()