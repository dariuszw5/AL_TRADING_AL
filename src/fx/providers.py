from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import (
    date,
    datetime,
    timezone,
)

from src.core.clock import (
    Clock,
    SystemClock,
)

from .models import (
    FxQuote,
    FxSourceQuality,
)


class FxProviderError(
    RuntimeError
):
    pass


class UrlLibJsonClient:
    """
    Minimal stdlib JSON HTTP client.

    No third-party dependency is introduced by
    the Phase 09 FX provider layer.
    """

    def __init__(
        self,
        *,
        user_agent=(
            "AL_TRADING_AL/"
            "Phase09-FX"
        ),
    ):
        self.user_agent = str(
            user_agent
        )

    def get_json(
        self,
        url,
        *,
        timeout_seconds,
    ):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    self.user_agent
                ),
                "Accept": (
                    "application/json"
                ),
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=float(
                    timeout_seconds
                ),
            ) as response:
                raw = response.read()

        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
        ) as exc:
            raise FxProviderError(
                "FX_HTTP_REQUEST_FAILED: "
                f"{exc}"
            ) from exc

        try:
            return json.loads(
                raw.decode(
                    "utf-8"
                )
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise FxProviderError(
                "FX_INVALID_JSON_RESPONSE"
            ) from exc


def _parse_iso_utc(
    value,
):
    text = str(
        value
    ).strip()

    if not text:
        raise FxProviderError(
            "FX_PROVIDER_TIMESTAMP_UNAVAILABLE"
        )

    if text.endswith("Z"):
        text = (
            text[:-1]
            + "+00:00"
        )

    try:
        parsed = datetime.fromisoformat(
            text
        )

    except ValueError as exc:
        raise FxProviderError(
            "FX_INVALID_PROVIDER_TIMESTAMP"
        ) from exc

    if parsed.tzinfo is None:
        raise FxProviderError(
            "FX_PROVIDER_TIMESTAMP_NOT_AWARE"
        )

    return parsed.astimezone(
        timezone.utc
    )


class NbpTableAProvider:
    """
    NBP Table A reference-accounting adapter.

    NBP does not provide a reliable intraday
    publication timestamp in this response.

    Therefore provider_timestamp is deliberately
    None. effective_date and table number are
    preserved instead.

    This prevents DAILY_REFERENCE from being
    silently treated as fresh intraday MTM.
    """

    BASE_URL = (
        "https://api.nbp.pl/"
        "api/exchangerates/rates/a"
    )

    SUPPORTED = {
        "USD",
        "EUR",
    }

    def __init__(
        self,
        *,
        json_client=None,
        clock: Clock | None = None,
        timeout_seconds=10.0,
    ):
        self.json_client = (
            json_client
            or UrlLibJsonClient()
        )

        self.clock = (
            clock
            or SystemClock()
        )

        self.timeout_seconds = float(
            timeout_seconds
        )

    def get_reference(
        self,
        currency,
        *,
        effective_date=None,
    ):
        currency = (
            str(currency)
            .strip()
            .upper()
        )

        if currency not in self.SUPPORTED:
            raise ValueError(
                "unsupported NBP currency: "
                f"{currency}"
            )

        now = self.clock.now()

        if (
            effective_date is not None
            and effective_date
            > now.date()
        ):
            raise ValueError(
                "future NBP effective date "
                "is not allowed"
            )

        code = currency.lower()

        if effective_date is None:
            url = (
                f"{self.BASE_URL}/"
                f"{code}/?format=json"
            )
        else:
            url = (
                f"{self.BASE_URL}/"
                f"{code}/"
                f"{effective_date.isoformat()}/"
                "?format=json"
            )

        payload = (
            self.json_client
            .get_json(
                url,
                timeout_seconds=(
                    self.timeout_seconds
                ),
            )
        )

        rates = payload.get(
            "rates"
        )

        if not rates:
            raise FxProviderError(
                "NBP_RATE_UNAVAILABLE"
            )

        item = rates[-1]

        try:
            rate = float(
                item["mid"]
            )

            table = str(
                item["no"]
            )

            returned_date = (
                date.fromisoformat(
                    str(
                        item[
                            "effectiveDate"
                        ]
                    )
                )
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise FxProviderError(
                "NBP_INVALID_RATE_PAYLOAD"
            ) from exc

        if returned_date > now.date():
            raise FxProviderError(
                "NBP_FUTURE_EFFECTIVE_DATE"
            )

        if (
            effective_date is not None
            and returned_date
            != effective_date
        ):
            raise FxProviderError(
                "NBP_EFFECTIVE_DATE_MISMATCH"
            )

        return FxQuote(
            base_currency=currency,
            quote_currency="PLN",
            rate=rate,
            provider="NBP_TABLE_A",
            provider_timestamp=None,
            observed_at=now,
            source_quality=(
                FxSourceQuality
                .DAILY_REFERENCE
            ),
            table=table,
            effective_date=(
                returned_date
            ),
            labels=(
                "REFERENCE_ACCOUNTING_ONLY",
                (
                    "PUBLICATION_TIMESTAMP_"
                    "UNAVAILABLE"
                ),
            ),
        )


class YahooPlnProvider:
    """
    Yahoo v8 chart FX adapter.

    Always STALE_PRONE.

    A successful HTTP request and even
    exchangeDataDelayedBy=0 do not upgrade
    this unofficial source to LIVE.
    """

    BASE_URL = (
        "https://query1.finance.yahoo.com/"
        "v8/finance/chart"
    )

    SYMBOLS = {
        "USD": "PLN=X",
        "EUR": "EURPLN=X",
    }

    def __init__(
        self,
        *,
        json_client=None,
        clock: Clock | None = None,
        timeout_seconds=10.0,
    ):
        self.json_client = (
            json_client
            or UrlLibJsonClient()
        )

        self.clock = (
            clock
            or SystemClock()
        )

        self.timeout_seconds = float(
            timeout_seconds
        )

    def get_quote(
        self,
        base_currency,
    ):
        base = (
            str(base_currency)
            .strip()
            .upper()
        )

        symbol = self.SYMBOLS.get(
            base
        )

        if symbol is None:
            raise ValueError(
                "unsupported Yahoo PLN base: "
                f"{base}"
            )

        encoded_symbol = (
            urllib.parse.quote(
                symbol,
                safe="=",
            )
        )

        url = (
            f"{self.BASE_URL}/"
            f"{encoded_symbol}"
            "?interval=1m&range=1d"
        )

        payload = (
            self.json_client
            .get_json(
                url,
                timeout_seconds=(
                    self.timeout_seconds
                ),
            )
        )

        try:
            result = (
                payload["chart"][
                    "result"
                ]
            )

            if not result:
                raise KeyError(
                    "chart.result"
                )

            meta = result[0][
                "meta"
            ]

            rate = float(
                meta[
                    "regularMarketPrice"
                ]
            )

        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as exc:
            raise FxProviderError(
                "YAHOO_FX_QUOTE_UNAVAILABLE"
            ) from exc

        raw_timestamp = meta.get(
            "regularMarketTime"
        )

        provider_timestamp = None

        if raw_timestamp is not None:
            try:
                provider_timestamp = (
                    datetime.fromtimestamp(
                        float(
                            raw_timestamp
                        ),
                        tz=timezone.utc,
                    )
                )

            except (
                TypeError,
                ValueError,
                OSError,
            ) as exc:
                raise FxProviderError(
                    "YAHOO_INVALID_PROVIDER_TIMESTAMP"
                ) from exc

        delay = meta.get(
            "exchangeDataDelayedBy"
        )

        labels = [
            "UNOFFICIAL",
            "DEGRADED_BY_DESIGN",
        ]

        if (
            delay is None
            or delay == ""
        ):
            labels.append(
                "DELAY_METADATA_UNAVAILABLE"
            )
        else:
            labels.append(
                "EXCHANGE_DATA_DELAYED_BY:"
                f"{delay}"
            )

        if provider_timestamp is None:
            labels.append(
                "PROVIDER_TIMESTAMP_UNAVAILABLE"
            )

        return FxQuote(
            base_currency=base,
            quote_currency="PLN",
            rate=rate,
            provider=(
                "YAHOO_FINANCE_V8_CHART"
            ),
            provider_timestamp=(
                provider_timestamp
            ),
            observed_at=(
                self.clock.now()
            ),
            source_quality=(
                FxSourceQuality
                .STALE_PRONE
            ),
            labels=tuple(
                labels
            ),
        )


class CoinbaseUsdtUsdProvider:
    """
    Public Coinbase Exchange USDT-USD
    level-1 order-book reference.

    Conversion reference rate:
        midpoint = (bid + ask) / 2
    """

    URL = (
        "https://api.exchange.coinbase.com/"
        "products/USDT-USD/book?level=1"
    )

    def __init__(
        self,
        *,
        json_client=None,
        clock: Clock | None = None,
        timeout_seconds=10.0,
    ):
        self.json_client = (
            json_client
            or UrlLibJsonClient()
        )

        self.clock = (
            clock
            or SystemClock()
        )

        self.timeout_seconds = float(
            timeout_seconds
        )

    def get_quote(
        self,
    ):
        payload = (
            self.json_client
            .get_json(
                self.URL,
                timeout_seconds=(
                    self.timeout_seconds
                ),
            )
        )

        bids = payload.get(
            "bids"
        )

        asks = payload.get(
            "asks"
        )

        if not bids or not asks:
            raise FxProviderError(
                "COINBASE_BOOK_UNAVAILABLE"
            )

        try:
            bid = float(
                bids[0][0]
            )

            ask = float(
                asks[0][0]
            )

        except (
            IndexError,
            TypeError,
            ValueError,
        ) as exc:
            raise FxProviderError(
                "COINBASE_INVALID_BOOK"
            ) from exc

        raw_time = payload.get(
            "time"
        )

        if not raw_time:
            raise FxProviderError(
                "COINBASE_PROVIDER_TIMESTAMP_UNAVAILABLE"
            )

        provider_timestamp = (
            _parse_iso_utc(
                raw_time
            )
        )

        rate = (
            bid
            + ask
        ) / 2.0

        return FxQuote(
            base_currency="USDT",
            quote_currency="USD",
            rate=rate,
            provider=(
                "COINBASE_EXCHANGE"
            ),
            provider_timestamp=(
                provider_timestamp
            ),
            observed_at=(
                self.clock.now()
            ),
            source_quality=(
                FxSourceQuality.LIVE
            ),
            bid=bid,
            ask=ask,
            labels=(
                "PUBLIC_ORDER_BOOK",
                "MIDPOINT_REFERENCE",
            ),
        )
