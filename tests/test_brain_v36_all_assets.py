"""Every registered/static asset + frozen dynamic symbols, every horizon/side.

Synthetic OHLC below tests code invariants ONLY. Real provider validation must
be run separately by scripts.run_brain_v36_all_assets and coverage inspected.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from math import sin
from pathlib import Path

import pytest

from src.data.candle import Candle
from src.research.brain_v36.costs import cost_for_symbol
from src.research.brain_v36.engine import (
    RiskPlan, label_outcome, validate_history, walk_forward,
)
from src.research.brain_v36.snapshots import real_candles, snapshot_record, load_snapshot
from src.research.brain_v36.universe import (
    FIXED_BY_CLASS, REFERENCE_TYPES, ResearchInstrument, class_coverage,
    live_crypto_symbols, universe,
)
import scripts.run_brain_v36_all_assets as multiasset

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = json.loads(
    (ROOT / "config/brain_v36_costs.multiasset_SCENARIO.json").read_text(encoding="utf-8")
)
CATALOG = universe()
DYNAMIC = ("ADAUSDT", "ETHFIUSDT", "0GUSDT")


def candle(i, *, duration=300_000, value=100.0):
    return Candle(
        timestamp=i * duration,
        open=value,
        high=value + 0.2,
        low=value - 0.2,
        close=value, volume=10.0,
    )


def wave(size=1100, *, interval=5):
    result = []
    previous = 100.0
    for i in range(size):
        close = 100 + 0.001 * i + sin(i / 12) * 0.45
        result.append(Candle(
            timestamp=i * interval * 60_000,
            open=previous, high=max(previous, close) + 0.02,
            low=min(previous, close) - 0.02, close=close, volume=100,
        ))
        previous = close
    return result


def test_complete_catalogue_and_all_fixed_market_classes():
    known = {x.symbol: x for x in CATALOG}
    assert len(known) == len(CATALOG)
    assert set(class_coverage(CATALOG)) == {
        "crypto", "equity", "etf", "forex", "index", "commodity"
    }
    for klass, expected in FIXED_BY_CLASS.items():
        assert set(expected) <= {
            s for s, obj in known.items() if obj.asset_type == klass
        }, f"Asset class {klass} lost catalog coverage"
    assert all(a.provider in {"binance", "yahoo"} for a in CATALOG)
    assert all(a.reference_only == (a.instrument_type in REFERENCE_TYPES) for a in CATALOG)
    symbols = set(known)
    assert {"GOLD_FUT_CONT", "WTI_FUT_CONT"} <= symbols
    assert "XAUUSD" not in symbols and "WTIUSD" not in symbols  # aliases, not new assets


def test_dynamic_scanner_assets_join_without_replacing_static_universe():
    enriched = universe(DYNAMIC)
    names = {asset.symbol for asset in enriched}
    assert {asset.symbol for asset in CATALOG} <= names
    assert set(DYNAMIC) <= names
    assert len(enriched) == len(names)
    assert all(
        asset.origin == "scanner_snapshot" and asset.provider == "binance"
        and asset.asset_type == "crypto"
        for asset in enriched if asset.symbol in DYNAMIC
    )
    for invalid in ("EURUSDX", "BTCUSD", "../SECRET", "x@yUSDT", ""):
        with pytest.raises(ValueError, match="dynamic"):
            universe([invalid])


def test_current_scanner_snapshot_extracts_only_real_present_usdt_symbols():
    ai = {"ranking": [
        {"symbol": "BTCUSDT"}, {"symbol": "ETHFIUSDT"},
        {"symbol": "0GUSDT"}, {"symbol": "NVDA"}, {"symbol": "XAUUSD"},
    ]}
    research = {"opportunities": [
        {"symbol": "ETHFIUSDT"}, {"symbol": "ADAUSDT"}, {"symbol": "SPY"},
    ]}
    assert live_crypto_symbols(ai, research) == (
        "0GUSDT", "ADAUSDT", "BTCUSDT", "ETHFIUSDT"
    )


@pytest.mark.parametrize("asset", universe(DYNAMIC), ids=lambda a: a.symbol)
@pytest.mark.parametrize("bar_minutes", (1, 5), ids=("1m", "5m"))
@pytest.mark.parametrize("horizon,side", [
    (15, "LONG"), (15, "SHORT"), (30, "LONG"), (30, "SHORT"),
    (60, "LONG"), (60, "SHORT"),
])
def test_every_asset_obeys_same_real_minute_execution_and_separate_cost_profile(
    asset, horizon, side, bar_minutes,
):
    costs, meta = cost_for_symbol(asset.symbol, SCENARIO)
    assert meta["asset_type"] == asset.asset_type
    assert meta["reference_only"] == asset.reference_only
    assert "UNVERIFIED_" in costs.source
    assert costs.round_trip > 0
    risk = RiskPlan(horizon_minutes=horizon, bar_minutes=bar_minutes)
    candles = [
        candle(i, duration=risk.candle_duration_ms)
        for i in range(risk.horizon_bars + 1)
    ]
    result = label_outcome(candles, 0, side, risk, costs)
    assert result["entry_timestamp"] == candles[1].timestamp
    assert result["exit_timestamp"] == candles[risk.horizon_bars].timestamp
    assert result["exit_timestamp"] - result["signal_timestamp"] == horizon * 60_000
    assert result["reason"] == "TIME_EXIT"
    assert result["return_fraction"] == pytest.approx(-costs.round_trip)


@pytest.mark.parametrize("asset_class", list(FIXED_BY_CLASS))
def test_each_asset_class_has_independent_walk_forward_and_sealed_test(asset_class):
    asset = next(x for x in CATALOG if x.asset_type == asset_class)
    cost, _ = cost_for_symbol(asset.symbol, SCENARIO)
    result = walk_forward(
        wave(), symbol=asset.symbol, asset_type=asset.asset_type,
        instrument_type=asset.instrument_type, costs=cost,
        risk=RiskPlan(horizon_minutes=15, bar_minutes=5),
        initial_train=450, validation_size=250, test_size=250,
        evaluate_test=False,
    )
    assert result["asset_type"] == asset_class
    assert result["reference_only"] == asset.reference_only
    assert len(result["results"]) == 6
    assert all(row["test"] is None and row["test_scan"] is None
               for row in result["results"])


def test_missing_cost_profile_fails_closed_for_any_market():
    for asset_class in FIXED_BY_CLASS:
        symbol = next(x.symbol for x in CATALOG if x.asset_type == asset_class)
        missing = {kind: value for kind, value in SCENARIO.items()
                   if kind != asset_class}
        with pytest.raises(ValueError, match="No cost model"):
            cost_for_symbol(symbol, missing)


def test_scanner_api_merges_current_dynamic_with_fixed_universe(monkeypatch):
    class Response:
        def __init__(self, obj):
            self.obj = obj
        def raise_for_status(self):
            pass
        def json(self):
            return self.obj
    def fake_get(url, **kwargs):
        if url.endswith("/api/ai"):
            return Response({"ranking": [
                {"symbol": "BTCUSDT"}, {"symbol": "ETHFIUSDT"},
                {"symbol": "NVDA"}, {"symbol": "0GUSDT"},
            ]})
        return Response({"opportunities": [{"symbol": "ADAUSDT"}, {"symbol": "SPY"}]})
    monkeypatch.setattr(multiasset.requests, "get", fake_get)
    dynamic, report = multiasset._api_read("https://research.example.org")
    assert set(DYNAMIC) <= set(dynamic)
    assert len(universe(dynamic)) >= len(CATALOG) + 3
    assert report["ai_ranking_rows"] == 4



def test_incomplete_ai_scanner_response_is_never_labeled_full_dynamic_coverage(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"status": "ok"}  # no ranking; cannot prove current universe
    monkeypatch.setattr(multiasset.requests, "get",
                        lambda *args, **kwargs: Response())
    with pytest.raises(ValueError, match="full AI ranking"):
        multiasset._api_read("https://research.example.org")



def test_binance_snapshot_closes_forming_bar_and_retains_real_timestamps():
    instrument = next(a for a in CATALOG if a.symbol == "BTCUSDT")
    cutoff = 3 * 300_000 + 150_000
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return [
                [0, "100", "101", "99", "100", "1"],
                [300_000, "100", "101", "99", "100", "1"],
                [600_000, "100", "101", "99", "100", "1"],
                [900_000, "100", "101", "99", "100", "1"],
            ]
    class Fake:
        def get(self, url, **kwargs):
            assert kwargs["params"]["interval"] == "5m"
            return Response()
    bars = real_candles(instrument, bar_minutes=5, limit=100,
                        as_of_ms=cutoff, session=Fake())
    assert [c.timestamp for c in bars] == [0, 300_000, 600_000]


def test_yahoo_snapshot_uses_actual_provider_symbol_and_drops_open_candle():
    instrument = next(a for a in CATALOG if a.symbol == "SP500_INDEX")
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"chart": {"result": [{
                "timestamp": [0, 300, 600, 900],
                "indicators": {"quote": [{
                    "open": [100, 100, 100, 100],
                    "high": [101, 101, 101, 101],
                    "low": [99, 99, 99, 99],
                    "close": [100, 100, 100, 100],
                    "volume": [None, None, None, None],
                }]},
            }]}}
    class Fake:
        def get(self, url, **kwargs):
            assert "%5EGSPC" in url
            assert kwargs["params"]["interval"] == "5m"
            return Response()
    bars = real_candles(instrument, bar_minutes=5, limit=100,
                        as_of_ms=1_100_000, session=Fake())
    assert [c.timestamp for c in bars] == [0, 300_000, 600_000]
    assert all(c.volume == 0 for c in bars)



def test_quote_source_retries_a_transient_timeout_without_fabricating_data(monkeypatch):
    import requests
    import src.research.brain_v36.snapshots as snapshots

    calls = []
    monkeypatch.setattr(snapshots, "sleep", lambda seconds: None)

    class Response:
        def raise_for_status(self):
            return None
        def json(self):
            return {"source": "ACTUAL_PROVIDER_RESPONSE"}

    class Session:
        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            if len(calls) == 1:
                raise requests.exceptions.Timeout("transient network failure")
            return Response()

    assert snapshots._get(Session(), "https://provider.example/api",
                          params={"interval": "5m"}) == {
        "source": "ACTUAL_PROVIDER_RESPONSE"
    }
    assert len(calls) == 2



def test_frozen_snapshot_checksum_and_immutable_write(tmp_path):
    instrument = CATALOG[0]
    bars = [candle(i) for i in range(100)]
    cutoff = bars[-1].timestamp + 300_000
    path = tmp_path / "snapshots" / "one.json"
    row = snapshot_record(instrument, bars, path=path,
                          bar_minutes=5, as_of_ms=cutoff)
    assert load_snapshot(row, base=tmp_path) == bars
    assert row["sha256"] == sha256(path.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        snapshot_record(instrument, bars, path=path,
                        bar_minutes=5, as_of_ms=cutoff)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="checksum"):
        load_snapshot(row, base=tmp_path)
    with pytest.raises(ValueError, match="Only independent"):
        load_snapshot({**row, "path": str(tmp_path.parent / "live_state.json")},
                      base=tmp_path)


def test_multiasset_evaluation_audits_every_symbol_and_reserves_outer_holdout(
    tmp_path, monkeypatch,
):
    # Prepare an immutable manifest with all fixed symbols accounted for; only
    # ONE market has sufficient synthetic OHLC. No network is called.
    out = tmp_path / "diagnostics" / "brain_v36" / "multiasset"
    monkeypatch.setattr(multiasset, "OUT", out)
    monkeypatch.setattr(multiasset, "SNAPSHOTS", out / "snapshots")
    sample = next(a for a in CATALOG if a.symbol == "BTCUSDT")
    bars = wave(1200)
    cutoff = bars[-1].timestamp + 300_000
    frozen = snapshot_record(
        sample, bars, path=multiasset.SNAPSHOTS / "snap" / "BTCUSDT_5m.json",
        bar_minutes=5, as_of_ms=cutoff,
    )
    all_entries = [frozen if a.symbol == sample.symbol else {
        **a.as_dict(), "status": "DATA_UNAVAILABLE",
        "reason": "Offline deterministic fixture", "count": 0,
        "bar_minutes": 5, "as_of_ms": cutoff,
    } for a in CATALOG]
    manifest = {
        "mode": "RESEARCH_ONLY", "bar_minutes": 5,
        "dynamic_discovery": {
            "status": "COMPLETE_API_READ", "dynamic_symbols": [],
        },
        "instruments": all_entries,
    }
    path = out / "universe_fixture.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    cost_path = tmp_path / "cost_scenario.json"
    cost_path.write_text(json.dumps(SCENARIO), encoding="utf-8")
    expected_last_visible = bars[-161].timestamp
    original = multiasset.walk_forward
    observed = []

    def holdout_guard(candles, **kwargs):
        observed.append(candles[-1].timestamp)
        assert candles[-1].timestamp == expected_last_visible
        assert kwargs["evaluate_test"] is False
        return original(candles, **kwargs)

    monkeypatch.setattr(multiasset, "walk_forward", holdout_guard)
    output, csv_path, report = multiasset.evaluate(
        path, costs_path=cost_path,
        initial_train=480, validation_size=320, internal_test_size=160,
        outer_holdout=160, horizons=(15, 30, 60), stamp="fixture",
    )
    assert output.is_file()
    assert csv_path.is_file()
    assert len(report["instruments"]) == len(CATALOG)
    btc = next(x for x in report["instruments"] if x["symbol"] == "BTCUSDT")
    assert btc["evaluation_status"] == "VALIDATION_ONLY_COMPLETED"
    assert btc["validated_rows"] == 3 * 6
    assert all(x["evaluation_status"] == "SKIPPED_DATA_UNAVAILABLE"
               for x in report["instruments"] if x["symbol"] != "BTCUSDT")
    assert all(x["outer_holdout_status"] == "RESERVED_NOT_PASSED_TO_EVALUATOR"
               and x["test"] is None for x in report["results"])
    # Later TEST quote modifications do not change saved development reports.
    mutated = list(bars)
    for b in mutated[-160:]:
        b.close += 10
    assert report["results"]
    assert len(observed) == 3
    assert all(ts == expected_last_visible for ts in observed)
