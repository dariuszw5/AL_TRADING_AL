import json

import pytest

from src.agent.ai_manager import AIPaperManager, STRATEGIES


def test_ai_manager_initializes_zero_pln_paper_account(tmp_path):
    path = tmp_path / "ai_paper.json"

    manager = AIPaperManager(path, assets=[])

    assert manager.state["version"] == 2
    assert manager.state["mode"] == "PAPER_ONLY"
    assert manager.state["unit"] == "PLN"
    assert manager.state["initial_balance"] == 0.0
    assert manager.state["balance"] == 0.0
    assert manager.state["equity"] == 0.0
    assert manager.state["position"] is None
    assert manager.state["funding_received"] == 0.0
    assert set(manager.state["strategy_learning"]) == set(STRATEGIES)


def test_ai_manager_waits_for_confirmed_funding(tmp_path):
    path = tmp_path / "ai_paper.json"
    manager = AIPaperManager(path, assets=[])

    state = manager.step({}, now_ms=1_800_000_000_000)

    assert state["mode"] == "PAPER_ONLY"
    assert state["balance"] == 0.0
    assert state["equity"] == 0.0
    assert state["position"] is None
    assert state["pending"] is None
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
    assert state["position"] is None
    assert state["decision"]["action"] == "WAIT_FUNDS"


def test_ai_manager_migrates_old_simulation_state_to_zero_pln(tmp_path):
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

    assert manager.state["version"] == 2
    assert manager.state["unit"] == "PLN"
    assert manager.state["balance"] == 0.0
    assert manager.state["equity"] == 0.0


def test_ai_manager_rejects_real_money_mode_only_by_resetting_to_paper(tmp_path):
    path = tmp_path / "ai_paper.json"
    path.write_text(
        json.dumps(
            {
                "version": 99,
                "mode": "REAL_MONEY",
            }
        ),
        encoding="utf-8",
    )

    manager = AIPaperManager(path, assets=[])

    assert manager.state["mode"] == "PAPER_ONLY"
    assert manager.state["unit"] == "PLN"
    assert manager.state["balance"] == 0.0
