from src.agent.shadow_research import ShadowResearchRunner
from src.data.assets import SUPPORTED_ASSETS
from src.data.candle import Candle


def test_shadow_research_never_enables_execution_and_persists(tmp_path, monkeypatch):
    monkeypatch.setattr('src.agent.shadow_research.fetch_pln_rates',
                        lambda currencies: {'rates': {'USDT': 4}, 'received_at': 0})
    bars = [Candle(i * 60_000, 100.0, 101.0, 99.0, 100.5, 10.0)
            for i in range(520)]
    assets = SUPPORTED_ASSETS[:3]
    runner = ShadowResearchRunner(tmp_path / "research.json", assets)
    monkeypatch.setattr(
        runner, "_fetch", lambda asset: (asset, bars), raising=False)
    monkeypatch.setattr(
        "src.agent.shadow_research.rank_asset",
        lambda symbol, candles: [{
            "symbol": symbol, "strategy": "trend", "eligible": True,
            "score": 0.01, "current_signal": True,
        }],
    )

    state = runner.run_once()

    assert state["mode"] == "RESEARCH_ONLY"
    assert state["execution_enabled"] is False
    assert set(state["assets"]) == {asset.symbol for asset in assets}
    assert all(item["recommendation"] == "OBSERVE_SIGNAL"
               for item in state["assets"].values())
    assert not any("position" in item or "trade" in item
                   for item in state["assets"].values())
    assert (tmp_path / "research.json").exists()
