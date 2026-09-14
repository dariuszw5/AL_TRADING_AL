from src.agent.virtual_broker import VirtualBroker
from src.data.candle import Candle


def test_virtual_broker_applies_costs_and_closes_take_profit():
    broker = VirtualBroker()
    assert broker.open('BTCUSDT', 100.0, 1)
    assert not broker.open('BTCUSDT', 100.0, 2)
    trade = broker.mark('BTCUSDT', Candle(2, 100, 103, 100, 102, 1), 2)
    assert trade['reason'] == 'TAKE_PROFIT'
    assert trade['profit'] > 0
    assert broker.positions == {}
    snapshot = broker.snapshot({'BTCUSDT': 102}, 2)
    assert snapshot['open_positions'] == 0
    assert snapshot['equity'] == broker.balance


def test_virtual_broker_stop_loss_is_virtual_only():
    broker = VirtualBroker()
    broker.open('ETHUSDT', 100.0, 1)
    trade = broker.mark('ETHUSDT', Candle(2, 100, 100, 98, 99, 1), 2)
    assert trade['reason'] == 'STOP_LOSS'
    assert len(broker.trades) == 1
