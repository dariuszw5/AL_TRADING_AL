from src.analysis.indicators import sma, ema, rsi


def test_sma():
    values = [10, 20, 30, 40, 50]

    assert sma(values, 3) == [20.0, 30.0, 40.0]


def test_ema():
    values = [10, 20, 30, 40, 50]

    result = ema(values, 3)

    assert len(result) == 3
    assert result[0] == 20.0
    assert result[1] == 30.0
    assert result[2] == 40.0


def test_rsi():
    values = [10, 11, 12, 11, 13, 14, 13, 15]

    result = rsi(values, 3)

    assert len(result) == 5
    assert all(0 <= value <= 100 for value in result)