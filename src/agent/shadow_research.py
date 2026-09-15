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
from src.data.geopolitical_feed import GeopoliticalFeed
from src.agent.geopolitical_analyst import GeopoliticalAnalyst


EXECUTION_ENABLED = False
STATE_PATH = Path("data/live_state/ai_research.json")


class ShadowResearchRunner:
    """Fetch and score all supported markets without placing transactions."""

    def __init__(self, path=STATE_PATH, assets=SUPPORTED_ASSETS):
        self.path = Path(path)
        self.assets = tuple(assets)
        self.ledger = PlnLedger(self.path.parent)
        self.geo_feed = GeopoliticalFeed()
        self.geo_analyst = GeopoliticalAnalyst()

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
            eligible = [row for row in rows if row.get("confidence_eligible")]
            if eligible:
                best = max(eligible, key=lambda row: row["confidence_score"])
                result["best"] = best
                result["recommendation"] = "OBSERVE_SIGNAL"
            elif rows:
                # Keep analysing lower-confidence assets, but never open a
                # virtual position from them. They can later graduate into Top
                # 10 after enough independent validation examples.
                result["best"] = max(rows, key=lambda row: row.get("confidence_score", 0))
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

    @staticmethod
    def rank_candidates(assets, limit=10):
        """Rank only model-scored assets; ties are deterministic by symbol."""
        scored = []
        for symbol, result in assets.items():
            best = result.get('best') or {}
            score = best.get('confidence_score')
            if isinstance(score, (int, float)):
                scored.append((symbol, float(score), best.get('strategy'),
                               best.get('validation_trades', 0)))
        scored.sort(key=lambda item: (-item[1], item[0]))
        return [
            {'rank': index, 'symbol': symbol, 'profit_probability_lower': score,
             'strategy': strategy, 'validation_trades': samples}
            for index, (symbol, score, strategy, samples) in enumerate(scored[:limit], start=1)
        ]

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
        top_10 = self.rank_candidates(assets)
        selected_symbols = {item['symbol'] for item in top_10}
        rank_by_symbol = {item['symbol']: item for item in top_10}
        for symbol, result in assets.items():
            result['portfolio_rank'] = rank_by_symbol.get(symbol, {}).get('rank')
            result['portfolio_selected'] = symbol in selected_symbols
        feed = self.geo_feed.fetch()
        geopolitical = self.geo_analyst.assess(
            feed['events'], {asset.asset_type for asset in self.assets})
        geopolitical['source'] = feed['source']
        geopolitical['issue'] = feed['issue']
        with self.ledger.transaction() as account:
            broker = PlnBroker(account)
            prices = {}
            # Positions are rotated only after this cycle has ranked every
            # market. Missing/stale quotes keep their existing protective exit
            # management rather than inventing an exit price.
            for symbol in sorted(set(account['positions']) - selected_symbols):
                candle = latest_candles.get(symbol)
                spec = specs.get(symbol)
                rate = fx['rates'].get(spec.quote) if spec else None
                if rate is not None and symbol in {'CORNUSD', 'WHEATUSD', 'SOYUSD', 'COFFEEUSD'}:
                    rate *= 0.01
                if candle is not None and rate is not None and 0 <= now_ms - candle.timestamp <= 180000:
                    broker.close_for_rotation(symbol, candle, rate, now_ms)
            for symbol, result in sorted(assets.items()):
                candle = latest_candles.get(symbol)
                rate = fx['rates'].get(specs[symbol].quote)
                # Yahoo agricultural futures prices are quoted in cents.
                if rate is not None and symbol in {'CORNUSD', 'WHEATUSD', 'SOYUSD', 'COFFEEUSD'}:
                    rate *= 0.01
                fresh = candle is not None and 0 <= now_ms - candle.timestamp <= 180000
                if rate is not None and fresh:
                    best = result.get('best') or {}
                    market_risk = geopolitical['asset_risk'].get(
                        specs[symbol].asset_type,
                        {'level': 'NORMAL', 'allow_new_entries': True},
                    )
                    requested_signal = (
                        result.get('recommendation') == 'OBSERVE_SIGNAL'
                        and symbol in selected_symbols
                    )
                    signal = requested_signal and market_risk['allow_new_entries']
                    note = None
                    if result.get('recommendation') == 'OBSERVE_SIGNAL' and symbol not in selected_symbols:
                        note = 'Poza rankingiem Top 10'
                    if requested_signal and not signal:
                        note = f"Ryzyko geopolityczne: {market_risk['level']}"
                    action = broker.process(
                        symbol,
                        candle,
                        signal,
                        rate,
                        now_ms,
                        asset_type=specs[symbol].asset_type,
                        strategy=best.get('strategy'),
                        score=best.get('score'),
                        note=note,
                        confidence_probability=best.get('profit_probability_lower'),
                        validation_trades=best.get('validation_trades'),
                    )
                    result['virtual_execution']['action'] = action
                    result['geopolitical_risk'] = market_risk
                    prices[symbol] = (candle.close, rate)
                    result['market_price_pln'] = candle.close * rate
                else:
                    result['issue'] = 'Brak aktualnego kursu waluty lub świec; symulacja wstrzymana'
                    result['virtual_execution']['action'] = 'WAIT_FOR_DATA'
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
            "geopolitical_research": geopolitical,
            "top_10": top_10,
            "assets": {symbol: assets[symbol] for symbol in sorted(assets)},
        }
        self._write(state)
        return state
