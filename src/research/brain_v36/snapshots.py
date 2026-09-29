"""Read-only real-provider OHLC acquisition into immutable research snapshots.

Source timestamps are real Binance/Yahoo candle OPEN times (UTC ms).
Never fills missing session bars and never retains an unfinished candle.
No production account/data-live/state imports. Network is used ONLY on
explicit invocation by the user of the multi-market research script.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from time import time
from urllib.parse import quote

import requests

from src.data.candle import Candle
from .engine import MINUTE_MS, contiguous, validate_history
from .universe import ResearchInstrument

BINANCE = "https://data-api.binance.vision/api/v3/klines"
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart"


def _get(session, url: str, *, params: dict):
    response = session.get(
        url, params=params, timeout=25,
        headers={"User-Agent": "AL-Trading-v36-research-only/1.0"},
    )
    response.raise_for_status()
    return response.json()


def real_candles(
    asset: ResearchInstrument, *, bar_minutes: int, limit: int,
    as_of_ms: int, session=requests,
) -> list[Candle]:
    """Download OHLC, retaining only COMPLETE bars as at one frozen cutoff."""
    if bar_minutes not in (1, 5):
        raise ValueError("Provider snapshots support explicit 1m or 5m only")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 100 <= limit <= 5000:
        raise ValueError("Historical candle limit must be 100..5000")
    bar_ms = bar_minutes * MINUTE_MS
    bars = []
    if asset.provider == "binance":
        end_time = as_of_ms - 1
        remaining = limit
        while remaining > 0:
            size = min(1000, remaining)
            raw = _get(session, BINANCE, params={
                "symbol": asset.provider_symbol,
                "interval": f"{bar_minutes}m", "limit": size,
                "endTime": end_time,
            })
            if not isinstance(raw, list) or not raw:
                break
            block = [Candle(
                timestamp=int(row[0]), open=float(row[1]),
                high=float(row[2]), low=float(row[3]),
                close=float(row[4]), volume=float(row[5]),
            ) for row in raw]
            bars = block + bars
            if block[0].timestamp >= end_time:
                raise ValueError(f"Non-backward historical pagination for {asset.symbol}")
            end_time = block[0].timestamp - 1
            remaining -= len(block)
            if len(block) < size:
                break
    elif asset.provider == "yahoo":
        data = _get(
            session, YAHOO + "/" + quote(asset.provider_symbol, safe=""),
            params={
                "range": "5d" if bar_minutes == 1 else "1mo",
                "interval": f"{bar_minutes}m",
                "includePrePost": "false", "events": "div,splits",
            },
        )
        chart = data.get("chart") or {}
        result = chart.get("result") or []
        if not result:
            raise ValueError(f"Yahoo returned no OHLC for {asset.symbol}: {chart.get('error')}")
        frame = result[0]
        ts = frame.get("timestamp") or []
        quotes = (frame.get("indicators") or {}).get("quote") or []
        if not quotes:
            raise ValueError(f"Yahoo returned no quote rows for {asset.symbol}")
        q = quotes[0]
        for i, t in enumerate(ts):
            values = []
            for key in ("open", "high", "low", "close"):
                column = q.get(key) or []
                values.append(column[i] if i < len(column) else None)
            if any(v is None for v in values):
                continue
            volume = q.get("volume") or []
            bars.append(Candle(
                timestamp=int(t) * 1000,
                open=float(values[0]), high=float(values[1]),
                low=float(values[2]), close=float(values[3]),
                volume=float((volume[i] if i < len(volume) else None) or 0),
            ))
        bars = bars[-limit:]
    else:
        raise ValueError(f"Unsupported data provider: {asset.provider}")
    bars = [c for c in bars if c.timestamp + bar_ms <= as_of_ms]
    return list(validate_history(bars, as_of_ms=as_of_ms, bar_minutes=bar_minutes))


def snapshot_record(
    asset: ResearchInstrument, candles: list[Candle], *,
    path: Path, bar_minutes: int, as_of_ms: int,
) -> dict:
    """Save one new frozen research file; never overwrite prior snapshots."""
    if path.exists():
        raise FileExistsError(f"Research snapshot exists, refusing overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        [asdict(c) for c in candles], ensure_ascii=False,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    with path.open("xb") as file:
        file.write(payload)
    gaps = sum(
        candles[i].timestamp - candles[i - 1].timestamp
        != bar_minutes * MINUTE_MS
        for i in range(1, len(candles))
    )
    return {
        **asset.as_dict(),
        "status": "FROZEN",
        "path": str(path.resolve()),
        "sha256": sha256(payload).hexdigest(),
        "count": len(candles),
        "first_timestamp": candles[0].timestamp,
        "last_timestamp": candles[-1].timestamp,
        "session_gaps": gaps,
        "bar_minutes": bar_minutes,
        "as_of_ms": as_of_ms,
        "data_origin": "REAL_PROVIDER_REFERENCE_OHLC_NOT_EXECUTABLE_BID_ASK",
    }


def load_snapshot(entry: dict, *, base: Path) -> list[Candle]:
    root = base.resolve()
    path = Path(entry["path"]).resolve()
    if not path.is_relative_to(root) or path.suffix.lower() != ".json":
        raise ValueError("Only independent research snapshot JSON files are allowed")
    content = path.read_bytes()
    if sha256(content).hexdigest() != entry["sha256"]:
        raise ValueError("Frozen research snapshot checksum mismatch")
    raw = json.loads(content.decode("utf-8"))
    candles = [Candle(
        timestamp=int(item["timestamp"]),
        open=float(item["open"]), high=float(item["high"]),
        low=float(item["low"]), close=float(item["close"]),
        volume=float(item["volume"]),
    ) for item in raw]
    validate_history(
        candles, as_of_ms=int(entry["as_of_ms"]),
        bar_minutes=int(entry["bar_minutes"]),
    )
    if len(candles) != entry["count"]:
        raise ValueError("Frozen research snapshot length mismatch")
    return candles
