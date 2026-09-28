"""Only reliable recent counterfactual evidence may reorder eligible choices."""
from copy import deepcopy
from types import SimpleNamespace

import src.agent.ai_manager as ai
from src.agent.shadow_advisor import (
    SHADOW_MAX_RANKING_BONUS,
    apply_shadow_advisor,
    assess_shadow_evidence,
)
from src.agent.shadow_ledger import empty_shadow_ledger


T0 = 1_800_000_000_000


def make_shadow(*, strategy="trend", side="LONG", returns=None, symbols=None):
    returns = [0.005] * 48 if returns is None else returns
    symbols = ("AAAUSDT", "BBBUSDT", "CCCUSDT") if symbols is None else symbols
    shadow = empty_shadow_ledger()
    for i, value in enumerate(returns):
        shadow["trades"].append({
            "symbol": symbols[i % len(symbols)],
            "strategy": strategy,
            "side": side,
            "signal_timestamp": T0 - (len(returns) - i + 2) * 900_000,
            "exit_timestamp": T0 - (len(returns) - i + 1) * 900_000,
            "return_fraction": value,
            "counterfactual": True,
        })
    return shadow


def candidate(*, symbol="TESTUSDT", strategy="trend",
              side="LONG", score=0.004, eligible=True):
    return {
        "symbol": symbol,
        "strategy": strategy,
        "side": side,
        "score": score,
        "eligible": eligible,
        "live_signal": True,
    }


def test_no_shadow_evidence_keeps_base_order_and_original_scores():
    rows = [
        candidate(strategy="breakout", score=0.005),
        candidate(strategy="trend", score=0.0049),
    ]
    before = deepcopy(rows)
    diagnostics = apply_shadow_advisor(rows, empty_shadow_ledger())
    assert diagnostics["trend|LONG"]["status"] == "INSUFFICIENT_SAMPLES"
    assert [r["shadow_selection_bonus"] for r in rows] == [0, 0]
    assert [r["shadow_selection_score"] for r in rows] == [
        original["score"] for original in before
    ]
    assert all(r["eligible"] for r in rows)


def test_two_chronological_positive_windows_add_bounded_ranking_bonus():
    shadow = make_shadow()
    evidence = assess_shadow_evidence(shadow, "trend", "LONG")
    assert evidence["samples"] == 48
    assert evidence["distinct_symbols"] == 3
    assert evidence["status"] == "SHADOW_CONFIRMED_FOR_RANKING"
    assert 0 < evidence["bonus"] <= SHADOW_MAX_RANKING_BONUS


def test_bad_older_half_cannot_be_erased_by_lucky_recent_half():
    shadow = make_shadow(returns=[-0.01] * 24 + [0.04] * 24)
    evidence = assess_shadow_evidence(shadow, "trend", "LONG")
    assert evidence["mean_after_costs"] > 0
    assert evidence["status"] == "INCONSISTENT_WINDOWS"
    assert evidence["bonus"] == 0


def test_one_symbol_cannot_dominate_challenger_evidence():
    shadow = make_shadow(symbols=("ONLYUSDT",))
    evidence = assess_shadow_evidence(shadow, "trend", "LONG")
    assert evidence["status"] == "CONCENTRATED_SAMPLE"
    assert evidence["bonus"] == 0


def test_short_experience_never_boosts_long_strategy():
    shadow = make_shadow(side="SHORT")
    rows = [candidate(side="LONG"), candidate(side="SHORT")]
    apply_shadow_advisor(rows, shadow)
    assert rows[0]["shadow_selection_bonus"] == 0
    assert rows[1]["shadow_selection_bonus"] > 0


def test_model_rejected_and_paused_candidates_never_become_eligible():
    shadow = make_shadow()
    rows = [
        candidate(eligible=False, score=0.006),
        candidate(eligible=True, score=0.004),
    ]
    rows[0]["eligibility_reason"] = "STRATEGY_SUPERVISOR_PAUSED"
    original = deepcopy(rows)
    apply_shadow_advisor(rows, shadow)
    assert rows[0]["shadow_selection_bonus"] == 0
    assert rows[0]["eligible"] is False
    assert rows[0]["eligibility_reason"] == original[0]["eligibility_reason"]
    assert rows[0]["score"] == original[0]["score"]
    assert rows[1]["score"] == original[1]["score"]
    assert rows[1]["shadow_selection_bonus"] > 0


def test_actual_supervisor_pause_cannot_be_reversed_by_shadow_bonus():
    from src.agent.strategy_supervisor import supervise_candidate

    shadow = make_shadow()
    row = {
        **candidate(score=0.005, eligible=True),
        "validated": False,
        "exploratory": False,
        "validation_trades": 0,
        "validation_mean": None,
    }
    supervise_candidate(
        row,
        {"strategies": {"trend": {"status": "PAUSED", "reason": "live losses"}}},
    )
    assert row["eligible"] is False
    apply_shadow_advisor([row], shadow)
    assert row["eligible"] is False
    assert row["shadow_selection_bonus"] == 0
    assert row["eligibility_reason"] == "STRATEGY_SUPERVISOR_PAUSED"


def test_all_model_rejected_signals_stay_rejected_with_positive_shadow():
    shadow = make_shadow()
    rows = [
        candidate(eligible=False, score=-0.002),
        candidate(eligible=False, score=-0.001),
    ]
    apply_shadow_advisor(rows, shadow)
    assert not any(row["eligible"] for row in rows)
    assert all(row["shadow_selection_bonus"] == 0 for row in rows)


def test_duplicate_samples_and_unverified_pnl_do_not_inflate_confidence():
    shadow = make_shadow(returns=[0.004])
    one = shadow["trades"][0]
    shadow["trades"] = [deepcopy(one) for _ in range(80)]
    shadow["trades"][0]["counterfactual"] = False
    evidence = assess_shadow_evidence(shadow, "trend", "LONG")
    assert evidence["samples"] == 1
    assert evidence["bonus"] == 0


def test_shadow_bonus_reorders_only_already_eligible_candidates():
    shadow = make_shadow(strategy="trend")
    rows = [
        candidate(strategy="breakout", symbol="AAAUSDT", score=0.0051),
        candidate(strategy="trend", symbol="BBBUSDT", score=0.0048),
    ]
    account = {"balance": 970.0, "positions": {}, "strategy_learning": {}}
    saved = deepcopy(account)
    apply_shadow_advisor(rows, shadow)
    rows.sort(
        key=lambda row: (
            bool(row["eligible"]),
            row["shadow_selection_score"],
        ),
        reverse=True,
    )
    assert rows[0]["strategy"] == "trend"
    assert rows[0]["shadow_selection_bonus"] > 0
    assert rows[0]["score"] == 0.0048
    assert account == saved


def _candle(timestamp):
    return SimpleNamespace(
        timestamp=timestamp, open=100.0, high=100.0,
        low=100.0, close=100.0, volume=10.0,
    )


def test_manager_records_shadow_reason_for_reordered_pending(tmp_path, monkeypatch):
    manager = ai.AIPaperManager(tmp_path / "ai_paper.json", assets=[])
    manager.state.update(
        initial_balance=1000.0,
        funded_capital=1000.0,
        balance=1000.0,
        equity=1000.0,
        peak=1000.0,
    )
    manager.state["shadow"] = make_shadow(strategy="trend")

    def fake_rank(symbol, bars):
        strategy = "trend" if symbol == "BBBUSDT" else "breakout"
        return [{
            **candidate(
                strategy=strategy,
                symbol=symbol,
                score=0.0048 if strategy == "trend" else 0.0051,
            ),
            "expected_net_return": 0.006,
            "neighbor_spread": 0.002,
            "validation_trades": 6,
            "validation_mean": 0.003,
            "validated": True,
            "exploratory": False,
        }]

    monkeypatch.setattr(ai, "rank_asset", fake_rank)
    bars = [_candle(T0 - ai.MINUTE), _candle(T0)]
    state = manager.step(
        {"AAAUSDT": bars, "BBBUSDT": bars},
        now_ms=T0 + ai.MINUTE + 1_000,
    )
    assert state["pending"][0]["symbol"] == "BBBUSDT"
    assert state["pending"][0]["shadow_selection_bonus"] > 0
    assert state["pending"][0]["score"] == 0.0048
    assert state["trades"] == []
    assert state["positions"] == {}
    assert state["balance"] == 1000.0
    assert state["shadow_advisor"]["trend|LONG"]["status"] == (
        "SHADOW_CONFIRMED_FOR_RANKING"
    )
