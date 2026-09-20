import json

from src.agent.ai_manager import AIPaperManager, STRATEGIES


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
    assert manager.state["balance"] == 2500.0
    assert manager.state["positions"]["ETHUSDT"]["side"] == "LONG"
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
