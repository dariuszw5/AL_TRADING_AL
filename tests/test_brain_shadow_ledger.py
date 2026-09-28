"""Persistent shadow evidence must never become a real/paper order."""
from copy import deepcopy
from types import SimpleNamespace

import src.agent.ai_manager as ai
from src.agent.shadow_ledger import (
    SHADOW_HISTORY_LIMIT,
    empty_shadow_ledger,
    update_shadow_ledger,
)


T0 = 1_800_000_000_000


def candle(ts, *, o=100.0, h=100.0, l=100.0, c=100.0):
    return SimpleNamespace(
        timestamp=ts, open=o, high=h, low=l, close=c, volume=10.0
    )


def signal(side="LONG", eligible=False, signal_on=True):
    return {
        "symbol": "TESTUSDT",
        "strategy": "trend",
        "side": side,
        "live_signal": signal_on,
        "eligible": eligible,
        "supervisor_status": "PAUSED",
    }


def advance(account, bars, rows, horizon=2):
    return update_shadow_ledger(
        account,
        {"TESTUSDT": bars},
        rows,
        minute=ai.MINUTE,
        horizon=horizon,
        exit_price=ai.exit_price,
        net_return=ai.net_return,
    )


def test_shadow_waits_for_closed_next_candle_and_does_not_touch_broker_fields():
    account = {
        "balance": 970.0,
        "realized_pnl": -30.0,
        "positions": {},
        "pending": [],
        "trades": [],
        "strategy_learning": {"trend": {"trades": 22}},
    }
    broker_snapshot = deepcopy(account)
    first = candle(T0)
    second = candle(T0 + ai.MINUTE, o=100, h=100, l=98, c=99)

    observed = advance(account, [first], [signal()], horizon=2)
    assert observed["summary"]["pending"] == 1
    assert observed["summary"]["completed_total"] == 0

    observed = advance(account, [first], [signal()], horizon=2)
    assert observed["summary"]["pending"] == 1
    assert observed["summary"]["completed_total"] == 0

    observed = advance(account, [first, second], [], horizon=2)
    assert observed["summary"]["completed_total"] == 1
    assert observed["summary"]["pending"] == 0
    assert observed["summary"]["open"] == 0
    assert observed["trades"][0]["reason"] == "STOP_LOSS"
    assert observed["trades"][0]["return_fraction"] < 0
    assert observed["trades"][0]["eligible_at_signal"] is False
    assert observed["trades"][0]["counterfactual"] is True

    assert {key: account[key] for key in broker_snapshot} == broker_snapshot


def test_short_direction_and_non_overlapping_signal_are_persisted():
    account = {}
    first = candle(T0)
    second = candle(T0 + ai.MINUTE, o=100, h=100, l=99.9, c=99.9)
    third = candle(T0 + 2 * ai.MINUTE, o=99.9, h=99.9, l=98, c=98)

    advance(account, [first], [signal(side="SHORT")], horizon=2)
    advance(account, [first, second], [signal(side="SHORT")], horizon=2)
    # The active shadow key prevents overlapping duplicate entries.
    assert len(account["shadow"]["positions"]) == 1
    assert len(account["shadow"]["pending"]) == 0

    advance(account, [first, second, third], [], horizon=2)
    s = account["shadow"]
    assert len(s["trades"]) == 1
    assert s["trades"][0]["side"] == "SHORT"
    assert s["trades"][0]["reason"] == "TIME_EXIT"
    assert s["trades"][0]["return_fraction"] > 0
    assert s["learning"]["trend|SHORT"]["trades"] == 1
    assert s["learning"]["trend|SHORT"]["wins"] == 1


def test_missing_next_candle_expires_observation_without_fabricating_pnl():
    account = {}
    first = candle(T0)
    third = candle(T0 + 2 * ai.MINUTE)
    advance(account, [first], [signal()], horizon=2)
    advance(account, [first, third], [], horizon=2)
    s = account["shadow"]
    assert s["summary"]["expired_signals"] == 1
    assert s["summary"]["completed_total"] == 0
    assert s["positions"] == {}
    assert s["pending"] == {}


def test_repeated_same_timestamp_never_creates_second_observation():
    account = {}
    first = candle(T0)
    for _ in range(4):
        advance(account, [first], [signal()], horizon=2)
    assert len(account["shadow"]["pending"]) == 1
    assert len(account["shadow"]["seen"]) == 1


def test_history_is_bounded_but_aggregate_evidence_is_not_reset():
    account = {"shadow": empty_shadow_ledger()}
    s = account["shadow"]
    s["trades"] = [{"return_fraction": -0.01}] * SHADOW_HISTORY_LIMIT
    s["learning"]["trend|LONG"] = {
        "trades": 500,
        "wins": 10,
        "total_return": -1.0,
        "gross_win": 0.1,
        "gross_loss": -1.1,
    }
    first = candle(T0)
    second = candle(T0 + ai.MINUTE, o=100, h=100, l=98, c=99)
    advance(account, [first], [signal()], horizon=2)
    advance(account, [first, second], [], horizon=2)
    assert len(s["trades"]) == SHADOW_HISTORY_LIMIT
    assert s["learning"]["trend|LONG"]["trades"] == 501
    assert s["summary"]["completed_total"] == 501


def test_manager_persists_shadow_evidence_without_real_trades(tmp_path, monkeypatch):
    path = tmp_path / "ai_paper.json"
    manager = ai.AIPaperManager(path, assets=[])
    s = manager.state
    s["funded_capital"] = 1000.0
    s["initial_balance"] = 1000.0
    s["balance"] = 1000.0
    s["equity"] = 1000.0
    s["peak"] = 1000.0

    def fake_rank(symbol, candles):
        return [{
            **signal(signal_on=(candles[-1].timestamp == T0)),
            "score": -0.01,
            "expected_net_return": -0.01,
            "neighbor_spread": 0.001,
            "validation_trades": 0,
            "validation_mean": None,
        }]

    monkeypatch.setattr(ai, "rank_asset", fake_rank)
    first = candle(T0 - ai.MINUTE)
    signal_bar = candle(T0)
    exit_bar = candle(T0 + ai.MINUTE, o=100, h=100, l=98, c=99)
    manager.step(
        {"TESTUSDT": [first, signal_bar]},
        now_ms=T0 + ai.MINUTE + 5_000,
    )
    assert len(manager.state["shadow"]["pending"]) == 1

    manager.step(
        {"TESTUSDT": [first, signal_bar, exit_bar]},
        now_ms=T0 + 2 * ai.MINUTE + 5_000,
    )
    assert manager.state["shadow"]["summary"]["completed_total"] == 1
    assert manager.state["trades"] == []
    assert manager.state["positions"] == {}
    assert manager.state["balance"] == 1000.0
    assert manager.state["equity"] == 1000.0
    assert manager.state["strategy_learning"]["trend"]["trades"] == 0

    loaded = ai.AIPaperManager(path, assets=[])
    assert loaded.state["shadow"]["summary"]["completed_total"] == 1
    assert loaded.state["mode"] == "PAPER_ONLY"
