from src.agent.shadow_research import ShadowResearchRunner
from src.data.assets import SUPPORTED_ASSETS
from src.data.candle import Candle


def test_candidate_ranking_returns_top_ten_in_deterministic_order():
    assets = {
        f'A{index}': {'best': {'confidence_score': index / 100, 'strategy': 'trend'}}
        for index in range(15)
    }
    top = ShadowResearchRunner.rank_candidates(assets)
    assert len(top) == 10
    assert top[0]['symbol'] == 'A14'
    assert top[-1]['symbol'] == 'A5'


def test_shadow_research_never_enables_execution_and_persists(tmp_path, monkeypatch):
    monkeypatch.setattr('src.agent.shadow_research.fetch_pln_rates',
                        lambda currencies: {'rates': {'USDT': 4}, 'received_at': 0})
    bars = [Candle(i * 60_000, 100.0, 101.0, 99.0, 100.5, 10.0)
            for i in range(520)]
    assets = SUPPORTED_ASSETS[:3]
    runner = ShadowResearchRunner(tmp_path / "research.json", assets)
    monkeypatch.setattr(runner.geo_feed, 'fetch',
                        lambda: {'events': [], 'source': 'test', 'issue': None})
    monkeypatch.setattr(
        runner, "_fetch", lambda asset: (asset, bars), raising=False)
    monkeypatch.setattr(
        "src.agent.shadow_research.rank_asset",
        lambda symbol, candles: [{
            "symbol": symbol, "strategy": "trend", "eligible": True,
            "score": 0.01, "confidence_score": .60,
            "confidence_eligible": True, "current_signal": True,
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
    assert state['geopolitical_research']['mode'] == 'RESEARCH_ONLY'
    assert (tmp_path / "research.json").exists()
