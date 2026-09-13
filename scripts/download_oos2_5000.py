import json
import time
import requests
from datetime import datetime, timezone

BASE_URL = "https://data-api.binance.vision"
SYMBOL = "BTCUSDT"
INTERVAL = "1m"
LIMIT = 5000

# OOS #2 zaczyna się dokładnie po ostatniej świecy OOS #1
START_MS = 1788462840000
END_MS = START_MS + (LIMIT - 1) * 60_000

OUTPUT = "data/backtest/BTCUSDT_1m_forward_5000_oos2.json"


def get_batch(start_time, end_time, limit=1000):
    response = requests.get(
        f"{BASE_URL}/api/v3/klines",
        params={
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "startTime": start_time,
            "endTime": end_time,
            "limit": limit,
        },
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


all_candles = []
current_start = START_MS

while current_start <= END_MS and len(all_candles) < LIMIT:
    batch = get_batch(
        current_start,
        END_MS,
        min(1000, LIMIT - len(all_candles)),
    )

    if not batch:
        break

    all_candles.extend(batch)

    print(
        f"Pobrano: {len(all_candles)}/{LIMIT} | "
        f"ostatnia: {datetime.fromtimestamp(batch[-1][0] / 1000, tz=timezone.utc)}"
    )

    current_start = batch[-1][0] + 60_000

    if len(batch) < min(1000, LIMIT - len(all_candles)):
        break

    time.sleep(0.2)


if len(all_candles) != LIMIT:
    raise RuntimeError(
        f"Nieprawidlowa liczba swiec: {len(all_candles)}, oczekiwano {LIMIT}"
    )


data = []

for item in all_candles:
    data.append({
        "timestamp": item[0],
        "open": float(item[1]),
        "high": float(item[2]),
        "low": float(item[3]),
        "close": float(item[4]),
        "volume": float(item[5]),
    })


with open(OUTPUT, "w", encoding="utf-8") as file:
    json.dump(data, file, indent=2)


print()
print("=" * 80)
print("OOS #2 DATASET CREATED")
print("=" * 80)
print(f"File:  {OUTPUT}")
print(f"Count: {len(data)}")
print(
    "FIRST:",
    datetime.fromtimestamp(data[0]["timestamp"] / 1000, tz=timezone.utc),
)
print(
    "LAST :",
    datetime.fromtimestamp(data[-1]["timestamp"] / 1000, tz=timezone.utc),
)
