from pathlib import Path
from typing import Any, Dict

from utils import save_json_file, slugify


class FileStore:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_keyword_files(
        self,
        keyword: str,
        captured_responses: Dict[str, Any],
        request_log: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, str]:
        slug = slugify(keyword)

        raw_file = self.output_dir / f"threads_search_raw_{slug}.json"
        request_file = self.output_dir / f"threads_search_requests_{slug}.json"
        result_file = self.output_dir / f"threads_search_{slug}.json"

        save_json_file(raw_file, captured_responses)
        save_json_file(request_file, request_log)
        save_json_file(result_file, result)

        return {
            "raw_file": str(raw_file),
            "request_file": str(request_file),
            "result_file": str(result_file),
        }

    def save_summary(self, summary: Dict[str, Any]) -> str:
        summary_file = self.output_dir / "threads_search_summary.json"
        save_json_file(summary_file, summary)
        return str(summary_file)