"""Audit whether forecast probabilities match paper-trading outcomes."""
from math import isfinite


def calibration_report(trades, bins=5):
    """Summarise only closed trades that recorded a probability forecast.

    The Brier score is lower when probabilities are better calibrated. This is
    an evaluation report; it never changes a strategy or risk limit itself.
    """
    observations = []
    for trade in trades:
        probability = trade.get('confidence_probability')
        profit = trade.get('profit')
        if not isinstance(probability, (int, float)) or not isinstance(profit, (int, float)):
            continue
        if not isfinite(probability) or not isfinite(profit) or not 0 <= probability <= 1:
            continue
        observations.append((float(probability), int(profit > 0)))
    buckets = [[] for _ in range(bins)]
    for probability, outcome in observations:
        buckets[min(bins - 1, int(probability * bins))].append((probability, outcome))
    groups = []
    for index, values in enumerate(buckets):
        if not values:
            continue
        groups.append({
            'range': [index / bins, (index + 1) / bins],
            'trades': len(values),
            'mean_forecast': round(sum(p for p, _ in values) / len(values), 4),
            'realized_win_rate': round(sum(y for _, y in values) / len(values), 4),
        })
    brier = (sum((probability - outcome) ** 2 for probability, outcome in observations)
             / len(observations) if observations else None)
    return {
        'closed_forecasts': len(observations),
        'brier_score': round(brier, 4) if brier is not None else None,
        'groups': groups,
        'ready': len(observations) >= 30,
        'note': ('Wymagane jest co najmniej 30 zamkniętych prognoz przed oceną kalibracji.'
                 if len(observations) < 30 else 'Raport porównuje prognozy z wynikami paper trading.'),
    }
