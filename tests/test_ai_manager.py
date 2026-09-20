import json
from types import SimpleNamespace

from src.agent.ai_manager import (
    AIPaperManager,
    CONTROLLED_LEARNING_EXPOSURE,
    EXPLORATION_POSITION_EXPOSURE,
    MAX_EXPLORATORY_POSITIONS,
    MAX_DAILY_LOSS_PCT,
    MIN_MODEL_EDGE,
    MIN_VALIDATION_TRADES,
    STRATEGIES,
)


def test_ai_manager_initializes_zero_pln_multi_position_account(tmp_path):
    path = tmp_path / "ai_paper.json"

    manager = AIPaperManager(path, assets=[])

    assert manager.state["version"] == 3
    assert manager.state["mode"] == "PAPER_ONLY"
    assert manager.state["unit"] == "PLN"
    assert manager.state["initial_balance"] == 0.0
    assert manager.state["balance"] == 0.0
    assert manager.state["equity"] == 0.0
    assert manager.state["positions"] == {}
    assert manager.state["pending"] == []
    assert manager.state["funding_received"] == 0.0
    assert set(manager.state["strategy_learning"]) == set(STRATEGIES)


def test_ai_manager_waits_for_confirmed_funding(tmp_path):
    path = tmp_path / "ai_paper.json"
    manager = AIPaperManager(path, assets=[])

    state = manager.step({}, now_ms=1_800_000_000_000)

    assert state["balance"] == 0.0
    assert state["equity"] == 0.0
    assert state["positions"] == {}
    assert state["pending"] == []
    assert state["decision"]["action"] == "WAIT_FUNDS"
    assert state["trades"] == []
    assert path.exists()


def test_ai_manager_applies_funding_event_once(tmp_path):
    path = tmp_path / "ai_paper.json"
    control = tmp_path / "ai_control.json"
    control.write_text(
        json.dumps(
            {
                "version": 1,
                "paper_only": True,
                "funding_events": [
                    {
                        "id": "fund-1",
                        "amount": 2500.0,
                        "currency": "PLN",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    manager = AIPaperManager(path, assets=[], control_path=control)
    state = manager.step({}, now_ms=1_800_000_000_000)

    assert state["balance"] == 2500.0
    assert state["equity"] == 2500.0
    assert state["initial_balance"] == 2500.0
    assert state["funding_received"] == 2500.0
    assert state["decision"]["action"] == "CASH"

    state = manager.step({}, now_ms=1_800_000_060_000)
    assert state["balance"] == 2500.0
    assert state["initial_balance"] == 2500.0
    assert state["funding_received"] == 2500.0


def test_ai_manager_run_once_with_no_assets_does_not_touch_network(tmp_path, monkeypatch):
    path = tmp_path / "ai_paper.json"
    manager = AIPaperManager(path, assets=[])

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Network/data provider must not be called")

    monkeypatch.setattr(
        "src.agent.ai_manager.DataProvider.get_candles",
        fail_if_called,
    )

    state = manager.run_once()

    assert state["mode"] == "PAPER_ONLY"
    assert state["positions"] == {}
    assert state["decision"]["action"] == "WAIT_FUNDS"


def test_ai_manager_migrates_v2_pln_state_and_keeps_funds(tmp_path):
    path = tmp_path / "ai_paper.json"
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "mode": "PAPER_ONLY",
                "unit": "PLN",
                "initial_balance": 3000.0,
                "funded_capital": 3000.0,
                "balance": 2500.0,
                "equity": 2510.0,
                "peak": 3030.0,
                "realized_pnl": -490.0,
                "unrealized_pnl": 10.0,
                "position": {
                    "symbol": "ETHUSDT",
                    "side": "LONG",
                    "strategy": "trend",
                    "entry": 2500.0,
                    "allocation_pln": 500.0,
                    "unrealized_pnl": 10.0,
                },
                "pending": None,
                "trades": [],
                "decisions": [],
                "strategy_learning": {},
                "applied_control_ids": ["fund-1"],
                "funding_received": 3000.0,
                "last_cycle": 123,
            }
        ),
        encoding="utf-8",
    )

    manager = AIPaperManager(path, assets=[])

    assert manager.state["version"] == 3
    assert manager.state["unit"] == "PLN"
    assert manager.state["balance"] == 2000.0
    assert manager.state["positions"]["ETHUSDT"]["side"] == "LONG"
    assert manager.state["positions"]["ETHUSDT"]["unrealized_pnl"] == 10.0
    assert manager.state["equity"] == 2510.0
    assert manager.state["funding_received"] == 3000.0


def test_ai_manager_resets_old_simulation_units_to_zero_pln(tmp_path):
    path = tmp_path / "ai_paper.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "PAPER_ONLY",
                "unit": "simulation_units",
                "balance": 995.0,
                "equity": 995.0,
            }
        ),
        encoding="utf-8",
    )

    manager = AIPaperManager(path, assets=[])

    assert manager.state["version"] == 3
    assert manager.state["unit"] == "PLN"
    assert manager.state["balance"] == 0.0
    assert manager.state["equity"] == 0.0


def test_ai_manager_real_money_state_is_never_reused(tmp_path):
    path = tmp_path / "ai_paper.json"
    path.write_text(
        json.dumps(
            {
                "version": 99,
                "mode": "REAL_MONEY",
                "unit": "PLN",
                "balance": 999999.0,
            }
        ),
        encoding="utf-8",
    )

    manager = AIPaperManager(path, assets=[])

    assert manager.state["mode"] == "PAPER_ONLY"
    assert manager.state["version"] == 3
    assert manager.state["balance"] == 0.0


def test_ai_manager_sweeps_only_realized_surplus(tmp_path):
    path = tmp_path / "ai_paper.json"
    manager = AIPaperManager(path, assets=[])

    s = manager.state
    s["funded_capital"] = 1000.0
    s["initial_balance"] = 1000.0
    s["balance"] = 1100.0
    s["equity"] = 1100.0
    s["peak"] = 1100.0

    event = manager._sweep_realized_profit(1_800_000_000_000)

    assert event is not None
    assert event["amount"] == 100.0
    assert s["balance"] == 1000.0
    assert s["equity"] == 1000.0
    assert s["profit_swept"] == 100.0
    assert len(s["profit_transfers"]) == 1


def test_ai_manager_does_not_sweep_when_account_is_below_funded_capital(tmp_path):
    path = tmp_path / "ai_paper.json"
    manager = AIPaperManager(path, assets=[])

    s = manager.state
    s["funded_capital"] = 1000.0
    s["initial_balance"] = 1000.0
    s["balance"] = 900.0
    s["equity"] = 900.0
    s["peak"] = 1000.0

    event = manager._sweep_realized_profit(1_800_000_000_000)

    assert event is None
    assert s["balance"] == 900.0
    assert s["equity"] == 900.0
    assert s["profit_swept"] == 0.0


def test_ai_manager_does_not_sweep_unrealized_profit(tmp_path):
    path = tmp_path / "ai_paper.json"
    manager = AIPaperManager(path, assets=[])

    s = manager.state
    s["funded_capital"] = 1000.0
    s["initial_balance"] = 1000.0
    s["balance"] = 900.0
    s["positions"] = {
        "ETHUSDT": {
            "symbol": "ETHUSDT",
            "strategy": "trend",
            "side": "LONG",
            "entry": 2500.0,
            "allocation_pln": 100.0,
            "unrealized_pnl": 50.0,
        }
    }
    manager._mark_equity()

    assert s["equity"] == 1050.0

    event = manager._sweep_realized_profit(1_800_000_000_000)

    assert event is None
    assert s["balance"] == 900.0
    assert s["equity"] == 1050.0



def _candle(ts, close=100.0):
    return SimpleNamespace(
        timestamp=ts,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1.0,
    )


def _fund_manager(manager, amount=1000.0):
    manager.state["funded_capital"] = amount
    manager.state["initial_balance"] = amount
    manager.state["balance"] = amount
    manager.state["equity"] = amount
    manager.state["peak"] = amount


def test_pending_waits_for_a_new_closed_candle_before_confirmation(tmp_path):
    manager = AIPaperManager(tmp_path / "ai_paper.json", assets=[])
    _fund_manager(manager)

    manager.state["pending"] = [
        {
            "symbol": "TESTUSDT",
            "strategy": "trend",
            "side": "LONG",
            "timestamp": 60_000,
            "signal_timestamp": 60_000,
            "score": 0.01,
        }
    ]

    result = manager._execute_pending(
        {"TESTUSDT": [_candle(60_000, 101.0)]},
        {"TESTUSDT": [_candle(60_000, 101.0)]},
        [
            {
                "symbol": "TESTUSDT",
                "strategy": "trend",
                "side": "LONG",
                "eligible": True,
                "score": 0.02,
                "exploratory": False,
            }
        ],
        90_000,
    )

    assert result["opened"] == []
    assert result["cancelled"] == []
    assert len(manager.state["pending"]) == 1
    assert manager.state["positions"] == {}


def test_pending_signal_is_cancelled_when_not_reconfirmed(tmp_path):
    manager = AIPaperManager(tmp_path / "ai_paper.json", assets=[])
    _fund_manager(manager)

    manager.state["pending"] = [
        {
            "symbol": "TESTUSDT",
            "strategy": "trend",
            "side": "LONG",
            "timestamp": 60_000,
            "signal_timestamp": 60_000,
            "score": 0.01,
        }
    ]

    result = manager._execute_pending(
        {"TESTUSDT": [_candle(120_000, 102.0)]},
        {"TESTUSDT": [_candle(120_000, 102.0)]},
        [],
        150_000,
    )

    assert result["opened"] == []
    assert len(result["cancelled"]) == 1
    assert result["cancelled"][0]["cancel_reason"] == "SIGNAL_NOT_CONFIRMED"
    assert manager.state["pending"] == []
    assert manager.state["positions"] == {}


def test_pending_signal_opens_only_after_reconfirmation(tmp_path):
    manager = AIPaperManager(tmp_path / "ai_paper.json", assets=[])
    _fund_manager(manager)

    manager.state["pending"] = [
        {
            "symbol": "TESTUSDT",
            "strategy": "trend",
            "side": "LONG",
            "timestamp": 60_000,
            "signal_timestamp": 60_000,
            "score": 0.01,
        }
    ]

    result = manager._execute_pending(
        {"TESTUSDT": [_candle(120_000, 103.0), _candle(150_000, 104.0)]},
        {"TESTUSDT": [_candle(120_000, 103.0)]},
        [
            {
                "symbol": "TESTUSDT",
                "strategy": "trend",
                "side": "LONG",
                "eligible": True,
                "score": 0.025,
                "exploratory": False,
            }
        ],
        150_000,
    )

    assert result["opened"] == ["TESTUSDT"]
    assert result["cancelled"] == []
    assert manager.state["pending"] == []

    position = manager.state["positions"]["TESTUSDT"]
    assert position["entry"] == 104.0
    assert position["selected_score"] == 0.01
    assert position["score"] == 0.025
    assert position["confirmed_timestamp"] == 120_000
    assert position["allocation_pln"] == 150.0



def test_guardrails_require_stronger_validation():
    assert MIN_VALIDATION_TRADES >= 4
    assert MIN_MODEL_EDGE >= 0.001
    assert EXPLORATION_POSITION_EXPOSURE < 0.15
    assert MAX_EXPLORATORY_POSITIONS == 1


def test_live_learning_can_reject_previously_eligible_signal(tmp_path):
    manager = AIPaperManager(tmp_path / "ai_paper.json", assets=[])
    manager.state["strategy_learning"]["trend"] = {
        "trades": 4,
        "wins": 1,
        "total_return": -0.04,
    }

    row = {
        "symbol": "TESTUSDT",
        "strategy": "trend",
        "side": "LONG",
        "eligible": True,
        "score": 0.0020,
    }

    manager._apply_live_learning(row)

    assert row["learning_bonus"] < 0
    assert row["score"] < MIN_MODEL_EDGE
    assert row["eligible"] is False
    assert row["eligibility_reason"] == "LIVE_LEARNING_EDGE_REJECTED"


def test_exploratory_entry_uses_smaller_position(tmp_path):
    manager = AIPaperManager(tmp_path / "ai_paper.json", assets=[])
    _fund_manager(manager)

    manager.state["pending"] = [
        {
            "symbol": "TESTUSDT",
            "strategy": "trend",
            "side": "LONG",
            "timestamp": 60_000,
            "signal_timestamp": 60_000,
            "score": 0.01,
            "exploratory": True,
        }
    ]

    result = manager._execute_pending(
        {"TESTUSDT": [_candle(120_000, 103.0), _candle(150_000, 104.0)]},
        {"TESTUSDT": [_candle(120_000, 103.0)]},
        [
            {
                "symbol": "TESTUSDT",
                "strategy": "trend",
                "side": "LONG",
                "eligible": True,
                "score": 0.025,
                "exploratory": True,
            }
        ],
        150_000,
    )

    assert result["opened"] == ["TESTUSDT"]
    assert manager.state["positions"]["TESTUSDT"]["allocation_pln"] == 50.0


def test_only_one_exploratory_candidate_can_be_pending(tmp_path):
    manager = AIPaperManager(tmp_path / "ai_paper.json", assets=[])
    _fund_manager(manager)

    rows = [
        {
            "symbol": "AAAUSDT",
            "strategy": "trend",
            "side": "LONG",
            "eligible": True,
            "score": 0.01,
            "exploratory": True,
        },
        {
            "symbol": "BBBUSDT",
            "strategy": "breakout",
            "side": "SHORT",
            "eligible": True,
            "score": 0.009,
            "exploratory": True,
        },
    ]
    fresh = {
        "AAAUSDT": [_candle(60_000, 100.0)],
        "BBBUSDT": [_candle(60_000, 100.0)],
    }

    selected = manager._select_new_pending(rows, fresh, 90_000)

    assert len(selected) == 1
    assert selected[0]["symbol"] == "AAAUSDT"
    assert selected[0]["exploratory"] is True



def test_v2_migration_does_not_double_count_open_position_principal(tmp_path):
    path = tmp_path / "ai_paper.json"
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "mode": "PAPER_ONLY",
                "unit": "PLN",
                "initial_balance": 1000.0,
                "funded_capital": 1000.0,
                "balance": 990.0,
                "equity": 995.0,
                "peak": 1010.0,
                "daily_loss": 10.0,
                "day": "2026-09-20",
                "realized_pnl": -10.0,
                "unrealized_pnl": 5.0,
                "position": {
                    "symbol": "TESTUSDT",
                    "side": "LONG",
                    "strategy": "trend",
                    "entry": 100.0,
                    "allocation_pln": 250.0,
                    "last_timestamp": 60_000,
                    "exit_at": 900_000,
                },
                "pending": None,
                "decisions": [],
                "trades": [],
                "last_cycle": 60_000,
                "applied_control_ids": ["fund-1"],
                "funding_received": 1000.0,
                "strategy_learning": {},
            }
        ),
        encoding="utf-8",
    )

    manager = AIPaperManager(path, assets=[])

    assert manager.state["balance"] == 740.0
    assert manager.state["positions"]["TESTUSDT"]["allocation_pln"] == 250.0
    assert manager.state["positions"]["TESTUSDT"]["unrealized_pnl"] == 5.0

    manager._mark_equity()

    assert manager.state["equity"] == 995.0
    assert abs(manager.state["accounting_gap"]) < 0.000001
    assert manager.state["accounting_error"] is False


def test_accounting_gap_guard_blocks_corrupted_state(tmp_path):
    manager = AIPaperManager(tmp_path / "ai_paper.json", assets=[])
    _fund_manager(manager)

    manager.state["balance"] = 1250.0
    manager.state["equity"] = 1250.0

    assert manager._blocked() is True
    assert manager.state["accounting_error"] is True
    assert round(manager.state["accounting_gap"], 6) == 250.0


def test_daily_loss_limit_is_ten_percent_of_funded_capital(tmp_path):
    manager = AIPaperManager(tmp_path / "ai_paper.json", assets=[])
    _fund_manager(manager, 1000.0)

    assert MAX_DAILY_LOSS_PCT == 0.10
    assert manager._daily_loss_limit() == 100.0


def test_daily_loss_uses_net_realized_pnl_and_wins_offset_losses(tmp_path):
    manager = AIPaperManager(tmp_path / "ai_paper.json", assets=[])
    _fund_manager(manager, 1000.0)

    manager._apply_daily_realized_result(-60.0)
    assert manager.state["daily_realized_pnl"] == -60.0
    assert manager.state["daily_loss"] == 60.0

    manager._apply_daily_realized_result(25.0)
    assert manager.state["daily_realized_pnl"] == -35.0
    assert manager.state["daily_loss"] == 35.0

    manager._apply_daily_realized_result(40.0)
    assert manager.state["daily_realized_pnl"] == 5.0
    assert manager.state["daily_loss"] == 0.0
    assert manager._blocked() is False


def test_loaded_state_rebuilds_current_day_loss_from_net_trade_history(tmp_path):
    path = tmp_path / "ai_paper.json"
    day = "2026-09-20"
    timestamp = 1_789_920_000_000

    path.write_text(
        json.dumps(
            {
                "version": 3,
                "mode": "PAPER_ONLY",
                "unit": "PLN",
                "initial_balance": 1000.0,
                "funded_capital": 1000.0,
                "balance": 975.0,
                "equity": 975.0,
                "peak": 1000.0,
                "daily_loss": 65.0,
                "day": day,
                "realized_pnl": -25.0,
                "unrealized_pnl": 0.0,
                "positions": {},
                "pending": [],
                "decisions": [],
                "trades": [
                    {
                        "exit_timestamp": timestamp,
                        "profit": -50.0,
                    },
                    {
                        "exit_timestamp": timestamp + 60_000,
                        "profit": 25.0,
                    },
                ],
                "last_cycle": timestamp,
                "applied_control_ids": [],
                "funding_received": 1000.0,
                "profit_swept": 0.0,
                "profit_transfers": [],
                "accounting_gap": 0.0,
                "accounting_error": False,
                "market_marks": {},
                "strategy_supervisor": {},
                "strategy_learning": {},
            }
        ),
        encoding="utf-8",
    )

    manager = AIPaperManager(path, assets=[])

    # The old gross-loss counter (65 PLN) is replaced by same-day net PnL.
    assert manager.state["daily_realized_pnl"] == -25.0
    assert manager.state["daily_loss"] == 25.0


def test_controlled_learning_probe_accepts_positive_learning_signal(tmp_path):
    manager = AIPaperManager(tmp_path / "ai_paper.json", assets=[])

    row = {
        "symbol": "TESTUSDT",
        "strategy": "breakout",
        "side": "LONG",
        "eligible": False,
        "live_signal": True,
        "validated": False,
        "exploratory": False,
        "score": 0.0008,
        "expected_net_return": 0.0030,
        "neighbor_spread": 0.010,
        "validation_trades": 2,
        "validation_mean": 0.0002,
        "supervisor_status": "LEARNING",
    }
    supervisor = {
        "strategies": {
            "breakout": {
                "status": "LEARNING",
                "reason": "collecting live evidence",
            }
        }
    }

    manager._apply_controlled_learning_probe(row, supervisor)

    assert row["eligible"] is True
    assert row["exploratory"] is True
    assert row["learning_probe"] is True
    assert row["supervisor_exposure"] == CONTROLLED_LEARNING_EXPOSURE
    assert row["eligibility_reason"] == "CONTROLLED_LEARNING_PROBE"


def test_controlled_learning_probe_never_revives_negative_model_edge(tmp_path):
    manager = AIPaperManager(tmp_path / "ai_paper.json", assets=[])

    row = {
        "symbol": "TESTUSDT",
        "strategy": "breakout",
        "side": "LONG",
        "eligible": False,
        "live_signal": True,
        "validated": False,
        "exploratory": False,
        "score": -0.001,
        "expected_net_return": -0.002,
        "neighbor_spread": 0.010,
        "validation_trades": 4,
        "validation_mean": -0.001,
        "supervisor_status": "LEARNING",
    }

    manager._apply_controlled_learning_probe(
        row,
        {"strategies": {"breakout": {"status": "LEARNING"}}},
    )

    assert row["eligible"] is False
    assert row["learning_probe"] is False
    assert row["eligibility_reason"] == "MODEL_OR_VALIDATION_REJECTED"


def test_paused_strategy_needs_stronger_edge_for_learning_probe(tmp_path):
    manager = AIPaperManager(tmp_path / "ai_paper.json", assets=[])
    supervisor = {"strategies": {"trend": {"status": "PAUSED"}}}

    weak = {
        "symbol": "AAAUSDT",
        "strategy": "trend",
        "side": "LONG",
        "eligible": False,
        "live_signal": True,
        "validated": False,
        "exploratory": False,
        "score": 0.0010,
        "expected_net_return": 0.0025,
        "neighbor_spread": 0.010,
        "validation_trades": 3,
        "validation_mean": 0.0004,
        "supervisor_status": "PAUSED",
    }
    manager._apply_controlled_learning_probe(weak, supervisor)
    assert weak["eligible"] is False

    strong = dict(
        weak,
        symbol="BBBUSDT",
        score=0.0018,
        expected_net_return=0.0035,
        validation_mean=0.0007,
        eligibility_reason=None,
    )
    manager._apply_controlled_learning_probe(strong, supervisor)

    assert strong["eligible"] is True
    assert strong["learning_probe"] is True
    assert strong["supervisor_exposure"] == CONTROLLED_LEARNING_EXPOSURE


def test_controlled_learning_probe_uses_two_percent_position(tmp_path):
    manager = AIPaperManager(tmp_path / "ai_paper.json", assets=[])
    _fund_manager(manager)

    manager.state["pending"] = [
        {
            "symbol": "TESTUSDT",
            "strategy": "breakout",
            "side": "LONG",
            "timestamp": 60_000,
            "signal_timestamp": 60_000,
            "score": 0.001,
            "exploratory": True,
            "learning_probe": True,
        }
    ]

    result = manager._execute_pending(
        {"TESTUSDT": [_candle(120_000, 100.0), _candle(150_000, 101.0)]},
        {"TESTUSDT": [_candle(120_000, 100.0)]},
        [
            {
                "symbol": "TESTUSDT",
                "strategy": "breakout",
                "side": "LONG",
                "eligible": True,
                "score": 0.0012,
                "exploratory": True,
                "learning_probe": True,
                "supervisor_exposure": CONTROLLED_LEARNING_EXPOSURE,
            }
        ],
        150_000,
    )

    assert result["opened"] == ["TESTUSDT"]
    assert manager.state["positions"]["TESTUSDT"]["allocation_pln"] == 20.0
    assert manager.state["positions"]["TESTUSDT"]["learning_probe"] is True
