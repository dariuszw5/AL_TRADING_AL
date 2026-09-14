from src.agent.independent_paper import IndependentPaperPortfolios, dashboard_state
from src.data.assets import SUPPORTED_ASSETS
from tests.test_ai_manager import candles, now


def test_accounts_open_independently_and_restore(tmp_path):
    assets = SUPPORTED_ASSETS[:2]
    runner = IndependentPaperPortfolios(tmp_path, assets)
    bars = candles(620)
    for symbol, manager in runner.managers.items():
        manager.step({symbol: bars[:600]}, now(bars[:600]))
        manager.step({symbol: bars[:601]}, now(bars[:601]))
        assert manager.state['position']['symbol'] == symbol
    first, second = runner.managers.values()
    first.state['balance'] = 900
    assert second.state['balance'] == 1000
    restored = IndependentPaperPortfolios(tmp_path, assets)
    for symbol, manager in restored.managers.items():
        assert manager.state['position']['symbol'] == symbol
        manager.step({symbol: bars}, now(bars))
        data = dashboard_state(manager.state)
        assert data['trade_manager_history']
        assert len(data['equity_curve']) >= 3
        assert data['source'] == 'INDEPENDENT_AI_PAPER'


def test_one_failure_does_not_stop_other_markets(tmp_path, monkeypatch):
    runner = IndependentPaperPortfolios(tmp_path, SUPPORTED_ASSETS[:2])
    def fail():
        raise ValueError('provider unavailable')
    monkeypatch.setattr(runner.managers['BTCUSDT'], 'run_once', fail)
    monkeypatch.setattr(runner.managers['ETHUSDT'], 'run_once', lambda: {'decision': {'action': 'HOLD'}})
    result = runner.run_once()
    assert result['BTCUSDT']['action'] == 'ERROR'
    assert result['ETHUSDT']['action'] == 'HOLD'
