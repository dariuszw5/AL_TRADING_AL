from src.strategy.basic_strategy import BasicStrategy


def test_buy_signal():
    strategy = BasicStrategy()

    signal = strategy.generate_signal(
        sma_value=100,
        ema_value=105,
        rsi_value=30
    )

    assert signal == "BUY"


def test_sell_signal():
    strategy = BasicStrategy()

    signal = strategy.generate_signal(
        sma_value=105,
        ema_value=100,
        rsi_value=70
    )

    assert signal == "SELL"


def test_hold_signal():
    strategy = BasicStrategy()

    signal = strategy.generate_signal(
        sma_value=100,
        ema_value=101,
        rsi_value=50
    )

    assert signal == "HOLD"