from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from math import log10
import os
import time
from pathlib import Path

import requests

from src.agent.ai_manager import features as ai_features, rank_asset
from src.data.assets import RESEARCH_ASSETS, AssetSpec, dynamic_binance_asset
from src.data.data_provider import DataProvider
from src.research.event_store import DailyJsonlStore
from src.research.experience import ExperienceMemory


@dataclass(frozen=True)
class UniverseCandidate:
    symbol: str
    provider: str
    market_score: float
    change_24h_pct: float
    range_24h_pct: float
    quote_volume_24h: float
    last_price: float

    def as_dict(self) -> dict:
        return asdict(self)


class OpportunityScanner:
    """Cross-market top-10 research scanner.

    Crypto is discovered dynamically from Binance. Equities, ETFs, FX,
    indices and commodity futures references come from the connected Yahoo
    research universe. Scores are normalized inside each asset class and the
    final selection applies a per-class cap so one market cannot dominate
    merely because its volatility scale is larger.
    """

    DEFAULT_CLASS_CAP = 3

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.provider = DataProvider()
        self.market_log = DailyJsonlStore(self.data_dir / "logs", "market_universe", 14)
        self.candle_log = DailyJsonlStore(self.data_dir / "logs", "selected_candles", 30)
        self.memory = ExperienceMemory(self.data_dir)
        self.min_quote_volume = float(
            os.getenv("AL_TRADING_MIN_QUOTE_VOLUME_USDT", "10000000")
        )
        self.crypto_preselect = max(
            5,
            int(os.getenv("AL_TRADING_CRYPTO_PRESELECT", "18")),
        )
        self.top_n = max(1, min(20, int(os.getenv("AL_TRADING_TOP_N", "10"))))
        self.class_cap = max(
            1,
            int(os.getenv("AL_TRADING_CLASS_CAP", str(self.DEFAULT_CLASS_CAP))),
        )
        self._last_logged_candle: dict[str, int] = {}

    def _binance_tickers(self) -> list[dict]:
        response = requests.get(
            f"{DataProvider.BINANCE_BASE_URL}/api/v3/ticker/24hr",
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Binance ticker response is not a list")
        return payload

    @staticmethod
    def _score_ticker(row: dict) -> UniverseCandidate | None:
        try:
            symbol = str(row["symbol"]).upper()
            if not symbol.endswith("USDT"):
                return None
            last_price = float(row["lastPrice"])
            change = float(row["priceChangePercent"])
            high = float(row["highPrice"])
            low = float(row["lowPrice"])
            quote_volume = float(row["quoteVolume"])
            if min(last_price, high, low, quote_volume) <= 0:
                return None
            range_pct = (high / low - 1.0) * 100.0
            liquidity = max(0.0, log10(max(1.0, quote_volume)) - 6.0)
            score = 0.45 * abs(change) + 0.35 * range_pct + 0.20 * liquidity
            return UniverseCandidate(
                symbol=symbol,
                provider="binance",
                market_score=score,
                change_24h_pct=change,
                range_24h_pct=range_pct,
                quote_volume_24h=quote_volume,
                last_price=last_price,
            )
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return None

    def discover(self) -> list[UniverseCandidate]:
        tickers = self._binance_tickers()
        candidates = []
        for row in tickers:
            candidate = self._score_ticker(row)
            if candidate is None or candidate.quote_volume_24h < self.min_quote_volume:
                continue
            candidates.append(candidate)
        candidates.sort(key=lambda item: item.market_score, reverse=True)
        self.market_log.append({
            "event_type": "CRYPTO_UNIVERSE_SNAPSHOT",
            "provider": "binance",
            "asset_class": "crypto",
            "symbols": [candidate.as_dict() for candidate in candidates],
            "count": len(candidates),
        })
        return candidates

    @staticmethod
    def _freshness_limit(asset_class: str) -> float:
        if asset_class == "crypto":
            return 180.0
        return 30 * 60.0

    @staticmethod
    def _intraday_market_score(candles) -> float:
        if len(candles) < 2:
            return 0.0
        window = candles[-min(len(candles), 120):]
        first = float(window[0].close)
        if first <= 0:
            return 0.0
        change_pct = abs(float(window[-1].close) / first - 1.0) * 100.0
        low = min(float(c.low) for c in window)
        high = max(float(c.high) for c in window)
        range_pct = (high / low - 1.0) * 100.0 if low > 0 else 0.0
        return 0.55 * change_pct + 0.45 * range_pct

    def _fetch_rank(
        self,
        asset: AssetSpec,
        market_score: float,
        macro_tags: list[str],
    ):
        try:
            candles = self.provider.get_candles(asset.symbol, "1m", 600)
            if len(candles) < 500:
                return None

            latest = candles[-1]
            age_seconds = max(0.0, time.time() - latest.timestamp / 1000.0)
            if age_seconds > self._freshness_limit(asset.asset_type):
                return {
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "provider": asset.provider,
                    "asset_class": asset.asset_type,
                    "error": f"STALE_MARKET:{age_seconds:.0f}s",
                    "combined_score": -999.0,
                }

            rows = rank_asset(asset.symbol, candles)
            best = max(rows, key=lambda row: row["score"], default=None)
            if best is None:
                return None

            feat = list(ai_features(candles, len(candles) - 1))
            memory = self.memory.adjustment(
                features=feat,
                strategy=str(best["strategy"]),
                macro_tags=macro_tags,
            )
            effective_market_score = (
                float(market_score)
                if market_score > 0
                else self._intraday_market_score(candles)
            )
            combined = (
                float(best["score"])
                + memory.adjustment
                + effective_market_score / 10_000.0
            )

            last_logged = self._last_logged_candle.get(asset.symbol)
            if last_logged != latest.timestamp:
                self.candle_log.append({
                    "event_type": "SELECTED_MARKET_CANDLE",
                    "symbol": asset.symbol,
                    "asset_class": asset.asset_type,
                    "provider": asset.provider,
                    "timestamp": latest.timestamp,
                    "open": latest.open,
                    "high": latest.high,
                    "low": latest.low,
                    "close": latest.close,
                    "volume": latest.volume,
                })
                self._last_logged_candle[asset.symbol] = latest.timestamp

            return {
                "symbol": asset.symbol,
                "name": asset.name,
                "provider": asset.provider,
                "provider_symbol": asset.provider_symbol,
                "asset_class": asset.asset_type,
                "instrument_type": asset.instrument_type,
                "strategy": best["strategy"],
                "eligible": bool(best.get("eligible")),
                "model_score": float(best["score"]),
                "combined_score": combined,
                "expected_net_return": float(best.get("expected_net_return", 0.0)),
                "neighbor_spread": float(best.get("neighbor_spread", 0.0)),
                "validation_trades": int(best.get("validation_trades", 0)),
                "validation_mean": best.get("validation_mean"),
                "market_score": effective_market_score,
                "features": feat,
                "memory": memory.as_dict(),
                "latest_timestamp": latest.timestamp,
                "age_seconds": age_seconds,
                "last_price": latest.close,
                "macro_tags": list(macro_tags),
            }
        except Exception as exc:
            return {
                "symbol": asset.symbol,
                "name": asset.name,
                "provider": asset.provider,
                "asset_class": asset.asset_type,
                "error": f"{type(exc).__name__}: {exc}",
                "combined_score": -999.0,
            }

    @staticmethod
    def _normalize_within_classes(rows: list[dict]) -> list[dict]:
        groups: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            groups[str(row["asset_class"])].append(row)

        normalized: list[dict] = []
        for asset_class, class_rows in groups.items():
            class_rows.sort(key=lambda row: row["combined_score"], reverse=True)
            count = len(class_rows)
            for index, row in enumerate(class_rows):
                percentile = 1.0 if count == 1 else 1.0 - index / (count - 1)
                validation_strength = min(
                    1.0,
                    max(0.0, float(row.get("validation_trades", 0))) / 20.0,
                )
                eligible_bonus = 0.10 if row.get("eligible") else 0.0
                cross_market_score = (
                    0.75 * percentile
                    + 0.15 * validation_strength
                    + eligible_bonus
                )
                copy = dict(row)
                copy["class_percentile"] = percentile
                copy["cross_market_score"] = cross_market_score
                normalized.append(copy)
        return normalized

    def _balanced_top(self, rows: list[dict]) -> list[dict]:
        normalized = self._normalize_within_classes(rows)
        normalized.sort(
            key=lambda row: (
                row["cross_market_score"],
                row["combined_score"],
            ),
            reverse=True,
        )
        if not normalized:
            return []

        by_class: dict[str, list[dict]] = defaultdict(list)
        for row in normalized:
            by_class[str(row["asset_class"])].append(row)

        class_heads = [values[0] for values in by_class.values() if values]
        class_heads.sort(
            key=lambda row: (
                row["cross_market_score"],
                row["combined_score"],
            ),
            reverse=True,
        )
        selected: list[dict] = class_heads[: self.top_n]
        selected_ids = {id(row) for row in selected}
        class_counts = Counter(str(row["asset_class"]) for row in selected)

        for row in normalized:
            if len(selected) >= self.top_n:
                break
            if id(row) in selected_ids:
                continue
            asset_class = str(row["asset_class"])
            if class_counts[asset_class] >= self.class_cap:
                continue
            selected.append(row)
            selected_ids.add(id(row))
            class_counts[asset_class] += 1

        for row in normalized:
            if len(selected) >= self.top_n:
                break
            if id(row) in selected_ids:
                continue
            selected.append(row)
            selected_ids.add(id(row))

        selected.sort(
            key=lambda row: (
                row["cross_market_score"],
                row["combined_score"],
            ),
            reverse=True,
        )
        return selected[: self.top_n]

    def scan(self, macro_tags: list[str] | None = None) -> dict:
        macro_tags = list(macro_tags or [])

        crypto_discovered = self.discover()
        crypto_preliminary = crypto_discovered[: self.crypto_preselect]
        assets: list[AssetSpec] = [
            dynamic_binance_asset(candidate.symbol)
            for candidate in crypto_preliminary
        ]
        market_scores = {
            candidate.symbol: candidate.market_score
            for candidate in crypto_preliminary
        }

        assets.extend(RESEARCH_ASSETS)
        asset_by_symbol = {asset.symbol: asset for asset in assets}

        def run(asset: AssetSpec):
            return self._fetch_rank(
                asset,
                market_scores.get(asset.symbol, 0.0),
                macro_tags,
            )

        max_workers = min(8, max(1, len(asset_by_symbol)))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            rows = [
                row
                for row in pool.map(run, asset_by_symbol.values())
                if row is not None
            ]

        closes = {
            str(row["symbol"]): (
                int(row["latest_timestamp"]),
                float(row["last_price"]),
            )
            for row in rows
            if "latest_timestamp" in row and "last_price" in row
        }
        self.memory.resolve(closes)

        valid = [row for row in rows if "error" not in row]
        top = self._balanced_top(valid)

        for row in top:
            self.memory.observe(
                symbol=row["symbol"],
                timestamp=row["latest_timestamp"],
                close=row["last_price"],
                features=row["features"],
                strategy=row["strategy"],
                macro_tags=row["macro_tags"],
                model_score=row["model_score"],
            )

        available_counts = Counter(str(row["asset_class"]) for row in valid)
        selected_counts = Counter(str(row["asset_class"]) for row in top)

        self.market_log.append({
            "event_type": "CROSS_MARKET_SELECTION",
            "available_by_class": dict(available_counts),
            "selected_by_class": dict(selected_counts),
            "selected": [row["symbol"] for row in top],
            "class_cap": self.class_cap,
        })

        return {
            "timestamp": int(time.time() * 1000),
            "universe_count": len(crypto_discovered) + len(RESEARCH_ASSETS),
            "crypto_universe_count": len(crypto_discovered),
            "connected_non_crypto_count": len(RESEARCH_ASSETS),
            "preselected_count": len(asset_by_symbol),
            "top_n": self.top_n,
            "opportunities": top,
            "available_by_class": dict(available_counts),
            "selected_by_class": dict(selected_counts),
            "errors": [row for row in rows if "error" in row],
            "paper_only": True,
            "real_orders": False,
            "selection_policy": {
                "class_cap": self.class_cap,
                "first_pass": "best fresh candidate from every active class",
                "normalization": "within-class percentile + validation strength",
                "fallback": (
                    "cap may be exceeded only when too few classes are "
                    "currently open/fresh to fill TOP N"
                ),
            },
            "ranking_note": (
                "Cross-market class-normalized heuristic + temporally "
                "validated k-NN + bounded experience memory. Ranking is not "
                "a profit guarantee."
            ),
        }
