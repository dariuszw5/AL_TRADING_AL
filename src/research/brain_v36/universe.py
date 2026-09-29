"""Versioned, catalog-wide research universe. Does not change production routing.

All supported, all fixed research markets, plus a frozen current-scanner
dynamic-USDT snapshot. Static fallback preserves coverage on older local
assets.py versions; unseen dynamic symbols MUST come from the API snapshot.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from collections import Counter
from typing import Iterable

from src.data import assets
from .costs import _research_asset

FIXED_BY_CLASS = {
    "crypto": ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"),
    "equity": ("AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "JPM", "XOM"),
    "etf": ("SPY", "QQQ", "IWM", "DIA", "XLK", "XLF"),
    "forex": ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"),
    "index": ("SP500_INDEX", "NASDAQ100_INDEX", "DOW30_INDEX", "RUSSELL2000_INDEX", "VIX_INDEX"),
    "commodity": (
        "GOLD_FUT_CONT", "WTI_FUT_CONT", "SILVER_FUT_CONT",
        "COPPER_FUT_CONT", "NATGAS_FUT_CONT", "BRENT_FUT_CONT",
    ),
}
YAHOO_PROVIDER_SYMBOL = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "JPY=X",
    "AUDUSD": "AUDUSD=X", "USDCAD": "CAD=X", "USDCHF": "CHF=X",
    "NZDUSD": "NZDUSD=X",
    "SP500_INDEX": "^GSPC", "NASDAQ100_INDEX": "^NDX", "DOW30_INDEX": "^DJI",
    "RUSSELL2000_INDEX": "^RUT", "VIX_INDEX": "^VIX",
    "GOLD_FUT_CONT": "GC=F", "WTI_FUT_CONT": "CL=F",
    "SILVER_FUT_CONT": "SI=F", "COPPER_FUT_CONT": "HG=F",
    "NATGAS_FUT_CONT": "NG=F", "BRENT_FUT_CONT": "BZ=F",
}
REFERENCE_TYPES = frozenset({
    "index_reference", "fx_spot_reference", "continuous_future_proxy",
})
_CRYPTO = re.compile(r"^[A-Z0-9]{1,20}USDT$")


@dataclass(frozen=True)
class ResearchInstrument:
    symbol: str
    asset_type: str
    instrument_type: str
    provider: str
    provider_symbol: str
    reference_only: bool
    origin: str

    def as_dict(self) -> dict:
        return asdict(self)


def universe(dynamic_symbols: Iterable[str] = ()) -> tuple[ResearchInstrument, ...]:
    catalog = {}
    for kind, symbols in FIXED_BY_CLASS.items():
        catalog.update({symbol: (kind, "fixed") for symbol in symbols})
    # Discover future additions directly, rather than hard-coding today's list.
    for item in (*getattr(assets, "SUPPORTED_ASSETS", ()),
                 *getattr(assets, "RESEARCH_ASSETS", ())):
        catalog[str(item.symbol).upper()] = (item.asset_type, "registered")
    fixed_names = frozenset(catalog)
    for raw in dynamic_symbols:
        symbol = str(raw).upper().strip()
        if symbol in catalog:
            continue
        if not _CRYPTO.fullmatch(symbol):
            raise ValueError(f"Unverified/unsupported dynamic crypto symbol: {symbol}")
        catalog[symbol] = ("crypto", "scanner_snapshot")

    out = []
    for symbol, (declared_class, origin) in sorted(catalog.items()):
        resolved = _research_asset(symbol)
        if resolved.asset_type != declared_class:
            raise ValueError(f"Asset classification mismatch: {symbol}")
        instrument_type = getattr(resolved, "instrument_type", None) or (
            "fx_spot_reference" if declared_class == "forex" else
            "index_reference" if declared_class == "index" else
            "continuous_future_proxy" if declared_class == "commodity" else
            "spot" if declared_class == "crypto" else declared_class
        )
        provider_symbol = (
            getattr(resolved, "provider_symbol", None)
            or YAHOO_PROVIDER_SYMBOL.get(symbol)
            or symbol
        )
        provider = getattr(resolved, "provider", "binance" if declared_class == "crypto" else "yahoo")
        if provider not in ("binance", "yahoo"):
            raise ValueError(f"Unsupported research data provider for {symbol}")
        out.append(ResearchInstrument(
            symbol=symbol, asset_type=declared_class,
            instrument_type=instrument_type,
            provider=provider, provider_symbol=provider_symbol,
            reference_only=instrument_type in REFERENCE_TYPES,
            origin="scanner_snapshot" if symbol not in fixed_names else origin,
        ))
    if len({asset.symbol for asset in out}) != len(out):
        raise AssertionError("Duplicate research universe symbols")
    if not set(FIXED_BY_CLASS).issubset({asset.asset_type for asset in out}):
        raise AssertionError("Incomplete multi-market research universe")
    return tuple(out)


def live_crypto_symbols(ai: dict, research: dict | None = None) -> tuple[str, ...]:
    """Extract only dynamic symbols the real scanner exposed; no synthetic tickers."""
    rows = list(ai.get("ranking") or [])
    if research:
        rows += list(research.get("opportunities") or [])
    symbols = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or "").upper().strip()
        if _CRYPTO.fullmatch(symbol):
            symbols.add(symbol)
    return tuple(sorted(symbols))


def class_coverage(instruments: Iterable[ResearchInstrument]) -> dict[str, int]:
    counts = Counter(asset.asset_type for asset in instruments)
    return {kind: counts.get(kind, 0) for kind in FIXED_BY_CLASS}
