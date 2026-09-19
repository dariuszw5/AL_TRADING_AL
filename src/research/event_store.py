from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Iterable


class DailyJsonlStore:
    def __init__(self, directory: str | Path, prefix: str, retention_days: int = 14):
        self.directory = Path(directory)
        self.prefix = prefix
        self.retention_days = int(retention_days)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, when: datetime) -> Path:
        day = when.astimezone(timezone.utc).date().isoformat()
        return self.directory / f"{self.prefix}_{day}.jsonl"

    def append(self, record: dict) -> None:
        now = datetime.now(timezone.utc)
        path = self._path_for(now)
        payload = dict(record)
        payload.setdefault("logged_at", now.isoformat())
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        self.prune(now)

    def append_many(self, records: Iterable[dict]) -> None:
        now = datetime.now(timezone.utc)
        rows = [dict(record) for record in records]
        if not rows:
            return
        for row in rows:
            row.setdefault("logged_at", now.isoformat())
        path = self._path_for(now)
        with path.open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.prune(now)

    def read_recent(self, limit: int = 200, days: int | None = None) -> list[dict]:
        horizon = days if days is not None else self.retention_days
        cutoff = datetime.now(timezone.utc).date() - timedelta(days=max(0, horizon - 1))
        paths = sorted(self.directory.glob(f"{self.prefix}_*.jsonl"), reverse=True)
        result: list[dict] = []
        for path in paths:
            try:
                date_part = path.stem.removeprefix(f"{self.prefix}_")
                if datetime.fromisoformat(date_part).date() < cutoff:
                    continue
            except ValueError:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line in reversed(lines):
                try:
                    result.append(json.loads(line))
                except (json.JSONDecodeError, TypeError):
                    continue
                if len(result) >= limit:
                    return list(reversed(result))
        return list(reversed(result))

    def prune(self, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        cutoff = now.date() - timedelta(days=self.retention_days)
        for path in self.directory.glob(f"{self.prefix}_*.jsonl"):
            try:
                date_part = path.stem.removeprefix(f"{self.prefix}_")
                day = datetime.fromisoformat(date_part).date()
            except ValueError:
                continue
            if day < cutoff:
                try:
                    path.unlink()
                except OSError:
                    pass
