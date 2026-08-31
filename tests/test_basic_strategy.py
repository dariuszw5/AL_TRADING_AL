from src.strategy.basic_strategy import BasicStrategy


def test_buy_signal():
    strategy = BasicStrategy()

    signal = strategy.generate_signal(
        sma_value=100,
        ema_value=105,
        rsi_value=25
    )

    assert signal == "BUY"


def test_sell_signal():
    strategy = BasicStrategy()

    signal = strategy.generate_signal(
        sma_value=105,
        ema_value=100,
        rsi_value=75
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


def test_rsi_boundary_30_is_hold():
    strategy = BasicStrategy()

    signal = strategy.generate_signal(
        sma_value=100,
        ema_value=105,
        rsi_value=30
    )

    assert signal == "HOLD"


def test_rsi_boundary_70_is_hold():
    strategy = BasicStrategy()

    signal = strategy.generate_signal(
        sma_value=105,
        ema_value=100,
        rsi_value=70
    )

    assert signal == "HOLD"


def test_buy_does_not_require_rising_ema():
    strategy = BasicStrategy()

    signal = strategy.generate_signal(
        sma_value=100,
        ema_value=105,
        rsi_value=25,
        previous_ema=106
    )

    assert signal == "BUY"


def test_sell_does_not_require_falling_ema():
    strategy = BasicStrategy()

    signal = strategy.generate_signal(
        sma_value=105,
        ema_value=100,
        rsi_value=75,
        previous_ema=99
    )

    assert signal == "SELL"
