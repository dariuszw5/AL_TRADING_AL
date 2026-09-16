from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import monotonic as system_monotonic
from typing import Protocol


def ensure_utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            "datetime must be timezone-aware"
        )

    return value.astimezone(timezone.utc)


class Clock(Protocol):

    def now(self) -> datetime:
        ...

    def monotonic(self) -> float:
        ...


class SystemClock:

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        return system_monotonic()


@dataclass
class FixedClock:
    current: datetime
    monotonic_value: float = 0.0

    def __post_init__(self):
        self.current = ensure_utc_aware(
            self.current
        )

    def now(self) -> datetime:
        return self.current

    def monotonic(self) -> float:
        return float(self.monotonic_value)

    def advance(self, seconds: float):
        if seconds < 0:
            raise ValueError(
                "Clock cannot move backwards"
            )

        self.current += timedelta(
            seconds=seconds
        )

        self.monotonic_value += seconds
