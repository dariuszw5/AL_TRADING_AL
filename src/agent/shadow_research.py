"""Real-market observation loop with an explicit no-execution boundary.

This module evaluates signals and simulates fractional positions in PLN.
It mutates only the local simulated ledger and cannot place external orders.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
from time import time

from src.agent.ai_manager import clean_candles, rank_asset
from src.data.assets import SUPPORTED_ASSETS
from src.data.data_provider import DataProvider
from src.agent.pln_broker import PlnLedger, PlnBroker
from src.data.fx_rates import fetch_pln_rates


EXECUTION_ENABLED = False
STATE_PATH = Path("data/live_state/ai_research.json")


class ShadowResearchRunner:
    """Fetch and score all supported markets without placing transactions."""

    def __init__(self, path=STATE_PATH, assets=SUPPORTED_ASSETS):
        self.path = Path(path)
        self.assets = tuple(assets)
        self.ledger = PlnLedger(self.path.parent)

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
                # Shadow mode also records technical signals that have not yet
                # collected five validation trades. This keeps the virtual
                # broker learning across all markets without enabling orders.
                exploratory = [row for row in rows if row.get("current_signal")]
                result["best"] = max(exploratory or rows, key=lambda row: row["score"])
                if exploratory:
                    result["recommendation"] = "OBSERVE_SIGNAL"
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
                    closed = clean_candles(candles, now_ms)
                    latest_candles[asset.symbol] = closed[-1] if closed else None
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
        try:
            fx = fetch_pln_rates(a.quote for a in self.assets)
        except Exception as exc:
            fx = {'rates': {}, 'issue': str(exc), 'currency': 'PLN'}
        specs = {a.symbol: a for a in self.assets}
        with self.ledger.transaction() as account:
            broker = PlnBroker(account)
            prices = {}
            for symbol, result in sorted(assets.items()):
                candle = latest_candles.get(symbol)
                rate = fx['rates'].get(specs[symbol].quote)
                # Yahoo agricultural futures prices are quoted in cents.
                if rate is not None and symbol in {'CORNUSD', 'WHEATUSD', 'SOYUSD', 'COFFEEUSD'}:
                    rate *= 0.01
                fresh = candle is not None and 0 <= now_ms - candle.timestamp <= 180000
                if rate is not None and fresh:
                    broker.process(symbol, candle, result.get('recommendation') == 'OBSERVE_SIGNAL', rate, now_ms)
                    prices[symbol] = (candle.close, rate)
                    result['market_price_pln'] = candle.close * rate
                else:
                    result['issue'] = 'Brak aktualnego kursu waluty lub świec; symulacja wstrzymana'
                result['virtual_execution']['position'] = 'LONG' if symbol in account['positions'] else 'FLAT'
            broker.rebalance(now_ms)
            broker.snapshot(prices, now_ms)
            broker_state = broker.public_state()
        state = {
            "version": 1,
            "mode": "RESEARCH_ONLY",
            "execution_enabled": EXECUTION_ENABLED,
            "model": "k-NN returns v1 shadow validation",
            "last_cycle": datetime.now(timezone.utc).isoformat(),
            "virtual_broker": broker_state,
            "fx": fx,
            "assets": {symbol: assets[symbol] for symbol in sorted(assets)},
        }
        self._write(state)
        return state
