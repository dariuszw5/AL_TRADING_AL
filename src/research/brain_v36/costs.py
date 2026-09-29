"""Explicit, auditable assumptions, not a claim of observed broker spreads.

The price candles are midpoint/reference OHLC. Subtract one round-trip spread
plus per-side commissions and slippage. Never silently assume zero costs.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import SimpleNamespace
from typing import Mapping
import re

from src.data import assets as asset_registry

# Research-only compatibility with older local asset registries. These are
# canonical symbols already defined in the newer project catalog; unfamiliar
# non-crypto symbols are deliberately rejected rather than guessed.
_LEGACY_RESEARCH = {
    **{symbol: ("equity", "equity", "yahoo") for symbol in
       ("AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "JPM", "XOM")},
    **{symbol: ("etf", "etf", "yahoo") for symbol in
       ("SPY", "QQQ", "IWM", "DIA", "XLK", "XLF")},
    **{symbol: ("forex", "fx_spot_reference", "yahoo") for symbol in
       ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD")},
    **{symbol: ("index", "index_reference", "yahoo") for symbol in
       ("SP500_INDEX", "NASDAQ100_INDEX", "DOW30_INDEX",
        "RUSSELL2000_INDEX", "VIX_INDEX")},
    **{symbol: ("commodity", "continuous_future_proxy", "yahoo") for symbol in
       ("GOLD_FUT_CONT", "WTI_FUT_CONT", "SILVER_FUT_CONT",
        "COPPER_FUT_CONT", "NATGAS_FUT_CONT", "BRENT_FUT_CONT")},
}


def _research_asset(symbol: str):
    """Resolve project metadata without requiring the newer get_asset keyword.

    The installed local asset registry may predate the feature branch. This
    adapter affects RESEARCH_ONLY reports, never production asset routing.
    """
    normalized = symbol.upper().strip()
    if not normalized:
        raise ValueError("Empty research asset symbol")
    try:
        asset = asset_registry.get_asset(normalized)
    except (KeyError, ValueError):
        asset = None
    if asset is None:
        research = getattr(asset_registry, "RESEARCH_ASSET_BY_SYMBOL", {})
        asset = research.get(normalized)
    if asset is not None:
        # Some older Windows copies expose get_asset(symbol) but omit the
        # newer instrument_type/provider_symbol dataclass fields. Normalize
        # ONLY the research metadata; never mutate production AssetSpec.
        canonical = str(asset.symbol).upper()
        asset_class = str(asset.asset_type)
        legacy = _LEGACY_RESEARCH.get(canonical)
        instrument = getattr(asset, "instrument_type", None)
        if not instrument or (instrument == "spot" and asset_class != "crypto"):
            instrument = legacy[1] if legacy else (
                "spot" if asset_class == "crypto" else asset_class
            )
        return SimpleNamespace(
            symbol=canonical,
            asset_type=asset_class,
            instrument_type=instrument,
            provider=getattr(asset, "provider", None) or (
                "binance" if asset_class == "crypto" else "yahoo"
            ),
            provider_symbol=getattr(asset, "provider_symbol", None),
        )
    if re.fullmatch(r"[A-Z0-9]{1,20}USDT", normalized):
        return SimpleNamespace(symbol=normalized, asset_type="crypto",
                               instrument_type="spot", provider="binance")
    if normalized in _LEGACY_RESEARCH:
        kind, instrument, provider = _LEGACY_RESEARCH[normalized]
        return SimpleNamespace(symbol=normalized, asset_type=kind,
                               instrument_type=instrument, provider=provider)
    raise ValueError(f"Unknown research asset: {normalized}")


@dataclass(frozen=True)
class CostProfile:
    commission_per_side: float
    spread_round_trip: float
    slippage_per_side: float
    source: str

    def __post_init__(self) -> None:
        for field in ("commission_per_side", "spread_round_trip", "slippage_per_side"):
            number = getattr(self, field)
            if isinstance(number, bool) or not isinstance(number, (int, float)):
                raise ValueError(f"{field}: numeric fraction required")
            if not isfinite(number) or number < 0:
                raise ValueError(f"{field}: finite non-negative fraction required")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("Specify the provenance of every cost assumption")
        if self.round_trip >= 1:
            raise ValueError("Combined cost is invalid")

    @property
    def round_trip(self) -> float:
        return (
            2 * self.commission_per_side
            + self.spread_round_trip
            + 2 * self.slippage_per_side
        )

    def net_fraction(self, entry_mid: float, exit_mid: float, side: str) -> float:
        if not isfinite(entry_mid) or not isfinite(exit_mid) or min(entry_mid, exit_mid) <= 0:
            raise ValueError("Invalid midpoint execution prices")
        if side not in {"LONG", "SHORT"}:
            raise ValueError("side must be LONG or SHORT")
        gross = (exit_mid / entry_mid - 1) * (1 if side == "LONG" else -1)
        return gross - self.round_trip

    @classmethod
    def from_mapping(cls, value: Mapping) -> "CostProfile":
        # Missing fields fail closed; do not synthesize zero spread/slippage.
        return cls(
            commission_per_side=float(value["commission_per_side"]),
            spread_round_trip=float(value["spread_round_trip"]),
            slippage_per_side=float(value["slippage_per_side"]),
            source=value["source"],
        )


def cost_for_symbol(symbol: str, profiles: Mapping[str, Mapping]) -> tuple[CostProfile, dict]:
    asset = _research_asset(symbol)
    raw = profiles.get(asset.symbol, profiles.get(asset.asset_type))
    if raw is None:
        raise ValueError(
            f"No cost model for {asset.symbol} ({asset.asset_type}); "
            "supply measured or explicitly labeled assumed fees/spread/slippage"
        )
    profile = CostProfile.from_mapping(raw)
    # Yahoo indices, FX references and continuous futures are not a broker's
    # executable instrument/quote; flag proxy status in every research row.
    proxy = asset.instrument_type in {
        "index_reference", "fx_spot_reference", "continuous_future_proxy"
    }
    return profile, {
        "symbol": asset.symbol,
        "asset_type": asset.asset_type,
        "instrument_type": asset.instrument_type,
        "provider": asset.provider,
        "reference_only": proxy,
    }
