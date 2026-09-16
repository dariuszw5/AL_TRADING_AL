from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import (
    date,
    datetime,
    time,
    timedelta,
    timezone,
)
from enum import Enum
from pathlib import Path

from src.data.assets import get_asset


class SessionState(str, Enum):
    OPEN = "OPEN"
    PRE_MARKET = "PRE_MARKET"
    REGULAR = "REGULAR"
    AFTER_HOURS = "AFTER_HOURS"
    MAINTENANCE = "MAINTENANCE"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


class SessionQuality(str, Enum):
    EXCHANGE_CALENDAR = "EXCHANGE_CALENDAR"
    APPROXIMATED = "APPROXIMATED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class MarketSessionSnapshot:
    asset_id: str
    session_id: str
    state: SessionState
    session_quality: SessionQuality
    observed_at: datetime
    timezone_name: str
    local_time: datetime
    reason: str
    calendar_version: str | None = None

    def __post_init__(self):
        if self.observed_at.tzinfo is None:
            raise ValueError(
                "observed_at must be timezone-aware"
            )

        if self.local_time.tzinfo is None:
            raise ValueError(
                "local_time must be timezone-aware"
            )

        if self.observed_at.utcoffset() != timezone.utc.utcoffset(
            self.observed_at
        ):
            raise ValueError(
                "observed_at must be UTC"
            )

    @property
    def is_open(self):
        return self.state in {
            SessionState.OPEN,
            SessionState.PRE_MARKET,
            SessionState.REGULAR,
            SessionState.AFTER_HOURS,
        }


class MarketSessionService:

    def __init__(
        self,
        calendar_path=None,
    ):
        if calendar_path is None:
            calendar_path = (
                Path(__file__)
                .resolve()
                .parents[2]
                / "config"
                / "market_calendars"
                / "market_calendars_v1.json"
            )

        self.calendar_path = Path(
            calendar_path
        )

        with self.calendar_path.open(
            "r",
            encoding="utf-8-sig",
        ) as file:
            self.calendar = json.load(
                file
            )

        self.calendar_version = str(
            self.calendar["version"]
        )

        self._validate_calendar()

    def _validate_calendar(self):
        if not self.calendar_version:
            raise ValueError(
                "Calendar version is required"
            )

        nasdaq = self.calendar.get(
            "nasdaq_us_equities"
        )

        cme = self.calendar.get(
            "cme_nymex_comex_proxy_2026"
        )

        if not nasdaq or not cme:
            raise ValueError(
                "Required calendar sections missing"
            )

        for section in (
            nasdaq,
            cme,
        ):
            start = date.fromisoformat(
                section["coverage_start"]
            )

            end = date.fromisoformat(
                section["coverage_end"]
            )

            if end < start:
                raise ValueError(
                    "Calendar coverage is invalid"
                )

        for value in nasdaq[
            "full_closures"
        ]:
            date.fromisoformat(value)

        for value in nasdaq[
            "early_closes"
        ]:
            date.fromisoformat(value)

        for value in cme[
            "special_schedule_dates"
        ]:
            date.fromisoformat(value)

    @staticmethod
    def _as_utc(
        at: datetime,
    ):
        if at.tzinfo is None:
            raise ValueError(
                "Market session datetime "
                "must be timezone-aware"
            )

        return at.astimezone(
            timezone.utc
        )

    @staticmethod
    def _parse_time(
        value: str,
    ):
        return time.fromisoformat(
            value
        )

    @staticmethod
    def _first_sunday(
        year: int,
        month: int,
    ):
        current = date(
            year,
            month,
            1,
        )

        days_until_sunday = (
            6 - current.weekday()
        ) % 7

        return current + timedelta(
            days=days_until_sunday
        )

    @classmethod
    def _second_sunday(
        cls,
        year: int,
        month: int,
    ):
        return (
            cls._first_sunday(
                year,
                month,
            )
            + timedelta(days=7)
        )

    @classmethod
    def _us_local_time(
        cls,
        observed_at: datetime,
        timezone_name: str,
    ):
        if timezone_name == "America/New_York":
            standard_offset = -5
            daylight_offset = -4
            dst_start_utc_hour = 7
            dst_end_utc_hour = 6

        elif timezone_name == "America/Chicago":
            standard_offset = -6
            daylight_offset = -5
            dst_start_utc_hour = 8
            dst_end_utc_hour = 7

        else:
            raise ValueError(
                "Unsupported deterministic timezone: "
                f"{timezone_name}"
            )

        year = observed_at.year

        dst_start_date = cls._second_sunday(
            year,
            3,
        )

        dst_end_date = cls._first_sunday(
            year,
            11,
        )

        dst_start = datetime(
            year,
            3,
            dst_start_date.day,
            dst_start_utc_hour,
            0,
            tzinfo=timezone.utc,
        )

        dst_end = datetime(
            year,
            11,
            dst_end_date.day,
            dst_end_utc_hour,
            0,
            tzinfo=timezone.utc,
        )

        offset_hours = (
            daylight_offset
            if dst_start <= observed_at < dst_end
            else standard_offset
        )

        target_timezone = timezone(
            timedelta(
                hours=offset_hours
            ),
            name=timezone_name,
        )

        return observed_at.astimezone(
            target_timezone
        )

    @staticmethod
    def _in_coverage(
        local_date: date,
        section,
    ):
        start = date.fromisoformat(
            section["coverage_start"]
        )

        end = date.fromisoformat(
            section["coverage_end"]
        )

        return (
            start
            <= local_date
            <= end
        )

    def get_session(
        self,
        asset_id: str,
        at: datetime,
    ):
        observed_at = self._as_utc(
            at
        )

        asset = get_asset(
            asset_id
        )

        session_id = str(
            asset.session_id
        )

        if session_id == "CRYPTO_24_7":
            return self._crypto(
                asset.asset_id,
                session_id,
                observed_at,
            )

        if (
            session_id
            == "NASDAQ_REGULAR_REFERENCE"
        ):
            return self._nasdaq(
                asset.asset_id,
                session_id,
                observed_at,
            )

        if (
            session_id
            == "FX_24_5_REFERENCE"
        ):
            return self._fx(
                asset.asset_id,
                session_id,
                observed_at,
            )

        if (
            session_id
            == "CME_GLOBEX_REFERENCE"
        ):
            return self._cme_proxy(
                asset.asset_id,
                session_id,
                observed_at,
            )

        return MarketSessionSnapshot(
            asset_id=asset.asset_id,
            session_id=session_id,
            state=SessionState.UNKNOWN,
            session_quality=(
                SessionQuality.UNKNOWN
            ),
            observed_at=observed_at,
            timezone_name="UTC",
            local_time=observed_at,
            reason="UNKNOWN_SESSION_ID",
            calendar_version=(
                self.calendar_version
            ),
        )

    def _crypto(
        self,
        asset_id,
        session_id,
        observed_at,
    ):
        return MarketSessionSnapshot(
            asset_id=asset_id,
            session_id=session_id,
            state=SessionState.OPEN,
            session_quality=(
                SessionQuality.EXCHANGE_CALENDAR
            ),
            observed_at=observed_at,
            timezone_name="UTC",
            local_time=observed_at,
            reason="CRYPTO_24_7",
            calendar_version=(
                self.calendar_version
            ),
        )

    def _nasdaq(
        self,
        asset_id,
        session_id,
        observed_at,
    ):
        section = self.calendar[
            "nasdaq_us_equities"
        ]

        timezone_name = section[
            "timezone"
        ]

        local = self._us_local_time(
            observed_at,
            timezone_name,
        )

        local_date = local.date()

        if not self._in_coverage(
            local_date,
            section,
        ):
            return MarketSessionSnapshot(
                asset_id=asset_id,
                session_id=session_id,
                state=SessionState.UNKNOWN,
                session_quality=(
                    SessionQuality.UNKNOWN
                ),
                observed_at=observed_at,
                timezone_name=timezone_name,
                local_time=local,
                reason="CALENDAR_OUT_OF_COVERAGE",
                calendar_version=(
                    self.calendar_version
                ),
            )

        day = local_date.isoformat()

        if day in set(
            section["full_closures"]
        ):
            return MarketSessionSnapshot(
                asset_id=asset_id,
                session_id=session_id,
                state=SessionState.CLOSED,
                session_quality=(
                    SessionQuality.EXCHANGE_CALENDAR
                ),
                observed_at=observed_at,
                timezone_name=timezone_name,
                local_time=local,
                reason="EXCHANGE_HOLIDAY",
                calendar_version=(
                    self.calendar_version
                ),
            )

        if local.weekday() >= 5:
            return MarketSessionSnapshot(
                asset_id=asset_id,
                session_id=session_id,
                state=SessionState.CLOSED,
                session_quality=(
                    SessionQuality.EXCHANGE_CALENDAR
                ),
                observed_at=observed_at,
                timezone_name=timezone_name,
                local_time=local,
                reason="WEEKEND",
                calendar_version=(
                    self.calendar_version
                ),
            )

        current = local.time().replace(
            tzinfo=None
        )

        pre_open = self._parse_time(
            section["pre_market_open"]
        )

        regular_open = self._parse_time(
            section["regular_open"]
        )

        normal_close = self._parse_time(
            section["regular_close"]
        )

        after_close = self._parse_time(
            section["after_hours_close"]
        )

        early_close_value = (
            section["early_closes"]
            .get(day)
        )

        if early_close_value:
            early_close = self._parse_time(
                early_close_value
            )

            if (
                pre_open
                <= current
                < regular_open
            ):
                state = (
                    SessionState.PRE_MARKET
                )
                quality = (
                    SessionQuality.EXCHANGE_CALENDAR
                )
                reason = "PRE_MARKET"

            elif (
                regular_open
                <= current
                < early_close
            ):
                state = (
                    SessionState.REGULAR
                )
                quality = (
                    SessionQuality.EXCHANGE_CALENDAR
                )
                reason = "EARLY_CLOSE_REGULAR"

            elif current < pre_open:
                state = SessionState.CLOSED
                quality = (
                    SessionQuality.EXCHANGE_CALENDAR
                )
                reason = "BEFORE_PRE_MARKET"

            else:
                state = SessionState.UNKNOWN
                quality = (
                    SessionQuality.UNKNOWN
                )
                reason = (
                    "EARLY_CLOSE_EXTENDED_"
                    "HOURS_UNVERIFIED"
                )

            return MarketSessionSnapshot(
                asset_id=asset_id,
                session_id=session_id,
                state=state,
                session_quality=quality,
                observed_at=observed_at,
                timezone_name=timezone_name,
                local_time=local,
                reason=reason,
                calendar_version=(
                    self.calendar_version
                ),
            )

        if current < pre_open:
            state = SessionState.CLOSED
            reason = "BEFORE_PRE_MARKET"

        elif current < regular_open:
            state = SessionState.PRE_MARKET
            reason = "PRE_MARKET"

        elif current < normal_close:
            state = SessionState.REGULAR
            reason = "REGULAR"

        elif current < after_close:
            state = (
                SessionState.AFTER_HOURS
            )
            reason = "AFTER_HOURS"

        else:
            state = SessionState.CLOSED
            reason = "AFTER_SESSION"

        return MarketSessionSnapshot(
            asset_id=asset_id,
            session_id=session_id,
            state=state,
            session_quality=(
                SessionQuality.EXCHANGE_CALENDAR
            ),
            observed_at=observed_at,
            timezone_name=timezone_name,
            local_time=local,
            reason=reason,
            calendar_version=(
                self.calendar_version
            ),
        )

    def _fx(
        self,
        asset_id,
        session_id,
        observed_at,
    ):
        timezone_name = (
            "America/New_York"
        )

        local = self._us_local_time(
            observed_at,
            timezone_name,
        )

        local_date = local.date()
        current = local.time().replace(
            tzinfo=None
        )

        if (
            local_date.month,
            local_date.day,
        ) in {
            (1, 1),
            (12, 25),
        }:
            state = SessionState.CLOSED
            reason = "FX_REFERENCE_HOLIDAY"

        elif local.weekday() == 5:
            state = SessionState.CLOSED
            reason = "FX_WEEKEND"

        elif local.weekday() == 6:
            if current >= time(
                17,
                0,
            ):
                state = SessionState.OPEN
                reason = "FX_WEEK_OPEN"
            else:
                state = SessionState.CLOSED
                reason = "FX_WEEKEND"

        elif local.weekday() == 4:
            if current < time(
                17,
                0,
            ):
                state = SessionState.OPEN
                reason = "FX_WEEK_OPEN"
            else:
                state = SessionState.CLOSED
                reason = "FX_WEEK_CLOSED"

        else:
            state = SessionState.OPEN
            reason = "FX_WEEK_OPEN"

        return MarketSessionSnapshot(
            asset_id=asset_id,
            session_id=session_id,
            state=state,
            session_quality=(
                SessionQuality.APPROXIMATED
            ),
            observed_at=observed_at,
            timezone_name=timezone_name,
            local_time=local,
            reason=reason,
            calendar_version=(
                self.calendar_version
            ),
        )

    def _cme_proxy(
        self,
        asset_id,
        session_id,
        observed_at,
    ):
        section = self.calendar[
            "cme_nymex_comex_proxy_2026"
        ]

        timezone_name = section[
            "timezone"
        ]

        local = self._us_local_time(
            observed_at,
            timezone_name,
        )

        local_date = local.date()

        if not self._in_coverage(
            local_date,
            section,
        ):
            return MarketSessionSnapshot(
                asset_id=asset_id,
                session_id=session_id,
                state=SessionState.UNKNOWN,
                session_quality=(
                    SessionQuality.UNKNOWN
                ),
                observed_at=observed_at,
                timezone_name=timezone_name,
                local_time=local,
                reason="CME_CALENDAR_OUT_OF_COVERAGE",
                calendar_version=(
                    self.calendar_version
                ),
            )

        if (
            local_date.isoformat()
            in set(
                section[
                    "special_schedule_dates"
                ]
            )
        ):
            return MarketSessionSnapshot(
                asset_id=asset_id,
                session_id=session_id,
                state=SessionState.UNKNOWN,
                session_quality=(
                    SessionQuality.UNKNOWN
                ),
                observed_at=observed_at,
                timezone_name=timezone_name,
                local_time=local,
                reason=(
                    "CME_SPECIAL_HOURS_"
                    "NOT_PRODUCT_VERIFIED"
                ),
                calendar_version=(
                    self.calendar_version
                ),
            )

        current = local.time().replace(
            tzinfo=None
        )

        weekday = local.weekday()

        daily_close = self._parse_time(
            section["daily_close"]
        )

        weekly_open = self._parse_time(
            section["weekly_open"]
        )

        if weekday == 5:
            state = SessionState.CLOSED
            reason = "CME_WEEKEND"

        elif weekday == 6:
            if current >= weekly_open:
                state = SessionState.OPEN
                reason = "CME_WEEK_OPEN"
            else:
                state = SessionState.CLOSED
                reason = "CME_WEEKEND"

        elif weekday == 4:
            if current < daily_close:
                state = SessionState.OPEN
                reason = "CME_OPEN"
            else:
                state = SessionState.CLOSED
                reason = "CME_WEEK_CLOSE"

        else:
            if (
                daily_close
                <= current
                < weekly_open
            ):
                state = (
                    SessionState.MAINTENANCE
                )
                reason = (
                    "CME_DAILY_MAINTENANCE"
                )
            else:
                state = SessionState.OPEN
                reason = "CME_OPEN"

        return MarketSessionSnapshot(
            asset_id=asset_id,
            session_id=session_id,
            state=state,
            session_quality=(
                SessionQuality.APPROXIMATED
            ),
            observed_at=observed_at,
            timezone_name=timezone_name,
            local_time=local,
            reason=reason,
            calendar_version=(
                self.calendar_version
            ),
        )
