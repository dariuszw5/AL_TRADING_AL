"""Real-market observation loop with an explicit no-execution boundary.

This module evaluates the existing strategy selector on fresh candles and
stores hypothetical signals. It deliberately has no order, position, or
portfolio mutation code; the runner is safe to use while tuning the strategy.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
from time import time

from src.agent.ai_manager import clean_candles, rank_asset
from src.data.assets import SUPPORTED_ASSETS
from src.data.data_provider import DataProvider
from src.agent.virtual_broker import VirtualBroker


EXECUTION_ENABLED = False
STATE_PATH = Path("data/live_state/ai_research.json")


class ShadowResearchRunner:
    """Fetch and score all supported markets without placing transactions."""

    def __init__(self, path=STATE_PATH, assets=SUPPORTED_ASSETS):
        self.path = Path(path)
        self.assets = tuple(assets)
        self.broker = VirtualBroker()

    @staticmethod
    def _fetch(asset):
        provider = DataProvider()
        candles = provider.get_candles(asset.symbol, "1m", 1000)
        return asset, candles

    def _analyze(self, asset, candles, now_ms):
        result = {
            "symbol": asset.symbol,
            "name": asset.name,
            "asset_type": asset.asset_type,
            "provider": asset.provider,
            "provider_symbol": asset.provider_symbol,
            "market_price": None,
            "rows": [],
            "best": None,
            "recommendation": "WAIT",
            "virtual_execution": {
                "enabled": True,
                "broker_orders": False,
                "position": "FLAT",
                "note": "Symulacja wejścia/wyjścia i kosztów; brak zlecenia u brokera",
            },
        }
        try:
            clean = clean_candles(candles, now_ms)
            if clean:
                result["market_price"] = clean[-1].close
            rows = rank_asset(asset.symbol, clean)
            result["rows"] = rows
            eligible = [row for row in rows if row.get("eligible")]
            if eligible:
                best = max(eligible, key=lambda row: row["score"])
                result["best"] = best
                result["recommendation"] = "OBSERVE_SIGNAL"
            elif rows:
                result["best"] = max(rows, key=lambda row: row["score"])
            if len(clean) < 500:
                result["issue"] = f"Za mało zamkniętych świec: {len(clean)}/500"
        except Exception as exc:  # One unavailable market must not stop the cycle.
            result["issue"] = str(exc)
        return result

    def _write(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def run_once(self):
        now_ms = int(time() * 1000)
        assets = {}
        latest_candles = {}
        with ThreadPoolExecutor(max_workers=min(8, len(self.assets))) as pool:
            futures = {pool.submit(self._fetch, asset): asset for asset in self.assets}
            for future in as_completed(futures):
                asset = futures[future]
                try:
                    _, candles = future.result()
                    latest_candles[asset.symbol] = candles[-1] if candles else None
                    assets[asset.symbol] = self._analyze(asset, candles, now_ms)
                except Exception as exc:
                    assets[asset.symbol] = {
                        "symbol": asset.symbol,
                        "name": asset.name,
                        "asset_type": asset.asset_type,
                        "provider": asset.provider,
                        "provider_symbol": asset.provider_symbol,
                        "market_price": None,
                        "rows": [],
                        "best": None,
                        "recommendation": "WAIT",
                        "virtual_execution": {
                            "enabled": True,
                            "broker_orders": False,
                            "position": "FLAT",
                        },
                        "issue": str(exc),
                    }
        for symbol, result in assets.items():
            candle = latest_candles.get(symbol)
            if candle is not None:
                self.broker.mark(symbol, candle, candle.timestamp)
                if result.get("recommendation") == "OBSERVE_SIGNAL":
                    self.broker.open(symbol, candle.close, candle.timestamp)
                result["virtual_execution"]["position"] = (
                    "LONG" if symbol in self.broker.positions else "FLAT")
        prices = {s: r["market_price"] for s, r in assets.items()
                  if r.get("market_price") is not None}
        self.broker.snapshot(prices, now_ms)
        state = {
            "version": 1,
            "mode": "RESEARCH_ONLY",
            "execution_enabled": EXECUTION_ENABLED,
            "model": "k-NN returns v1 shadow validation",
            "last_cycle": datetime.now(timezone.utc).isoformat(),
            "virtual_broker": {
                "initial_balance": self.broker.initial_balance,
                "balance": self.broker.balance,
                "execution_enabled": False,
                "trades": self.broker.trades[-300:],
                "equity_curve": self.broker.equity_curve[-300:],
            },
            "assets": {symbol: assets[symbol] for symbol in sorted(assets)},
        }
        self._write(state)
        return state
