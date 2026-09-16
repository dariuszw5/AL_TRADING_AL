from __future__ import annotations

from dataclasses import dataclass
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
    FxPath,
    FxQuote,
    FxSourceQuality,
)


FX_CONVERSION_COST_LIMITATION = (
    "KNOWN_LIMITATION: "
    "FX_CONVERSION_COST_NOT_MODELLED"
)

DAILY_REFERENCE_TIME_LIMITATION = (
    "KNOWN_LIMITATION: "
    "DAILY_REFERENCE_INTRADAY_PUBLICATION_TIME_UNAVAILABLE"
)


class RealizedFxBookingError(
    ValueError
):
    pass


def _currency(
    value,
):
    result = (
        str(value)
        .strip()
        .upper()
    )

    if not result:
        raise RealizedFxBookingError(
            "native_currency is required"
        )

    return result


def _required_text(
    value,
    field_name,
):
    result = str(
        value
    ).strip()

    if not result:
        raise RealizedFxBookingError(
            f"{field_name} is required"
        )

    return result


def _aware_utc(
    value,
    field_name,
):
    if value.tzinfo is None:
        raise RealizedFxBookingError(
            f"{field_name} must be timezone-aware"
        )

    return value.astimezone(
        timezone.utc
    )


@dataclass(frozen=True)
class RealizedFxLegSnapshot:
    pair: str
    rate: float
    provider: str
    provider_timestamp: datetime | None
    source_quality: str
    bid: float | None
    ask: float | None
    table: str | None
    effective_date: date | None
    labels: tuple[str, ...]


@dataclass(frozen=True)
class RealizedPnlBooking:
    """
    Immutable realized-PnL FX snapshot.

    This object intentionally has no revalue method.
    Historical pnl_pln is part of the booked record.
    """

    booking_id: str
    asset_id: str
    close_execution_id: str

    closed_at: datetime
    booked_at: datetime

    native_pnl: float
    native_currency: str

    pnl_pln: float

    fx_pair: str
    fx_path: str
    fx_rate: float

    fx_provider: str | None
    fx_timestamp: datetime | None

    fx_table: str | None
    fx_effective_date: date | None

    fx_legs: tuple[
        RealizedFxLegSnapshot,
        ...
    ]

    limitations: tuple[str, ...]


class RealizedFxBooker:
    """
    Build an immutable realized FX booking from
    explicitly supplied FX evidence.

    Important:
    this class does NOT select an NBP table and does
    NOT fetch market data.

    Source selection remains a separate policy layer.
    """

    def __init__(
        self,
        *,
        clock: Clock | None = None,
    ):
        self.clock = (
            clock
            or SystemClock()
        )

    @staticmethod
    def _path_for(
        source,
    ):
        if source == "PLN":
            return FxPath(
                ("PLN",)
            )

        if source == "USD":
            return FxPath(
                (
                    "USD",
                    "PLN",
                )
            )

        if source == "EUR":
            return FxPath(
                (
                    "EUR",
                    "PLN",
                )
            )

        if source == "USDT":
            return FxPath(
                (
                    "USDT",
                    "USD",
                    "PLN",
                )
            )

        raise RealizedFxBookingError(
            "NO_REALIZED_FX_PATH:"
            f"{source}→PLN"
        )

    @staticmethod
    def _pairs_for(
        path,
    ):
        currencies = path.currencies

        return tuple(
            currencies[index]
            + currencies[index + 1]
            for index
            in range(
                len(currencies) - 1
            )
        )

    @staticmethod
    def _quote_map(
        quotes,
    ):
        result = {}

        for quote in quotes:
            pair = quote.pair

            if pair in result:
                raise RealizedFxBookingError(
                    "DUPLICATE_FX_LEG:"
                    + pair
                )

            result[pair] = quote

        return result

    @staticmethod
    def _validate_quote(
        quote,
        *,
        closed_at,
        booked_at,
    ):
        if quote.observed_at > booked_at:
            raise RealizedFxBookingError(
                "FX_OBSERVATION_AFTER_BOOKING:"
                + quote.pair
            )

        if (
            quote.source_quality
            is FxSourceQuality.DAILY_REFERENCE
        ):
            if (
                not quote.table
                or quote.effective_date is None
            ):
                raise RealizedFxBookingError(
                    "DAILY_REFERENCE_METADATA_INCOMPLETE:"
                    + quote.pair
                )

            if (
                quote.effective_date
                > closed_at.date()
            ):
                raise RealizedFxBookingError(
                    "FX_EFFECTIVE_DATE_AFTER_CLOSE:"
                    + quote.pair
                )

            if (
                quote.provider_timestamp
                is not None
                and quote.provider_timestamp
                > closed_at
            ):
                raise RealizedFxBookingError(
                    "FX_TIMESTAMP_AFTER_CLOSE:"
                    + quote.pair
                )

            return

        if quote.provider_timestamp is None:
            raise RealizedFxBookingError(
                "FX_TIMESTAMP_REQUIRED:"
                + quote.pair
            )

        if (
            quote.provider_timestamp
            > closed_at
        ):
            raise RealizedFxBookingError(
                "FX_TIMESTAMP_AFTER_CLOSE:"
                + quote.pair
            )

    @staticmethod
    def _snapshot(
        quote,
    ):
        return RealizedFxLegSnapshot(
            pair=quote.pair,
            rate=float(
                quote.rate
            ),
            provider=quote.provider,
            provider_timestamp=(
                quote.provider_timestamp
            ),
            source_quality=(
                quote.source_quality.value
            ),
            bid=quote.bid,
            ask=quote.ask,
            table=quote.table,
            effective_date=(
                quote.effective_date
            ),
            labels=tuple(
                quote.labels
            ),
        )

    def book(
        self,
        *,
        booking_id,
        asset_id,
        close_execution_id,
        closed_at,
        native_pnl,
        native_currency,
        quotes,
    ):
        booking_id = _required_text(
            booking_id,
            "booking_id",
        )

        asset_id = _required_text(
            asset_id,
            "asset_id",
        )

        close_execution_id = (
            _required_text(
                close_execution_id,
                "close_execution_id",
            )
        )

        source = _currency(
            native_currency
        )

        closed_at = _aware_utc(
            closed_at,
            "closed_at",
        )

        booked_at = _aware_utc(
            self.clock.now(),
            "booked_at",
        )

        if booked_at < closed_at:
            raise RealizedFxBookingError(
                "BOOKING_BEFORE_CLOSE"
            )

        native_pnl = float(
            native_pnl
        )

        path = self._path_for(
            source
        )

        if source == "PLN":
            return RealizedPnlBooking(
                booking_id=booking_id,
                asset_id=asset_id,
                close_execution_id=(
                    close_execution_id
                ),
                closed_at=closed_at,
                booked_at=booked_at,
                native_pnl=native_pnl,
                native_currency="PLN",
                pnl_pln=native_pnl,
                fx_pair="PLNPLN",
                fx_path="PLN",
                fx_rate=1.0,
                fx_provider=None,
                fx_timestamp=None,
                fx_table=None,
                fx_effective_date=None,
                fx_legs=(),
                limitations=(),
            )

        quote_map = self._quote_map(
            quotes
        )

        selected = []

        for pair in self._pairs_for(
            path
        ):
            quote = quote_map.get(
                pair
            )

            if quote is None:
                raise RealizedFxBookingError(
                    "MISSING_FX_LEG:"
                    + pair
                )

            self._validate_quote(
                quote,
                closed_at=closed_at,
                booked_at=booked_at,
            )

            selected.append(
                quote
            )

        fx_rate = 1.0

        for quote in selected:
            fx_rate *= float(
                quote.rate
            )

        pnl_pln = (
            native_pnl
            * fx_rate
        )

        snapshots = tuple(
            self._snapshot(
                quote
            )
            for quote in selected
        )

        providers = "|".join(
            quote.provider
            for quote in selected
        )

        # A singular timestamp is only truthful
        # for a singular conversion leg.
        fx_timestamp = (
            selected[0].provider_timestamp
            if len(selected) == 1
            else None
        )

        daily_reference_legs = [
            quote
            for quote in selected
            if (
                quote.source_quality
                is FxSourceQuality.DAILY_REFERENCE
            )
        ]

        fx_table = None
        fx_effective_date = None

        if len(
            daily_reference_legs
        ) == 1:
            daily = (
                daily_reference_legs[0]
            )

            fx_table = daily.table
            fx_effective_date = (
                daily.effective_date
            )

        limitations = [
            FX_CONVERSION_COST_LIMITATION,
        ]

        if any(
            quote.source_quality
            is FxSourceQuality.DAILY_REFERENCE
            and quote.provider_timestamp is None
            for quote in selected
        ):
            limitations.append(
                DAILY_REFERENCE_TIME_LIMITATION
            )

        return RealizedPnlBooking(
            booking_id=booking_id,
            asset_id=asset_id,
            close_execution_id=(
                close_execution_id
            ),
            closed_at=closed_at,
            booked_at=booked_at,
            native_pnl=native_pnl,
            native_currency=source,
            pnl_pln=pnl_pln,
            fx_pair=(
                source
                + "PLN"
            ),
            fx_path=path.text,
            fx_rate=fx_rate,
            fx_provider=providers,
            fx_timestamp=fx_timestamp,
            fx_table=fx_table,
            fx_effective_date=(
                fx_effective_date
            ),
            fx_legs=snapshots,
            limitations=tuple(
                limitations
            ),
        )
