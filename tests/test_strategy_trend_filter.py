from src.strategy.basic_strategy import BasicStrategy


def test_strategy_holds_when_ema_sma_difference_is_too_small():
    strategy = BasicStrategy()

    signal = strategy.generate_signal(
        sma_value=100.0,
        ema_value=100.5,
        rsi_value=25.0,
        min_difference=1.0
    )

    assert signal == "HOLD"


def test_strategy_allows_buy_when_ema_sma_difference_is_large_enough():
    strategy = BasicStrategy()

    signal = strategy.generate_signal(
        sma_value=100.0,
        ema_value=102.0,
        rsi_value=25.0,
        min_difference=1.0
    )

    assert signal == "BUY"


def test_strategy_allows_sell_when_ema_sma_difference_is_large_enough():
    strategy = BasicStrategy()

    signal = strategy.generate_signal(
        sma_value=102.0,
        ema_value=100.0,
        rsi_value=75.0,
        min_difference=1.0
    )

    assert signal == "SELL"
