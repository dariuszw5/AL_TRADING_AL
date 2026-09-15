import json
import pytest
from src.agent.pln_broker import PlnBroker, PlnLedger, initial_state
from src.data.candle import Candle
from src.data.fx_rates import fetch_pln_rates


def bar(t, low=100, high=100, close=100):
    return Candle(t, 100, high, low, close, 1)


def test_capital_reserved_and_no_leverage():
    state = initial_state()
    broker = PlnBroker(state)
    for i in range(40):
        broker.process(str(i), bar(60000), True, 4, 120000)
    broker.snapshot({str(i): (100, 4) for i in range(40)}, 120000)
    assert len(state['positions']) == 10
    assert state['free_cash'] == 0
    assert state['equity'] < 1000  # fees and spread


def test_profit_sweep_loss_topup_and_replay(tmp_path):
    ledger = PlnLedger(tmp_path)
    with ledger.transaction() as s:
        b = PlnBroker(s)
        b.process('A', bar(60000), True, 4, 120000)
        b.process('A', bar(120000, high=103), True, 4, 180000)
        profit = s['trades'][0]['profit']
        assert profit > 0
        assert s['balance'] == 1000
        assert s['user_portfolio']['balance'] == profit
    with ledger.transaction() as s:
        b = PlnBroker(s)
        b.process('A', bar(120000, high=103), True, 4, 180000)
        assert len(s['trades']) == 1
        assert len(s['transfers']) == 1
        b.process('A', bar(180000), True, 4, 240000)
        b.process('A', bar(240000, low=98), False, 4, 300000)
        assert s['balance'] == 1000
        assert s['user_portfolio']['balance'] < profit
        assert s['transfers'][-1]['direction'] == 'TO_TRADING'


def test_insufficient_reserve_pauses_new_positions():
    s = initial_state()
    b = PlnBroker(s)
    b.process('A', bar(60000), True, 4, 120000)
    b.process('A', bar(120000, low=98), False, 4, 180000)
    b.process('B', bar(180000), True, 4, 240000)
    assert s['shortfall'] > 0
    assert not s['positions']
    assert s['user_portfolio']['balance'] == 0


def test_fx_movement_counts_in_profit():
    s = initial_state()
    b = PlnBroker(s)
    b.process('A', bar(60000), True, 4, 120000)
    b.process('A', bar(120000, high=103), False, 3, 180000)
    assert s['trades'][0]['profit'] < 0  # instrument rose but PLN strengthened


def test_stale_and_invalid_rates_do_not_open():
    s = initial_state()
    b = PlnBroker(s)
    b.process('A', bar(60000), True, float('nan'), 120000)
    b.process('B', bar(60000), True, 4, 900000)
    assert not s['positions']


def test_daily_loss_circuit_breaker_blocks_new_entries():
    s = initial_state()
    s['risk']['daily_loss_limit_pln'] = 0.5
    b = PlnBroker(s)
    assert b.process('A', bar(60000), True, 4, 120000) == 'OPEN_LONG'
    gap = Candle(120000, 98, 100, 97, 98, 1)
    assert b.process('A', gap, False, 4, 180000) == 'STOP_GAP'
    assert s['risk']['halted'] is True
    assert s['risk']['halt_reason'] == 'DAILY_LOSS_LIMIT'
    assert b.process('B', bar(180000), True, 4, 240000) == 'RISK_HALT'


def test_risk_budget_sizes_entry_to_remaining_daily_loss():
    s = initial_state()
    s['risk']['daily_loss_limit_pln'] = 1.0
    b = PlnBroker(s)
    b.process('A', bar(60000), True, 4, 120000)
    assert s['positions']['A']['cost_pln'] < 100
    assert s['positions']['A']['max_loss_pln'] <= 1.0


def test_category_concentration_limit_and_decision_journal():
    s = initial_state()
    b = PlnBroker(s)
    b.process('A', bar(60000), True, 4, 120000, asset_type='crypto', strategy='trend', score=.1)
    b.process('B', bar(60000), True, 4, 120000, asset_type='crypto')
    b.process('C', bar(60000), True, 4, 120000, asset_type='crypto')
    assert len(s['positions']) == 3
    assert b.process('D', bar(60000), True, 4, 120000, asset_type='crypto') == 'RISK_BUDGET'
    assert s['decision_log'][0]['strategy'] == 'trend'
    assert s['decision_log'][-1]['action'] == 'RISK_BUDGET'


def test_rotation_closes_a_position_that_leaves_top_ten():
    s = initial_state()
    b = PlnBroker(s)
    b.process('A', bar(60000), True, 4, 120000, asset_type='stock')
    assert b.close_for_rotation('A', bar(120000, close=101), 4, 180000) == 'ROTATED_OUT'
    assert not s['positions']
    assert s['trades'][-1]['reason'] == 'ROTATED_OUT'


def test_daily_equity_keeps_the_last_complete_value_for_each_utc_day():
    s = initial_state()
    b = PlnBroker(s)
    b.snapshot({}, 60_000)
    b.snapshot({}, 120_000)
    b.snapshot({}, 86_400_000)
    assert len(s['daily_equity']) == 2
    assert s['daily_equity'][0]['timestamp'] == 120_000
    assert s['daily_equity'][1]['date'] == '1970-01-02'


def test_transaction_rollback_and_legacy_preservation(tmp_path):
    (tmp_path / 'user_portfolio.json').write_text(json.dumps({'balance': 25}))
    (tmp_path / 'ai_research.json').write_text(json.dumps({'virtual_broker': {'balance': 1107}}))
    ledger = PlnLedger(tmp_path)
    with ledger.transaction() as s:
        assert s['balance'] == 1000
        assert s['legacy_archive']['balance'] == 1107
        assert s['user_portfolio']['balance'] == 25
    with pytest.raises(RuntimeError):
        with ledger.transaction() as s:
            s['balance'] = 5
            raise RuntimeError('simulated failure')
    with ledger.transaction() as s:
        assert s['balance'] == 1000


def test_corrupt_reserve_is_not_silently_reset(tmp_path):
    (tmp_path / 'user_portfolio.json').write_text('broken')
    with pytest.raises(ValueError):
        with PlnLedger(tmp_path).transaction():
            pass


def test_cross_rates_include_usdt_without_dollar_parity(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {'data': {'currency': 'USD', 'rates': {'PLN': '4', 'JPY': '150', 'USDT': '0.99'}}}
    monkeypatch.setattr('src.data.fx_rates.requests.get', lambda *a, **kw: Response())
    rates = fetch_pln_rates(['PLN', 'USD', 'JPY', 'USDT'])['rates']
    assert rates['USD'] == 4
    assert rates['JPY'] == pytest.approx(4/150)
    assert rates['USDT'] == pytest.approx(4/.99)
