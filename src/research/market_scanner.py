from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from math import log10
import os
import time
from pathlib import Path

import requests

from src.agent.ai_manager import features as ai_features, rank_asset
from src.data.assets import SUPPORTED_ASSETS, AssetSpec, dynamic_binance_asset
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
    """Selects ten strongest research opportunities from real market data.

    The ranking is a research heuristic/model, never a profit guarantee.
    All execution remains virtual paper trading.
    """

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.provider = DataProvider()
        self.market_log = DailyJsonlStore(self.data_dir / "logs", "market_universe", 14)
        self.candle_log = DailyJsonlStore(self.data_dir / "logs", "selected_candles", 30)
        self.memory = ExperienceMemory(self.data_dir)
        self.min_quote_volume = float(
            os.getenv("AL_TRADING_MIN_QUOTE_VOLUME_USDT", "10000000")
        )
        self.preselect = max(10, int(os.getenv("AL_TRADING_PRESELECT", "30")))
        self.top_n = max(1, min(20, int(os.getenv("AL_TRADING_TOP_N", "10"))))
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
            "event_type": "MARKET_UNIVERSE_SNAPSHOT",
            "provider": "binance",
            "symbols": [candidate.as_dict() for candidate in candidates],
            "count": len(candidates),
        })
        return candidates

    def _configured_non_crypto(self) -> list[AssetSpec]:
        return [asset for asset in SUPPORTED_ASSETS if asset.provider != "binance"]

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
            rows = rank_asset(asset.symbol, candles)
            best = max(rows, key=lambda row: row["score"], default=None)
            if best is None:
                return None
            latest = candles[-1]
            feat = list(ai_features(candles, len(candles) - 1))
            memory = self.memory.adjustment(
                features=feat,
                strategy=str(best["strategy"]),
                macro_tags=macro_tags,
            )
            combined = (
                float(best["score"])
                + memory.adjustment
                + market_score / 10_000.0
            )
            last_logged = self._last_logged_candle.get(asset.symbol)
            if last_logged != latest.timestamp:
                self.candle_log.append({
                    "event_type": "SELECTED_MARKET_CANDLE",
                    "symbol": asset.symbol,
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
                "instrument_type": asset.instrument_type,
                "strategy": best["strategy"],
                "eligible": bool(best.get("eligible")),
                "model_score": float(best["score"]),
                "combined_score": combined,
                "expected_net_return": float(best.get("expected_net_return", 0.0)),
                "neighbor_spread": float(best.get("neighbor_spread", 0.0)),
                "validation_trades": int(best.get("validation_trades", 0)),
                "validation_mean": best.get("validation_mean"),
                "market_score": float(market_score),
                "features": feat,
                "memory": memory.as_dict(),
                "latest_timestamp": latest.timestamp,
                "last_price": latest.close,
                "macro_tags": list(macro_tags),
            }
        except Exception as exc:
            return {
                "symbol": asset.symbol,
                "name": asset.name,
                "provider": asset.provider,
                "error": f"{type(exc).__name__}: {exc}",
                "combined_score": -999.0,
            }

    def scan(self, macro_tags: list[str] | None = None) -> dict:
        macro_tags = list(macro_tags or [])
        discovered = self.discover()
        preliminary = discovered[: self.preselect]
        asset_by_symbol = {
            candidate.symbol: dynamic_binance_asset(candidate.symbol)
            for candidate in preliminary
        }
        market_scores = {
            candidate.symbol: candidate.market_score for candidate in preliminary
        }
        for asset in self._configured_non_crypto():
            asset_by_symbol[asset.symbol] = asset
            market_scores.setdefault(asset.symbol, 0.0)

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
        valid.sort(key=lambda row: row["combined_score"], reverse=True)
        top = valid[: self.top_n]
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

        return {
            "timestamp": int(time.time() * 1000),
            "universe_count": len(discovered),
            "preselected_count": len(asset_by_symbol),
            "top_n": self.top_n,
            "opportunities": top,
            "errors": [row for row in rows if "error" in row],
            "paper_only": True,
            "real_orders": False,
            "ranking_note": (
                "Heuristic + temporally validated k-NN + bounded experience "
                "memory; ranking is not a profit guarantee."
            ),
        }
