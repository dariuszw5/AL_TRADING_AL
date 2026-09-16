import json
import math

import pytest
from pytest import approx

from src.agent import ai_manager as ai
from src.data.candle import Candle


def candles(count=600, step=0.0003, start=1_700_000_040_000):
    result = []
    price = 100.0
    for i in range(count):
        value = price * (1 + step + math.sin(i / 9) * abs(step) * 0.2)
        result.append(Candle(start+i*ai.MINUTE, price, max(price, value)*1.0001,
                             min(price, value)*0.9999, value, 10))
        price = value
    return result


def manager(tmp_path):
    return ai.AIPaperManager(tmp_path / 'ai.json', assets=[])


def now(bars):
    return bars[-1].timestamp + ai.MINUTE


def test_filters_forming_candle_and_rejects_malformed_data():
    bars = candles()
    assert len(ai.clean_candles(bars, now(bars)-1)) == 599
    bars[-1].close = float('nan')
    with pytest.raises(ValueError):
        ai.clean_candles(bars, now(bars))


def test_model_learns_local_returns():
    model = ai.NearestReturnModel([((0.,), -0.02), ((1.,), 0.04)], k=1)
    assert model.predict((0.1,))[0] == -0.02
    assert model.predict((0.9,))[0] == 0.04


def test_temporal_validation_has_no_training_label_leak():
    rows = ai.rank_asset('BTCUSDT', candles())
    assert len(rows) == 3
    assert all(r['train_label_end'] < r['validation_start'] for r in rows)
    assert rows[0]['validation_trades'] >= 5
    assert rows[0]['eligible']


def test_falling_and_flat_markets_cannot_pass_after_costs():
    for step in (0, -0.0003):
        assert not any(r['eligible'] for r in ai.rank_asset('BTCUSDT', candles(step=step)))


def test_future_changes_do_not_change_past_features():
    bars = candles()
    before = ai.features(bars, 100)
    bars[101].close *= 3
    assert before == ai.features(bars, 100)


def test_closed_market_is_excluded_and_cash_preserved(tmp_path):
    m = manager(tmp_path)
    bars = candles()
    state = m.step({'AAPL': bars}, now(bars)+10*ai.MINUTE)
    assert state['decision']['action'] == 'CASH'
    assert state['balance'] == 1000
    assert 'AAPL' in state['data_issues']


def test_signal_executes_next_open_once_and_restores(tmp_path):
    m = manager(tmp_path)
    bars = candles(620)
    state = m.step({'BTCUSDT': bars[:600]}, now(bars[:600]))
    assert state['pending']['symbol'] == 'BTCUSDT'
    assert state['position'] is None
    state = m.step({'BTCUSDT': bars[:601]}, now(bars[:601]))
    assert state['position']['entry'] == bars[600].open
    assert state['position']['allocation'] == 200
    restored = manager(tmp_path)
    assert restored.state['position'] == state['position']
    assert restored.step({'BTCUSDT': bars[:601]}, now(bars[:601])) == state
    state = restored.step({'BTCUSDT': bars[:610]}, now(bars[:610]))
    assert len(state['trades']) == 1
    assert state['trades'][0]['reason'] == 'TIME_EXIT'
    assert state['balance'] == 1000
    assert state['profit_swept'] > 0
    learning = state['strategy_learning']['trend']
    assert learning['trades'] == 1
    assert learning['total_return'] > 0


def test_online_learning_is_bounded_and_exposed_in_ranking(tmp_path, monkeypatch):
    m = manager(tmp_path)
    m.state['strategy_learning']['trend'] = {
        'trades': 3, 'wins': 3, 'total_return': 0.30,
    }
    monkeypatch.setattr(ai, 'rank_asset', lambda symbol, bars: [dict(
        symbol=symbol, strategy='trend', score=0.01, eligible=True)])
    bars = candles()
    state = m.step({'BTCUSDT': bars}, now(bars))
    row = state['ranking'][0]
    assert row['learning_trades'] == 3
    assert row['learning_mean_return'] == approx(0.10)
    assert row['learning_bonus'] == approx(ai.LEARNING_WEIGHT * 0.10)
    assert row['score'] == approx(0.01 + ai.LEARNING_WEIGHT * 0.10)


def test_realized_surplus_is_transferred_to_user_ledger(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    m = manager(tmp_path / 'ai.json')
    m.state['balance'] = 1012.5
    m.state['equity'] = 1012.5
    state = m.step({}, now(candles()))
    user = ai.LiveStateStore('data/live_state/user_portfolio.json').load()
    assert state['balance'] == 1000
    assert state['profit_swept'] == approx(12.5)
    assert user['profit_transferred'] == approx(12.5)
    assert user['balance'] == approx(12.5)


def test_stop_gap_and_costs_are_charged(tmp_path):
    m = manager(tmp_path)
    bars = candles(602)
    m.step({'BTCUSDT': bars[:600]}, now(bars[:600]))
    m.step({'BTCUSDT': bars[:601]}, now(bars[:601]))
    entry = bars[600].open
    bars[601] = Candle(bars[601].timestamp, entry*.9, entry*.91, entry*.89, entry*.9, 10)
    state = m.step({'BTCUSDT': bars}, now(bars))
    assert state['trades'][0]['reason'] == 'STOP_GAP'
    assert state['trades'][0]['profit'] < -20
    assert state['decision']['action'] == 'HALT'
    assert state['pending'] is None


def test_no_new_allocation_when_open_market_is_unavailable(tmp_path):
    m = manager(tmp_path)
    bars = candles(601)
    m.step({'BTCUSDT': bars[:600]}, now(bars[:600]))
    m.step({'BTCUSDT': bars}, now(bars))
    state = m.step({'ETHUSDT': bars}, now(bars)+ai.MINUTE, {'BTCUSDT': 'timeout'})
    assert state['position']['symbol'] == 'BTCUSDT'
    assert state['pending'] is None
    assert 'BTCUSDT' in state['data_issues']


def test_selects_best_asset_and_can_switch_after_exit(tmp_path, monkeypatch):
    def ranking(symbol, bars):
        score = 0.03 if symbol == 'ETHUSDT' else 0.01
        return [dict(symbol=symbol, strategy='trend', score=score, eligible=True)]
    monkeypatch.setattr(ai, 'rank_asset', ranking)
    m = manager(tmp_path)
    bars = candles(610)
    state = m.step({'BTCUSDT': bars[:600], 'ETHUSDT': bars[:600]}, now(bars[:600]))
    assert state['pending']['symbol'] == 'ETHUSDT'
    m.step({'BTCUSDT': bars[:601], 'ETHUSDT': bars[:601]}, now(bars[:601]))
    monkeypatch.setattr(ai, 'rank_asset', lambda s, b: [dict(
        symbol=s, strategy='breakout', score=0.03, eligible=s == 'BTCUSDT')])
    state = m.step({'BTCUSDT': bars, 'ETHUSDT': bars}, now(bars))
    assert state['trades'][0]['symbol'] == 'ETHUSDT'
    assert state['pending']['symbol'] == 'BTCUSDT'
    assert state['pending']['strategy'] == 'breakout'


def test_drawdown_halt_survives_restart_and_day_change(tmp_path):
    m = manager(tmp_path)
    m.state.update(equity=940, balance=940)
    state = m.step({}, 1_700_000_000_000)
    assert state['halted']
    restored = manager(tmp_path)
    state = restored.step({}, 1_700_000_000_000+86_400_000)
    assert state['decision']['action'] == 'HALT'


def test_api_reads_only_separate_ai_state(tmp_path, monkeypatch):
    from app.backend import main
    monkeypatch.setattr(main, 'LIVE_STATE_DIR', tmp_path)
    assert main.ai_status()['available'] is False
    (tmp_path/'ai_paper.json').write_text(json.dumps(
        dict(mode='PAPER_ONLY', last_cycle=1, equity=1000)), encoding='utf-8')
    result = main.ai_status()
    assert result['available'] and result['stale']
    assert result['equity'] == 1000


def test_decision_never_fills_before_it_was_made(tmp_path):
    m = manager(tmp_path)
    bars = candles(601)
    state = m.step({'BTCUSDT': bars[:600]}, now(bars[:600])+5000)
    assert state['pending']['entry_at'] > now(bars[:600])+5000
    state = m.step({'BTCUSDT': bars}, now(bars))
    assert state['position'] is None


def test_save_failure_rolls_back_in_memory_account(tmp_path, monkeypatch):
    m = manager(tmp_path)
    original = ai.deepcopy(m.state)
    def fail(_):
        raise OSError('disk full')
    monkeypatch.setattr(m.store, 'save', fail)
    with pytest.raises(OSError):
        m.step({'BTCUSDT': candles()}, now(candles()))
    assert m.state == original


def test_provider_failure_is_reported_without_stopping_other_markets(tmp_path, monkeypatch):
    from src.data.assets import SUPPORTED_ASSETS
    bars = candles()
    def fetch(_, symbol, interval, limit):
        if symbol == 'ETHUSDT':
            raise TimeoutError('provider timeout')
        return bars
    monkeypatch.setattr(ai.DataProvider, 'get_candles', fetch)
    monkeypatch.setattr(ai, 'time', lambda: now(bars)/1000)
    m = ai.AIPaperManager(tmp_path/'ai.json', assets=SUPPORTED_ASSETS[:2])
    state = m.run_once()
    assert 'ETHUSDT' in state['data_issues']
    assert state['pending']['symbol'] == 'BTCUSDT'


def test_current_feature_window_cannot_cross_market_gap():
    bars = candles()
    for bar in bars[-10:]:
        bar.timestamp += ai.MINUTE
    assert ai.rank_asset('BTCUSDT', bars) == []


def test_stopped_position_does_not_mark_later_candle_recovery_as_profit(tmp_path):
    m = manager(tmp_path)
    bars = candles(602)
    m.step({'BTCUSDT': bars[:600]}, now(bars[:600]))
    m.step({'BTCUSDT': bars[:601]}, now(bars[:601]))
    previous_peak = m.state['peak']
    entry = bars[600].open
    bars[601] = Candle(bars[601].timestamp, entry, entry*1.5,
                       entry*.98, entry*1.4, 10)
    state = m.step({'BTCUSDT': bars}, now(bars))
    assert state['trades'][0]['reason'] == 'STOP_LOSS'
    assert state['trades'][0]['profit'] < 0
    assert state['peak'] == previous_peak
    assert not state.get('halted', False)
