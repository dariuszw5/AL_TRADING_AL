from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from statistics import mean

from src.agent.ai_manager import HORIZON, SIDES, net_return
from src.agent.live_state_store import LiveStateStore
from src.research.event_store import DailyJsonlStore


@dataclass(frozen=True)
class MemoryAdjustment:
    samples: int
    mean_return: float
    similarity: float
    adjustment: float

    def as_dict(self) -> dict:
        return {
            "samples": self.samples,
            "mean_return": self.mean_return,
            "similarity": self.similarity,
            "adjustment": self.adjustment,
        }


class ExperienceMemory:
    def __init__(self, data_dir: str | Path, horizon_minutes: int = HORIZON):
        root = Path(data_dir)
        root.mkdir(parents=True, exist_ok=True)
        self.horizon_ms = int(horizon_minutes) * 60_000
        self.resolved = DailyJsonlStore(root / "logs", "experiences", 120)
        self.pending_store = LiveStateStore(root / "research_pending.json")
        self.pending = self.pending_store.load() or {"version": 1, "items": []}
        if self.pending.get("version") != 1:
            self.pending = {"version": 1, "items": []}

    def observe(self, *, symbol, timestamp, close, features, strategy, side, macro_tags, model_score):
        side = str(side).upper()
        if side not in SIDES:
            raise ValueError("Experience direction must be LONG or SHORT")
        item = {
            "label_version": 2,
            "side": side,
            "symbol": symbol,
            "timestamp": int(timestamp),
            "close": float(close),
            "features": [float(x) for x in features],
            "strategy": strategy,
            "macro_tags": sorted(set(str(x) for x in macro_tags)),
            "model_score": float(model_score),
        }
        items = self.pending.get("items", [])
        key = (item["symbol"], item["strategy"], item["side"], item["timestamp"])
        if not any(
            (r.get("symbol"), r.get("strategy"), r.get("side"), r.get("timestamp")) == key
            for r in items
        ):
            items.append(item)
        self.pending["items"] = items[-2000:]
        self.pending_store.save(self.pending)

    def resolve(self, market_closes: dict[str, tuple[int, float]]) -> int:
        remaining, resolved_rows = [], []
        for row in self.pending.get("items", []):
            # Old observations had no direction; their outcomes cannot safely
            # be classified as successful/failed LONG or SHORT experiences.
            if row.get("label_version") != 2 or row.get("side") not in SIDES:
                continue
            current = market_closes.get(str(row.get("symbol")))
            if current is None:
                remaining.append(row)
                continue
            current_timestamp, current_close = current
            if current_timestamp < int(row["timestamp"]) + self.horizon_ms:
                remaining.append(row)
                continue
            entry = float(row["close"])
            if entry <= 0:
                continue
            resolved_rows.append({
                **row,
                "outcome_timestamp": int(current_timestamp),
                "outcome_close": float(current_close),
                # Research label, NOT executed brokerage PnL. Use the same
                # directional round-trip fee/slippage convention as paper AI.
                "realized_forward_return": net_return(
                    entry, float(current_close), str(row["side"])
                ),
                "label_type": "DIRECTIONAL_CLOSE_PROXY_AFTER_COSTS",
                "event_type": "RESOLVED_EXPERIENCE",
            })
        self.pending["items"] = remaining[-2000:]
        self.pending_store.save(self.pending)
        if resolved_rows:
            self.resolved.append_many(resolved_rows)
        return len(resolved_rows)

    @staticmethod
    def _distance(a, b):
        if len(a) != len(b) or not a:
            return float("inf")
        return sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def adjustment(self, *, features, strategy, side, macro_tags, k: int = 20) -> MemoryAdjustment:
        side = str(side).upper()
        if side not in SIDES:
            raise ValueError("Experience direction must be LONG or SHORT")
        target = [float(x) for x in features]
        target_tags = set(str(x) for x in macro_tags)
        rows = [r for r in self.resolved.read_recent(limit=6000, days=120)
                if r.get("event_type") == "RESOLVED_EXPERIENCE"
                and r.get("label_version") == 2
                and r.get("side") == side
                and r.get("strategy") == strategy]
        ranked = []
        for row in rows:
            try:
                row_features = [float(x) for x in row.get("features", [])]
                distance = self._distance(target, row_features)
                if distance == float("inf"):
                    continue
                row_tags = set(str(x) for x in row.get("macro_tags", []))
                overlap = len(target_tags & row_tags) / max(1, len(target_tags | row_tags))
                ranked.append((distance / (1.0 + 0.5 * overlap), overlap,
                               float(row["realized_forward_return"])))
            except (TypeError, ValueError, KeyError):
                continue
        ranked.sort(key=lambda item: item[0])
        neighbors = ranked[:max(1, int(k))]
        if len(neighbors) < 5:
            return MemoryAdjustment(0, 0.0, 0.0, 0.0)
        avg = mean(item[2] for item in neighbors)
        similarity = mean(1.0 / (1.0 + item[0]) for item in neighbors)
        adjustment = max(-0.01, min(0.01, avg * 0.25 * similarity))
        return MemoryAdjustment(len(neighbors), avg, similarity, adjustment)
