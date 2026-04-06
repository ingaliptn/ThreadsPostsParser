import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    original = value.strip().lower()

    normalized = unicodedata.normalize("NFKD", original)
    ascii_part = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_part = re.sub(r"[^a-z0-9]+", "_", ascii_part)
    ascii_part = re.sub(r"_+", "_", ascii_part).strip("_")

    digest = hashlib.md5(original.encode("utf-8")).hexdigest()[:8]

    if ascii_part:
        return f"{ascii_part}_{digest}"

    return f"keyword_{digest}"


def load_json_file(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return default

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        return default
    except Exception:
        return default


def save_json_file(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )