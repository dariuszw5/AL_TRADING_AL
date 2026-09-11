import json
from pathlib import Path


class LiveStateStore:
    def __init__(self, path="data/live_state/agent_state.json"):
        self.path = Path(path)

    def save(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)

        temporary = self.path.with_suffix(".tmp")

        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(
                state,
                handle,
                indent=2,
                ensure_ascii=False
            )

        temporary.replace(self.path)

    def load(self):
        if not self.path.exists():
            return None

        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def clear(self):
        if self.path.exists():
            self.path.unlink()
