"""Explicit, auditable assumptions, not a claim of observed broker spreads.

The price candles are midpoint/reference OHLC. Subtract one round-trip spread
plus per-side commissions and slippage. Never silently assume zero costs.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping

from src.data.assets import get_asset


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
            source=str(value["source"]),
        )


def cost_for_symbol(symbol: str, profiles: Mapping[str, Mapping]) -> tuple[CostProfile, dict]:
    asset = get_asset(symbol, allow_dynamic_binance=True)
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
