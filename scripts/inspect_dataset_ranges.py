import json
from datetime import datetime, timezone

DATASETS = {
    "TRAIN": "data/backtest/BTCUSDT_1m_5000.json",
    "VALID": "data/backtest/BTCUSDT_1m_validation_5000.json",
    "TEST": "data/backtest/BTCUSDT_1m_test_5000.json",
}

def candles_from(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("candles", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]
    raise ValueError("Nieznana struktura JSON")

def ts_of(c):
    if isinstance(c, dict):
        return int(c["timestamp"])
    return int(c[0])

for name, path in DATASETS.items():
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    candles = candles_from(data)
    ts = [ts_of(c) for c in candles]

    first = min(ts)
    last = max(ts)

    print(f"{name}: {len(candles)} candles")
    print("  FIRST:", first, datetime.fromtimestamp(first / 1000, tz=timezone.utc))
    print("  LAST :", last, datetime.fromtimestamp(last / 1000, tz=timezone.utc))
