import json

import pytest

from src.agent.ai_manager import AIPaperManager, STRATEGIES


def test_ai_manager_initializes_isolated_paper_only_state(tmp_path):
    path = tmp_path / "ai_paper.json"

    manager = AIPaperManager(path, assets=[])

    assert manager.state["version"] == 1
    assert manager.state["mode"] == "PAPER_ONLY"
    assert manager.state["unit"] == "simulation_units"
    assert manager.state["initial_balance"] == 1000.0
    assert manager.state["balance"] == 1000.0
    assert manager.state["equity"] == 1000.0
    assert manager.state["position"] is None
    assert manager.state["profit_swept"] == 0.0
    assert manager.state["profit_transfers"] == []
    assert set(manager.state["strategy_learning"]) == set(STRATEGIES)


def test_ai_manager_empty_universe_stays_in_virtual_cash(tmp_path):
    path = tmp_path / "ai_paper.json"
    manager = AIPaperManager(path, assets=[])

    state = manager.step({}, now_ms=1_800_000_000_000)

    assert state["mode"] == "PAPER_ONLY"
    assert state["balance"] == 1000.0
    assert state["equity"] == 1000.0
    assert state["position"] is None
    assert state["pending"] is None
    assert state["decision"]["action"] == "CASH"
    assert state["trades"] == []
    assert path.exists()


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
    assert state["decision"]["action"] == "CASH"


def test_ai_manager_rejects_non_paper_state(tmp_path):
    path = tmp_path / "ai_paper.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "mode": "REAL_MONEY",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported AI paper state"):
        AIPaperManager(path, assets=[])
