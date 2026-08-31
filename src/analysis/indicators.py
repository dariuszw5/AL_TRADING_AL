def sma(values, period):
    if period <= 0:
        raise ValueError("Period must be greater than zero")

    if len(values) < period:
        return []

    result = []

    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        result.append(sum(window) / period)

    return result


def ema(values, period):
    if period <= 0:
        raise ValueError("Period must be greater than zero")

    if len(values) < period:
        return []

    result = []

    previous = sum(values[:period]) / period
    result.append(previous)

    multiplier = 2 / (period + 1)

    for value in values[period:]:
        current = (value - previous) * multiplier + previous
        result.append(current)
        previous = current

    return result


def rsi(values, period):
    if period <= 0:
        raise ValueError("Period must be greater than zero")

    if len(values) <= period:
        return []

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    result = []

    for i in range(period, len(gains) + 1):
        average_gain = sum(gains[i - period:i]) / period
        average_loss = sum(losses[i - period:i]) / period

        if average_loss == 0:
            result.append(100.0)
        else:
            relative_strength = average_gain / average_loss
            result.append(
                100 - (100 / (1 + relative_strength))
            )

    return result


def rsi_wilder(values, period):
    if period <= 0:
        raise ValueError("Period must be greater than zero")

    if len(values) <= period:
        return []

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))

    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period

    result = []

    if average_loss == 0:
        result.append(100.0)
    else:
        relative_strength = average_gain / average_loss
        result.append(
            100 - (100 / (1 + relative_strength))
        )

    for i in range(period, len(gains)):
        average_gain = (
            (average_gain * (period - 1))
            + gains[i]
        ) / period

        average_loss = (
            (average_loss * (period - 1))
            + losses[i]
        ) / period

        if average_loss == 0:
            result.append(100.0)
        elif average_gain == 0:
            result.append(0.0)
        else:
            relative_strength = average_gain / average_loss
            result.append(
                100 - (100 / (1 + relative_strength))
            )

    return result