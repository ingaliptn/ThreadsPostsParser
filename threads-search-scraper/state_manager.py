from pathlib import Path
from typing import Dict, Any

from utils import load_json_file, save_json_file


class StateManager:
    def __init__(self, output_dir: str, state_file_name: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.output_dir / state_file_name
        self.state = load_json_file(self.state_file, {"keywords": {}})

        if "keywords" not in self.state or not isinstance(self.state["keywords"], dict):
            self.state["keywords"] = {}

    def get_keyword_state(self, keyword: str) -> Dict[str, Any]:
        keywords = self.state.setdefault("keywords", {})

        if keyword not in keywords or not isinstance(keywords[keyword], dict):
            keywords[keyword] = {
                "last_seen_post_id": None,
                "first_seen_run_at": None,
                "last_seen_run_at": None,
                "mode": "recent"
            }

        return keywords[keyword]

    def save(self) -> None:
        save_json_file(self.state_file, self.state)