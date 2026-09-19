from __future__ import annotations

from datetime import datetime, timezone
import time

from src.data.assets import SUPPORTED_ASSETS
from src.data.data_provider import DataProvider
from src.data.fx_provider import FxRateProvider


def main():
    provider = DataProvider()
    fx = FxRateProvider(ttl_seconds=0)

    print("=" * 96)
    print("AL TRADING AGENT | REAL DATA NETWORK SMOKE")
    print("READ-ONLY MARKET/FX CHECK - ZERO REAL ORDERS")
    print("=" * 96)

    failures = 0

    for asset in SUPPORTED_ASSETS:
        try:
            candles = provider.get_candles(
                symbol=asset.symbol,
                interval="1m",
                limit=5,
            )
            latest = candles[-1]
            age = max(0.0, time.time() - latest.timestamp / 1000.0)
            print(
                f"{asset.symbol:<14} MARKET OK  "
                f"provider={asset.provider:<7} "
                f"last={latest.close:<14g} age={age:>8.1f}s"
            )
        except Exception as exc:
            failures += 1
            print(f"{asset.symbol:<14} MARKET FAIL {type(exc).__name__}: {exc}")

    for currency in ("USD", "USDT"):
        try:
            rate = fx.quote_to_pln(currency)
            print(
                f"{currency:<14} FX OK      "
                f"rate={rate.rate_to_pln:.8f} PLN "
                f"path={rate.path} providers={','.join(rate.providers)}"
            )
        except Exception as exc:
            failures += 1
            print(f"{currency:<14} FX FAIL    {type(exc).__name__}: {exc}")

    print("-" * 96)
    print("UTC:", datetime.now(timezone.utc).isoformat())
    print("REAL EXCHANGE ORDERS SENT: 0")
    print("RESULT:", "PASS" if failures == 0 else f"PARTIAL/FAIL ({failures} checks)")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
