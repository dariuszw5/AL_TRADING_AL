from src.agent.strategy_supervisor import (
    PROBATION_EXPOSURE,
    build_strategy_supervisor,
    supervise_candidate,
)


def _trade(
    strategy,
    value,
    *,
    side="LONG",
    reason="TIME_EXIT",
):
    return {
        "strategy": strategy,
        "side": side,
        "return_fraction": value,
        "reason": reason,
    }


def test_strategy_supervisor_learns_before_enough_live_trades():
    trades = [
        _trade("breakout", 0.01),
        _trade("breakout", -0.005),
        _trade("breakout", 0.004),
    ]

    report = build_strategy_supervisor(
        trades,
        ("trend", "mean_reversion", "breakout"),
    )

    assert report["strategies"]["breakout"]["status"] == "LEARNING"


def test_strategy_supervisor_pauses_persistently_bad_strategy():
    trades = [
        _trade("trend", -0.01, reason="STOP_LOSS"),
        _trade("trend", -0.008, reason="STOP_LOSS"),
        _trade("trend", 0.003),
        _trade("trend", -0.007, reason="STOP_LOSS"),
        _trade("trend", -0.006, reason="STOP_LOSS"),
        _trade("trend", 0.002),
    ]

    report = build_strategy_supervisor(trades, ("trend",))

    health = report["strategies"]["trend"]
    assert health["status"] == "PAUSED"
    assert health["mean_return"] < 0
    assert health["profit_factor"] < 0.75


def test_strategy_supervisor_keeps_positive_strategy_active():
    trades = [
        _trade("breakout", 0.012),
        _trade("breakout", -0.004),
        _trade("breakout", 0.010),
        _trade("breakout", -0.003),
        _trade("breakout", 0.008),
        _trade("breakout", 0.005),
    ]

    report = build_strategy_supervisor(trades, ("breakout",))

    assert report["strategies"]["breakout"]["status"] == "ACTIVE"


def test_paused_strategy_blocks_ordinary_candidate():
    report = {
        "strategies": {
            "trend": {
                "status": "PAUSED",
                "reason": "bad live performance",
            }
        }
    }
    row = {
        "strategy": "trend",
        "eligible": True,
        "validated": True,
        "validation_trades": 4,
        "validation_mean": 0.001,
        "score": 0.0015,
        "exploratory": False,
    }

    supervise_candidate(row, report)

    assert row["eligible"] is False
    assert row["eligibility_reason"] == "STRATEGY_SUPERVISOR_PAUSED"


def test_paused_strategy_can_return_only_as_strong_probation():
    report = {
        "strategies": {
            "trend": {
                "status": "PAUSED",
                "reason": "bad live performance",
            }
        }
    }
    row = {
        "strategy": "trend",
        "eligible": True,
        "validated": True,
        "validation_trades": 8,
        "validation_mean": 0.002,
        "score": 0.004,
        "exploratory": False,
    }

    supervise_candidate(row, report)

    assert row["eligible"] is True
    assert row["supervisor_probation"] is True
    assert row["supervisor_exposure"] == PROBATION_EXPOSURE
    assert row["eligibility_reason"] == "STRATEGY_SUPERVISOR_PROBATION"


def test_watch_strategy_rejects_exploration():
    report = {
        "strategies": {
            "mean_reversion": {
                "status": "WATCH",
                "reason": "weak live edge",
            }
        }
    }
    row = {
        "strategy": "mean_reversion",
        "eligible": True,
        "validated": False,
        "validation_trades": 2,
        "validation_mean": 0.0,
        "score": 0.003,
        "exploratory": True,
    }

    supervise_candidate(row, report)

    assert row["eligible"] is False
    assert (
        row["eligibility_reason"]
        == "STRATEGY_SUPERVISOR_WATCH_NO_EXPLORATION"
    )
