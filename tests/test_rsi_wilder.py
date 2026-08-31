from src.analysis.indicators import rsi_wilder


def test_rsi_wilder_returns_values_between_zero_and_hundred():
    values = [
        10, 11, 12, 11, 13, 14, 13, 15,
        16, 15, 17, 18, 17, 19, 20, 18
    ]

    result = rsi_wilder(values, 5)

    assert result
    assert all(0 <= value <= 100 for value in result)


def test_rsi_wilder_returns_empty_when_not_enough_data():
    values = [10, 11, 12, 13]

    result = rsi_wilder(values, 5)

    assert result == []


def test_rsi_wilder_handles_only_gains():
    values = [
        10, 11, 12, 13, 14, 15,
        16, 17, 18, 19, 20
    ]

    result = rsi_wilder(values, 5)

    assert result
    assert all(value == 100.0 for value in result)


def test_rsi_wilder_handles_only_losses():
    values = [
        20, 19, 18, 17, 16, 15,
        14, 13, 12, 11, 10
    ]

    result = rsi_wilder(values, 5)

    assert result
    assert all(value == 0.0 for value in result)