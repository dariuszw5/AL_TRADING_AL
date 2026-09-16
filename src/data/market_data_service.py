from dataclasses import dataclass
from threading import Lock
from types import MappingProxyType

from src.core.clock import (
    Clock,
    SystemClock,
)
from src.data.market_data import (
    MarketSnapshot,
)


class CycleInProgressError(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class MarketDataCycleResult:
    snapshots: object
    errors: object
    duration_seconds: float
    timed_out: bool


class MarketDataService:

    def __init__(
        self,
        provider,
        *,
        clock: Clock | None = None,
        cycle_timeout_seconds: float = 30.0,
        stale_after_seconds: float = 120.0,
    ):
        if cycle_timeout_seconds <= 0.0:
            raise ValueError(
                "cycle_timeout_seconds must "
                "be positive"
            )

        if stale_after_seconds <= 0.0:
            raise ValueError(
                "stale_after_seconds must "
                "be positive"
            )

        self.provider = provider
        self.clock = clock or SystemClock()

        self.cycle_timeout_seconds = float(
            cycle_timeout_seconds
        )

        self.stale_after_seconds = float(
            stale_after_seconds
        )

        self._cycle_lock = Lock()

    def run_cycle(
        self,
        asset_ids,
    ) -> MarketDataCycleResult:
        if not self._cycle_lock.acquire(
            blocking=False
        ):
            raise CycleInProgressError(
                "Market-data cycle already "
                "in progress"
            )

        started = self.clock.monotonic()
        deadline = (
            started
            + self.cycle_timeout_seconds
        )

        snapshots = {}
        errors = {}
        timed_out = False

        asset_ids = tuple(asset_ids)

        try:
            for index, asset_id in enumerate(
                asset_ids
            ):
                if (
                    self.clock.monotonic()
                    >= deadline
                ):
                    timed_out = True

                    for remaining in asset_ids[
                        index:
                    ]:
                        errors[
                            remaining
                        ] = "CYCLE_TIMEOUT"

                    break

                try:
                    snapshot = (
                        self.provider
                        .get_market_snapshot(
                            asset_id,
                            stale_after_seconds=(
                                self.stale_after_seconds
                            ),
                            deadline_monotonic=(
                                deadline
                            ),
                        )
                    )

                    if not isinstance(
                        snapshot,
                        MarketSnapshot,
                    ):
                        raise TypeError(
                            "Provider returned "
                            "non-MarketSnapshot"
                        )

                    if (
                        self.clock.monotonic()
                        > deadline
                    ):
                        errors[
                            asset_id
                        ] = "CYCLE_TIMEOUT"

                        timed_out = True

                        for remaining in asset_ids[
                            index + 1:
                        ]:
                            errors[
                                remaining
                            ] = "CYCLE_TIMEOUT"

                        break

                    snapshots[
                        asset_id
                    ] = snapshot

                except Exception as exc:
                    errors[
                        asset_id
                    ] = (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )

            duration = max(
                0.0,
                self.clock.monotonic()
                - started,
            )

            return MarketDataCycleResult(
                snapshots=MappingProxyType(
                    dict(snapshots)
                ),
                errors=MappingProxyType(
                    dict(errors)
                ),
                duration_seconds=duration,
                timed_out=timed_out,
            )

        finally:
            self._cycle_lock.release()
