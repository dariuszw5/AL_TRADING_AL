from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests


TIMEOUT = 12

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "AL-Trading-Agent-Phase07-Research/1.0",
        "Accept": "application/json",
    }
)


def build_url(host: str, path: str) -> str:
    return "https" + "://" + host + path


def request_json(host, path, *, params=None, headers=None):
    url = build_url(host, path)

    try:
        response = SESSION.get(
            url,
            params=params,
            headers=headers,
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        return {
            "ok": True,
            "status_code": response.status_code,
            "url": response.url,
            "data": response.json(),
            "error": None,
        }

    except Exception as exc:
        return {
            "ok": False,
            "status_code": getattr(
                getattr(exc, "response", None),
                "status_code",
                None,
            ),
            "url": url,
            "data": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def probe_nbp(code):
    return request_json(
        "api.nbp.pl",
        f"/api/exchangerates/rates/a/{code.lower()}/",
        params={"format": "json"},
    )


def probe_yahoo(symbol):
    encoded = urllib.parse.quote(
        symbol,
        safe="",
    )

    result = request_json(
        "query1.finance.yahoo.com",
        f"/v8/finance/chart/{encoded}",
        params={
            "range": "1d",
            "interval": "1m",
            "includePrePost": "true",
            "events": "div,splits",
        },
    )

    if not result["ok"]:
        return result

    payload = result["data"] or {}
    chart = payload.get("chart", {})
    rows = chart.get("result") or []

    if not rows:
        result["ok"] = False
        result["error"] = str(
            chart.get("error")
            or "empty chart result"
        )
        return result

    row = rows[0]
    meta = row.get("meta") or {}

    result["summary"] = {
        "symbol": symbol,
        "currency": meta.get("currency"),
        "exchangeName": meta.get("exchangeName"),
        "fullExchangeName": meta.get("fullExchangeName"),
        "instrumentType": meta.get("instrumentType"),
        "exchangeTimezoneName": meta.get(
            "exchangeTimezoneName"
        ),
        "gmtoffset": meta.get("gmtoffset"),
        "regularMarketPrice": meta.get(
            "regularMarketPrice"
        ),
        "regularMarketTime": meta.get(
            "regularMarketTime"
        ),
        "exchangeDataDelayedBy": meta.get(
            "exchangeDataDelayedBy"
        ),
        "currentTradingPeriod": meta.get(
            "currentTradingPeriod"
        ),
        "dataGranularity": meta.get(
            "dataGranularity"
        ),
    }

    # Avoid storing the complete minute-bar payload.
    result["data"] = None

    return result


def probe_coinbase_usdt_usd():
    return request_json(
        "api.exchange.coinbase.com",
        "/products/USDT-USD/ticker",
    )


def nbp_summary(result):
    if not result["ok"]:
        return None

    payload = result["data"] or {}
    rates = payload.get("rates") or []

    if not rates:
        return None

    rate = rates[-1]

    return {
        "currency": payload.get("currency"),
        "code": payload.get("code"),
        "table": payload.get("table"),
        "no": rate.get("no"),
        "effectiveDate": rate.get(
            "effectiveDate"
        ),
        "mid": rate.get("mid"),
    }


def coinbase_summary(result):
    if not result["ok"]:
        return None

    payload = result["data"] or {}

    return {
        "trade_id": payload.get("trade_id"),
        "price": payload.get("price"),
        "size": payload.get("size"),
        "bid": payload.get("bid"),
        "ask": payload.get("ask"),
        "volume": payload.get("volume"),
        "time": payload.get("time"),
    }


def main():
    generated_at = datetime.now(
        timezone.utc
    ).isoformat()

    nbp = {
        "USD": probe_nbp("USD"),
        "EUR": probe_nbp("EUR"),
    }

    yahoo_symbols = (
        "USDPLN=X",
        "EURPLN=X",
        "EURUSD=X",
        "AAPL",
        "GC=F",
        "CL=F",
    )

    yahoo = {
        symbol: probe_yahoo(symbol)
        for symbol in yahoo_symbols
    }

    coinbase = probe_coinbase_usdt_usd()

    evidence = {
        "generated_at_utc": generated_at,
        "purpose": (
            "Phase 07 market-session and FX "
            "source research only"
        ),
        "execution_changed": False,
        "nbp": {
            code: {
                "request": {
                    "ok": result["ok"],
                    "status_code": result[
                        "status_code"
                    ],
                    "error": result["error"],
                },
                "summary": nbp_summary(
                    result
                ),
            }
            for code, result in nbp.items()
        },
        "yahoo": {
            symbol: {
                "ok": result["ok"],
                "status_code": result[
                    "status_code"
                ],
                "error": result["error"],
                "summary": result.get(
                    "summary"
                ),
            }
            for symbol, result in yahoo.items()
        },
        "coinbase_usdt_usd": {
            "ok": coinbase["ok"],
            "status_code": coinbase[
                "status_code"
            ],
            "error": coinbase["error"],
            "summary": coinbase_summary(
                coinbase
            ),
        },
    }

    output = Path(
        "docs/evidence/"
        "PHASE07_SESSION_FX_PROBE_2026-09-16.json"
    )

    output.write_text(
        json.dumps(
            evidence,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
        newline="\n",
    )

    print()
    print("=" * 88)
    print("PHASE 07 - FX / SESSION SOURCE PROBE")
    print("=" * 88)

    print()
    print("NBP REFERENCE RATES")

    for code, result in nbp.items():
        summary = nbp_summary(result)

        print(
            f"{code:4} "
            f"status={'OK' if result['ok'] else 'ERROR':5} "
            f"effective="
            f"{summary.get('effectiveDate') if summary else None} "
            f"mid="
            f"{summary.get('mid') if summary else None}"
        )

    print()
    print("YAHOO SOURCE METADATA")

    for symbol, result in yahoo.items():
        summary = result.get(
            "summary"
        ) or {}

        print(
            f"{symbol:10} "
            f"status={'OK' if result['ok'] else 'ERROR':5} "
            f"exchange={str(summary.get('exchangeName')):12} "
            f"tz={str(summary.get('exchangeTimezoneName')):22} "
            f"delay={str(summary.get('exchangeDataDelayedBy')):8} "
            f"price={summary.get('regularMarketPrice')}"
        )

    print()
    print("COINBASE USDT-USD")

    cb = coinbase_summary(
        coinbase
    ) or {}

    print(
        "status="
        f"{'OK' if coinbase['ok'] else 'ERROR'} "
        f"price={cb.get('price')} "
        f"bid={cb.get('bid')} "
        f"ask={cb.get('ask')} "
        f"time={cb.get('time')}"
    )

    print()
    print("EVIDENCE FILE:")
    print(output)

    required_failures = []

    for code, result in nbp.items():
        if not result["ok"]:
            required_failures.append(
                f"NBP:{code}"
            )

    for symbol in (
        "USDPLN=X",
        "EURPLN=X",
        "EURUSD=X",
        "AAPL",
        "GC=F",
        "CL=F",
    ):
        if not yahoo[symbol]["ok"]:
            required_failures.append(
                f"YAHOO:{symbol}"
            )

    if not coinbase["ok"]:
        required_failures.append(
            "COINBASE:USDT-USD"
        )

    print()
    print(
        "FAILED SOURCES:",
        required_failures or "NONE",
    )

    if required_failures:
        print(
            "RESEARCH STATUS: INCOMPLETE"
        )
        return 2

    print(
        "RESEARCH STATUS: GREEN"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
