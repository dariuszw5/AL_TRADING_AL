from __future__ import annotations

import math
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests


BINANCE_BASE = "https://data-api.binance.vision"
YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"

TIMEOUT = 12
ATTEMPTS = 2

ASSETS = (
    {
        "asset_id": "BTCUSDT",
        "provider": "binance",
        "provider_symbol": "BTCUSDT",
    },
    {
        "asset_id": "ETHUSDT",
        "provider": "binance",
        "provider_symbol": "ETHUSDT",
    },
    {
        "asset_id": "SOLUSDT",
        "provider": "binance",
        "provider_symbol": "SOLUSDT",
    },
    {
        "asset_id": "BNBUSDT",
        "provider": "binance",
        "provider_symbol": "BNBUSDT",
    },
    {
        "asset_id": "XRPUSDT",
        "provider": "binance",
        "provider_symbol": "XRPUSDT",
    },
    {
        "asset_id": "GOLD_FUT_CONT",
        "provider": "yahoo",
        "provider_symbol": "GC=F",
    },
    {
        "asset_id": "WTI_FUT_CONT",
        "provider": "yahoo",
        "provider_symbol": "CL=F",
    },
    {
        "asset_id": "EURUSD",
        "provider": "yahoo",
        "provider_symbol": "EURUSD=X",
    },
    {
        "asset_id": "AAPL",
        "provider": "yahoo",
        "provider_symbol": "AAPL",
    },
)


SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "AL-Trading-Agent-Capability-Probe/1.0",
        "Accept": "application/json",
    }
)


def utc_now():
    return datetime.now(timezone.utc)


def finite_positive(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False

    return math.isfinite(number) and number > 0.0


def yes_no(value):
    return "YES" if value else "NO"


def request_json(url, params=None):
    last_error = None

    for attempt in range(1, ATTEMPTS + 1):
        started = time.perf_counter()

        try:
            response = SESSION.get(
                url,
                params=params,
                timeout=TIMEOUT,
            )

            latency_ms = (
                time.perf_counter() - started
            ) * 1000.0

            response.raise_for_status()

            return {
                "ok": True,
                "status_code": response.status_code,
                "latency_ms": round(latency_ms, 2),
                "url": response.url,
                "data": response.json(),
                "error": None,
            }

        except (
            requests.RequestException,
            ValueError,
        ) as exc:
            last_error = f"{type(exc).__name__}: {exc}"

            if attempt < ATTEMPTS:
                time.sleep(1.0)

    return {
        "ok": False,
        "status_code": None,
        "latency_ms": None,
        "url": url,
        "data": None,
        "error": last_error,
    }


def classify_delay_seconds(seconds):
    if seconds is None:
        return "UNKNOWN"

    try:
        seconds = max(
            0.0,
            float(seconds),
        )
    except (TypeError, ValueError):
        return "UNKNOWN"

    if seconds <= 10.0:
        return "REALTIME"

    minutes = max(
        1,
        math.ceil(seconds / 60.0),
    )

    return f"DELAYED_{minutes}MIN"


def format_rate_limits(rate_limits):
    if not rate_limits:
        return "UNKNOWN"

    result = []

    for row in rate_limits:
        result.append(
            "{type}:{limit}/{interval_num}{interval}".format(
                type=row.get(
                    "rateLimitType",
                    "UNKNOWN",
                ),
                limit=row.get(
                    "limit",
                    "?",
                ),
                interval_num=row.get(
                    "intervalNum",
                    "?",
                ),
                interval=row.get(
                    "interval",
                    "?",
                ),
            )
        )

    return "; ".join(result)


def binance_symbol_filters(exchange_info):
    symbols = (
        exchange_info.get("symbols")
        if isinstance(exchange_info, dict)
        else None
    ) or []

    if not symbols:
        return {}, None

    symbol_info = symbols[0]

    filters = {
        item.get("filterType"): item
        for item in symbol_info.get(
            "filters",
            [],
        )
        if item.get("filterType")
    }

    return filters, symbol_info


def probe_binance(asset):
    symbol = asset["provider_symbol"]

    endpoints = {
        "server_time": request_json(
            f"{BINANCE_BASE}/api/v3/time"
        ),
        "book_ticker": request_json(
            f"{BINANCE_BASE}/api/v3/ticker/bookTicker",
            {"symbol": symbol},
        ),
        "depth": request_json(
            f"{BINANCE_BASE}/api/v3/depth",
            {
                "symbol": symbol,
                "limit": 5,
            },
        ),
        "ticker_24hr": request_json(
            f"{BINANCE_BASE}/api/v3/ticker/24hr",
            {"symbol": symbol},
        ),
        "exchange_info": request_json(
            f"{BINANCE_BASE}/api/v3/exchangeInfo",
            {"symbol": symbol},
        ),
        "klines": request_json(
            f"{BINANCE_BASE}/api/v3/klines",
            {
                "symbol": symbol,
                "interval": "1m",
                "limit": 2,
            },
        ),
    }

    book = (
        endpoints["book_ticker"]["data"]
        if endpoints["book_ticker"]["ok"]
        else {}
    ) or {}

    depth = (
        endpoints["depth"]["data"]
        if endpoints["depth"]["ok"]
        else {}
    ) or {}

    ticker = (
        endpoints["ticker_24hr"]["data"]
        if endpoints["ticker_24hr"]["ok"]
        else {}
    ) or {}

    exchange_info = (
        endpoints["exchange_info"]["data"]
        if endpoints["exchange_info"]["ok"]
        else {}
    ) or {}

    klines = (
        endpoints["klines"]["data"]
        if endpoints["klines"]["ok"]
        else []
    ) or []

    server_time_payload = (
        endpoints["server_time"]["data"]
        if endpoints["server_time"]["ok"]
        else {}
    ) or {}

    filters, symbol_info = binance_symbol_filters(
        exchange_info
    )

    price_filter = filters.get(
        "PRICE_FILTER",
        {},
    )

    lot_size = filters.get(
        "LOT_SIZE",
        {},
    )

    notional = (
        filters.get("NOTIONAL")
        or filters.get("MIN_NOTIONAL")
        or {}
    )

    bid_available = finite_positive(
        book.get("bidPrice")
    )

    ask_available = finite_positive(
        book.get("askPrice")
    )

    depth_available = bool(
        depth.get("bids")
        and depth.get("asks")
    )

    last_available = finite_positive(
        ticker.get("lastPrice")
    )

    volume_available = (
        finite_positive(
            ticker.get("volume")
        )
        or finite_positive(
            ticker.get("quoteVolume")
        )
        or any(
            len(row) > 5
            and finite_positive(row[5])
            for row in klines
            if isinstance(row, list)
        )
    )

    server_time = server_time_payload.get(
        "serverTime"
    )

    provider_timestamp = ticker.get(
        "closeTime"
    )

    measured_age_seconds = None

    if (
        isinstance(server_time, (int, float))
        and isinstance(
            provider_timestamp,
            (int, float),
        )
    ):
        measured_age_seconds = max(
            0.0,
            (
                float(server_time)
                - float(provider_timestamp)
            )
            / 1000.0,
        )

    delay_classification = (
        classify_delay_seconds(
            measured_age_seconds
        )
    )

    metadata_available = (
        symbol_info is not None
    )

    tick_size_available = (
        finite_positive(
            price_filter.get("tickSize")
        )
    )

    quantity_rules_available = (
        finite_positive(
            lot_size.get("stepSize")
        )
        and finite_positive(
            lot_size.get("minQty")
        )
    )

    min_notional = (
        notional.get("minNotional")
        if isinstance(notional, dict)
        else None
    )

    endpoint_errors = {
        name: result["error"]
        for name, result in endpoints.items()
        if not result["ok"]
    }

    status = (
        "CONNECTED"
        if not endpoint_errors
        else "DEGRADED"
    )

    return {
        **asset,
        "probe_status": status,
        "bid": yes_no(bid_available),
        "ask": yes_no(ask_available),
        "book_depth": yes_no(
            depth_available
        ),
        "last": yes_no(last_available),
        "volume": yes_no(
            volume_available
        ),
        "feed_delay": delay_classification,
        "delay_source": (
            "/api/v3/ticker/24hr closeTime "
            "vs /api/v3/time serverTime"
        ),
        "measured_age_seconds": (
            None
            if measured_age_seconds is None
            else round(
                measured_age_seconds,
                3,
            )
        ),
        "streaming": "UNKNOWN_NOT_PROBED",
        "instrument_metadata": yes_no(
            metadata_available
        ),
        "tick_size_from_source": yes_no(
            tick_size_available
        ),
        "quantity_rules_from_source": yes_no(
            quantity_rules_available
        ),
        "tick_size": price_filter.get(
            "tickSize"
        ),
        "step_size": lot_size.get(
            "stepSize"
        ),
        "min_quantity": lot_size.get(
            "minQty"
        ),
        "min_notional": min_notional,
        "rate_limits": format_rate_limits(
            exchange_info.get(
                "rateLimits",
                [],
            )
        ),
        "officialness": (
            "OFFICIAL_PUBLIC_READ_ONLY_ENDPOINT"
        ),
        "provider_note": (
            "data-api.binance.vision public "
            "market-data endpoint"
        ),
        "endpoint_results": endpoints,
        "errors": endpoint_errors,
    }


def probe_yahoo(asset):
    symbol = asset["provider_symbol"]

    encoded = urllib.parse.quote(
        symbol,
        safe="",
    )

    endpoint = request_json(
        f"{YAHOO_BASE}/{encoded}",
        {
            "range": "1d",
            "interval": "1m",
            "includePrePost": "false",
            "events": "div,splits",
        },
    )

    if not endpoint["ok"]:
        return {
            **asset,
            "probe_status": "ERROR",
            "bid": "UNKNOWN",
            "ask": "UNKNOWN",
            "book_depth": "UNKNOWN",
            "last": "UNKNOWN",
            "volume": "UNKNOWN",
            "feed_delay": "UNKNOWN",
            "delay_source": (
                "Yahoo chart request failed"
            ),
            "measured_age_seconds": None,
            "streaming": "UNKNOWN_NOT_PROBED",
            "instrument_metadata": "UNKNOWN",
            "tick_size_from_source": "UNKNOWN",
            "quantity_rules_from_source": "UNKNOWN",
            "tick_size": None,
            "step_size": None,
            "min_quantity": None,
            "min_notional": None,
            "rate_limits": "UNKNOWN",
            "officialness": (
                "UNOFFICIAL / DEGRADED_BY_DESIGN"
            ),
            "provider_note": (
                "Yahoo Finance v8 chart endpoint"
            ),
            "endpoint_results": {
                "chart": endpoint
            },
            "errors": {
                "chart": endpoint["error"]
            },
        }

    payload = endpoint["data"] or {}
    chart = payload.get(
        "chart",
        {},
    )

    results = chart.get(
        "result",
    ) or []

    if not results:
        return {
            **asset,
            "probe_status": "ERROR",
            "bid": "UNKNOWN",
            "ask": "UNKNOWN",
            "book_depth": "UNKNOWN",
            "last": "UNKNOWN",
            "volume": "UNKNOWN",
            "feed_delay": "UNKNOWN",
            "delay_source": (
                "Yahoo chart returned no result"
            ),
            "measured_age_seconds": None,
            "streaming": "UNKNOWN_NOT_PROBED",
            "instrument_metadata": "NO",
            "tick_size_from_source": "NO",
            "quantity_rules_from_source": "NO",
            "tick_size": None,
            "step_size": None,
            "min_quantity": None,
            "min_notional": None,
            "rate_limits": "UNKNOWN",
            "officialness": (
                "UNOFFICIAL / DEGRADED_BY_DESIGN"
            ),
            "provider_note": (
                "Yahoo Finance v8 chart endpoint"
            ),
            "endpoint_results": {
                "chart": endpoint
            },
            "errors": {
                "chart": str(
                    chart.get("error")
                    or "empty result"
                )
            },
        }

    result = results[0]
    meta = result.get(
        "meta",
        {},
    ) or {}

    timestamps = result.get(
        "timestamp",
    ) or []

    quote_rows = (
        result.get(
            "indicators",
            {},
        )
        .get(
            "quote",
            [{}],
        )
    )

    quote = (
        quote_rows[0]
        if quote_rows
        else {}
    ) or {}

    volumes = quote.get(
        "volume",
    ) or []

    closes = quote.get(
        "close",
    ) or []

    bid_available = finite_positive(
        meta.get("bid")
    )

    ask_available = finite_positive(
        meta.get("ask")
    )

    # This endpoint is a chart endpoint; no order-book
    # depth structure is returned.
    depth_available = False

    last_available = finite_positive(
        meta.get("regularMarketPrice")
    ) or any(
        finite_positive(value)
        for value in closes
        if value is not None
    )

    volume_available = any(
        value is not None
        for value in volumes
    )

    delayed_by = meta.get(
        "exchangeDataDelayedBy"
    )

    feed_delay = (
        classify_delay_seconds(
            delayed_by
        )
        if isinstance(
            delayed_by,
            (int, float),
        )
        else "UNKNOWN"
    )

    latest_bar_age_seconds = None

    if timestamps:
        latest_timestamp = max(
            int(value)
            for value in timestamps
            if value is not None
        )

        latest_bar_age_seconds = max(
            0.0,
            utc_now().timestamp()
            - latest_timestamp,
        )

    metadata_available = bool(
        meta
    )

    return {
        **asset,
        "probe_status": "CONNECTED",
        "bid": yes_no(
            bid_available
        ),
        "ask": yes_no(
            ask_available
        ),
        "book_depth": yes_no(
            depth_available
        ),
        "last": yes_no(
            last_available
        ),
        "volume": yes_no(
            volume_available
        ),
        "feed_delay": feed_delay,
        "delay_source": (
            "chart.meta.exchangeDataDelayedBy"
            if delayed_by is not None
            else "UNKNOWN - metadata field absent"
        ),
        "exchange_data_delayed_by_seconds": delayed_by,
        "measured_age_seconds": (
            None
            if latest_bar_age_seconds is None
            else round(
                latest_bar_age_seconds,
                3,
            )
        ),
        "streaming": "UNKNOWN_NOT_PROBED",
        "instrument_metadata": yes_no(
            metadata_available
        ),
        "tick_size_from_source": "NO",
        "quantity_rules_from_source": "NO",
        "tick_size": None,
        "step_size": None,
        "min_quantity": None,
        "min_notional": None,
        "rate_limits": (
            "UNKNOWN - no stable public API contract"
        ),
        "officialness": (
            "UNOFFICIAL / DEGRADED_BY_DESIGN"
        ),
        "provider_note": (
            "Yahoo Finance v8 chart endpoint; "
            "research/display source, not a "
            "broker execution feed"
        ),
        "exchange": meta.get(
            "exchangeName"
        ),
        "currency": meta.get(
            "currency"
        ),
        "timezone": meta.get(
            "exchangeTimezoneName"
        ),
        "endpoint_results": {
            "chart": endpoint
        },
        "errors": {},
    }


def md_value(value):
    if value is None:
        return "UNKNOWN"

    return str(value).replace(
        "|",
        "\\|",
    )


def write_markdown(results):
    probe_time = utc_now().isoformat()

    lines = [
        "# PROVIDER CAPABILITY MATRIX",
        "",
        f"Probe timestamp UTC: `{probe_time}`",
        "",
        "This document records empirical provider capability observations",
        "for the current AL_TRADING_AL provider configuration.",
        "",
        "It is a point-in-time capability probe, not a guarantee of future",
        "availability. Missing information is recorded as UNKNOWN rather",
        "than inferred.",
        "",
        "No trading execution semantics are changed by this probe.",
        "",
        "## Summary",
        "",
        (
            "| Asset | Provider | Symbol | Bid | Ask | Depth | Last | "
            "Volume | Feed delay | Metadata | Tick size | Qty rules | Status |"
        ),
        (
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|"
        ),
    ]

    for row in results:
        lines.append(
            "| {asset_id} | {provider} | {provider_symbol} | "
            "{bid} | {ask} | {book_depth} | {last} | "
            "{volume} | {feed_delay} | {instrument_metadata} | "
            "{tick_size_from_source} | {quantity_rules_from_source} | "
            "{probe_status} |".format(
                **{
                    key: md_value(
                        row.get(key)
                    )
                    for key in (
                        "asset_id",
                        "provider",
                        "provider_symbol",
                        "bid",
                        "ask",
                        "book_depth",
                        "last",
                        "volume",
                        "feed_delay",
                        "instrument_metadata",
                        "tick_size_from_source",
                        "quantity_rules_from_source",
                        "probe_status",
                    )
                }
            )
        )

    lines.extend(
        [
            "",
            "## Detailed observations",
            "",
        ]
    )

    for row in results:
        lines.extend(
            [
                f"### {row['asset_id']}",
                "",
                f"- asset_id: `{row['asset_id']}`",
                f"- provider: `{row['provider']}`",
                f"- provider_symbol: `{row['provider_symbol']}`",
                f"- probe_status: `{row['probe_status']}`",
                f"- bid available: `{row['bid']}`",
                f"- ask available: `{row['ask']}`",
                f"- book depth available: `{row['book_depth']}`",
                f"- last available: `{row['last']}`",
                f"- volume available: `{row['volume']}`",
                f"- feed delay: `{row['feed_delay']}`",
                f"- delay source: `{md_value(row.get('delay_source'))}`",
                (
                    "- observed/latest timestamp age seconds: "
                    f"`{md_value(row.get('measured_age_seconds'))}`"
                ),
                f"- streaming available: `{row['streaming']}`",
                (
                    "- instrument metadata: "
                    f"`{row['instrument_metadata']}`"
                ),
                (
                    "- tick size from source: "
                    f"`{row['tick_size_from_source']}`"
                ),
                (
                    "- quantity rules from source: "
                    f"`{row['quantity_rules_from_source']}`"
                ),
                f"- tick_size: `{md_value(row.get('tick_size'))}`",
                f"- step_size: `{md_value(row.get('step_size'))}`",
                (
                    "- minimum_quantity: "
                    f"`{md_value(row.get('min_quantity'))}`"
                ),
                (
                    "- minimum_notional: "
                    f"`{md_value(row.get('min_notional'))}`"
                ),
                f"- rate limits: `{md_value(row.get('rate_limits'))}`",
                f"- API status: `{row['officialness']}`",
                f"- provider note: {row['provider_note']}",
                "",
                "Endpoints used:",
            ]
        )

        for name, endpoint in row[
            "endpoint_results"
        ].items():
            lines.append(
                "- `{name}`: status=`{status}`, "
                "latency_ms=`{latency}`, URL=`{url}`".format(
                    name=name,
                    status=(
                        endpoint.get("status_code")
                        if endpoint.get("ok")
                        else "ERROR"
                    ),
                    latency=md_value(
                        endpoint.get("latency_ms")
                    ),
                    url=endpoint.get("url"),
                )
            )

        if row.get("errors"):
            lines.extend(
                [
                    "",
                    "Errors:",
                ]
            )

            for name, error in row[
                "errors"
            ].items():
                lines.append(
                    f"- `{name}`: `{error}`"
                )

        lines.append("")

    lines.extend(
        [
            "## Provider notes",
            "",
            "### Binance",
            "",
            (
                "`data-api.binance.vision` is used as the project's "
                "public read-only market-data source."
            ),
            (
                "The probe checks bookTicker, depth, ticker/24hr, "
                "exchangeInfo, klines and server time."
            ),
            "",
            "### Yahoo",
            "",
            (
                "`query1.finance.yahoo.com/v8/finance/chart` is treated "
                "as `UNOFFICIAL / DEGRADED_BY_DESIGN`."
            ),
            (
                "It is not treated as an execution-grade provider. "
                "Missing bid/ask, depth or trading rules are not fabricated."
            ),
            "",
            (
                "`GOLD_FUT_CONT` (`GC=F`) and `WTI_FUT_CONT` (`CL=F`) "
                "are continuous-futures proxies, not spot instruments."
            ),
            "",
            "## Remaining unknowns",
            "",
            (
                "- Streaming capability is intentionally `UNKNOWN_NOT_PROBED` "
                "because this probe does not add a WebSocket dependency."
            ),
            (
                "- Yahoo rate limits are UNKNOWN because the chart endpoint "
                "does not have a stable public API contract."
            ),
            (
                "- Market/session-calendar correctness is not established "
                "by this probe; that belongs to the market-data/session phases."
            ),
            (
                "- This matrix does not authorize REALISTIC_V2 fills."
            ),
            "",
        ]
    )

    Path(
        "docs/PROVIDER_CAPABILITY.md"
    ).write_text(
        "\n".join(lines),
        encoding="utf-8",
        newline="\n",
    )


def main():
    results = []

    for asset in ASSETS:
        print(
            f"PROBING {asset['asset_id']:<14} "
            f"{asset['provider']:<8} "
            f"{asset['provider_symbol']}"
        )

        if asset["provider"] == "binance":
            result = probe_binance(asset)
        else:
            result = probe_yahoo(asset)

        results.append(result)

        print(
            "  status={status} bid={bid} ask={ask} "
            "depth={depth} last={last} volume={volume} "
            "delay={delay}".format(
                status=result["probe_status"],
                bid=result["bid"],
                ask=result["ask"],
                depth=result["book_depth"],
                last=result["last"],
                volume=result["volume"],
                delay=result["feed_delay"],
            )
        )

    if len(results) != 9:
        raise RuntimeError(
            f"Expected 9 assets, got {len(results)}"
        )

    write_markdown(results)

    print()
    print("PROVIDER CAPABILITY PROBE COMPLETE")
    print("Assets:", len(results))
    print(
        "Document: docs/PROVIDER_CAPABILITY.md"
    )

    failed = [
        row["asset_id"]
        for row in results
        if row["probe_status"] == "ERROR"
    ]

    degraded = [
        row["asset_id"]
        for row in results
        if row["probe_status"] == "DEGRADED"
    ]

    print("ERROR assets:", failed or "NONE")
    print("DEGRADED assets:", degraded or "NONE")

    if failed or degraded:
        print()
        print(
            "PROBE INCOMPLETE: capability document was "
            "saved, but provider errors require review."
        )
        return 2

    print()
    print(
        "PROBE GREEN: all 9 assets returned the "
        "required probe responses."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
