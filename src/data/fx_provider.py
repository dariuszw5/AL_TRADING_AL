from __future__ import annotations

from dataclasses import asdict, dataclass
import time
from typing import Any

import requests


@dataclass(frozen=True)
class PlnRate:
    source_currency: str
    rate_to_pln: float
    path: str
    providers: tuple[str, ...]
    quality: str
    observed_at_unix: float
    effective_date: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["providers"] = list(self.providers)
        return payload


class FxRateProvider:
    """Small reporting-only FX adapter for the existing paper application.

    It never fabricates USD/PLN or assumes USDT == USD. USD/PLN comes from
    the official NBP table A reference rate. USDT/PLN additionally requires
    a real USDT/USD quote from Coinbase Exchange.
    """

    NBP_USD_URL = "https://api.nbp.pl/api/exchangerates/rates/a/usd/"
    COINBASE_USDT_URL = "https://api.exchange.coinbase.com/products/USDT-USD/ticker"

    def __init__(self, ttl_seconds: float = 60.0, timeout_seconds: float = 1.5):
        self.ttl_seconds = float(ttl_seconds)
        self.timeout_seconds = float(timeout_seconds)
        self._cache: dict[str, tuple[float, PlnRate]] = {}

    def _cached(self, currency: str) -> PlnRate | None:
        item = self._cache.get(currency)
        if item is None:
            return None
        cached_at, rate = item
        if time.time() - cached_at <= self.ttl_seconds:
            return rate
        return None

    def _store(self, currency: str, rate: PlnRate) -> PlnRate:
        self._cache[currency] = (time.time(), rate)
        return rate

    def _get_json(self, url: str, *, headers: dict[str, str] | None = None) -> Any:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < 1:
                    time.sleep(0.1)
        if last_error is None:
            raise RuntimeError("FX request failed")
        raise last_error

    def _usd_to_pln(self) -> PlnRate:
        cached = self._cached("USD")
        if cached is not None:
            return cached

        payload = self._get_json(
            self.NBP_USD_URL,
            headers={"Accept": "application/json"},
        )
        rates = payload.get("rates") or []
        if not rates:
            raise ValueError("NBP returned no USD/PLN reference rate")

        latest = rates[-1]
        value = float(latest["mid"])
        if value <= 0:
            raise ValueError("NBP returned invalid USD/PLN rate")

        return self._store(
            "USD",
            PlnRate(
                source_currency="USD",
                rate_to_pln=value,
                path="USD→PLN",
                providers=("NBP_TABLE_A",),
                quality="DAILY_REFERENCE",
                observed_at_unix=time.time(),
                effective_date=str(latest.get("effectiveDate") or "") or None,
            ),
        )

    def _usdt_to_usd(self) -> float:
        payload = self._get_json(
            self.COINBASE_USDT_URL,
            headers={"User-Agent": "AL-Trading-Agent-Paper/1.0"},
        )
        # Coinbase ticker normally contains price, bid and ask. For reporting
        # use the real last price; execution continues to use the existing
        # trading engine and is not changed by this module.
        value = float(payload["price"])
        if value <= 0:
            raise ValueError("Coinbase returned invalid USDT/USD rate")
        return value

    def quote_to_pln(self, currency: str) -> PlnRate:
        normalized = currency.upper().strip()

        if normalized == "PLN":
            return PlnRate(
                source_currency="PLN",
                rate_to_pln=1.0,
                path="PLN",
                providers=("DIRECT",),
                quality="DIRECT",
                observed_at_unix=time.time(),
            )

        if normalized == "USD":
            return self._usd_to_pln()

        if normalized == "USDT":
            cached = self._cached("USDT")
            if cached is not None:
                return cached

            usdtusd = self._usdt_to_usd()
            usdpln = self._usd_to_pln()
            rate = usdtusd * usdpln.rate_to_pln
            if rate <= 0:
                raise ValueError("Invalid USDT→USD→PLN conversion")

            return self._store(
                "USDT",
                PlnRate(
                    source_currency="USDT",
                    rate_to_pln=rate,
                    path="USDT→USD→PLN",
                    providers=("COINBASE_EXCHANGE", "NBP_TABLE_A"),
                    quality="LIVE_PLUS_DAILY_REFERENCE",
                    observed_at_unix=time.time(),
                    effective_date=usdpln.effective_date,
                ),
            )

        raise ValueError(f"No real PLN conversion path for {currency}")

    def convert(self, amount: float, currency: str) -> tuple[float, PlnRate]:
        rate = self.quote_to_pln(currency)
        return float(amount) * rate.rate_to_pln, rate
