import json
from pathlib import Path

INPUT_FILE = Path("output/captured_search_responses.json")

if not INPUT_FILE.exists():
    print(f"Файл не знайдено: {INPUT_FILE}")
    raise SystemExit(1)

data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

interesting_keywords = [
    "python",
    "search",
    "query",
    "user",
    "users",
    "thread",
    "threads",
    "result",
    "results",
    "media",
    "text_post",
    "username",
    "profile"
]

matches_found = 0

for i, item in enumerate(data):
    text_parts = []

    url = item.get("url", "")
    body_preview = item.get("body_preview", "")
    json_body = item.get("json")

    if url:
        text_parts.append(url)

    if body_preview:
        text_parts.append(body_preview)

    if json_body is not None:
        try:
            text_parts.append(json.dumps(json_body, ensure_ascii=False))
        except Exception:
            pass

    blob = "\n".join(text_parts).lower()

    matches = [kw for kw in interesting_keywords if kw in blob]
    if matches:
        matches_found += 1
        print("=" * 120)
        print(f"INDEX: {i}")
        print(f"MATCHES: {matches}")
        print(f"URL: {url}")
        print(f"STATUS: {item.get('status')}")
        print("BODY PREVIEW:")
        print(body_preview[:1500])
        print()

print("=" * 120)
print(f"Усього знайдено цікавих записів: {matches_found}")