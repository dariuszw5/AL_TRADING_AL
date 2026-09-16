from __future__ import annotations

from concurrent.futures import (
    ThreadPoolExecutor,
    wait,
)
from threading import Lock
from types import MappingProxyType

from src.core.clock import Clock, SystemClock
from src.data.market_data import MarketSnapshot
from src.data.market_data_service import (
    CycleInProgressError,
    MarketDataCycleResult,
)


class ParallelMarketDataService:
    """
    REALISTIC_V2 market-data cycle with bounded
    parallelism.

    The Phase 06 MarketDataService remains untouched.
    """

    def __init__(
        self,
        provider,
        *,
        clock: Clock | None = None,
        cycle_timeout_seconds=20.0,
        stale_after_seconds=120.0,
        per_asset_timeout_seconds=8.0,
        max_workers=5,
    ):
        if cycle_timeout_seconds <= 0.0:
            raise ValueError(
                "cycle_timeout_seconds must be positive"
            )

        if stale_after_seconds <= 0.0:
            raise ValueError(
                "stale_after_seconds must be positive"
            )

        if per_asset_timeout_seconds <= 0.0:
            raise ValueError(
                "per_asset_timeout_seconds must be positive"
            )

        if int(max_workers) <= 0:
            raise ValueError(
                "max_workers must be positive"
            )

        self.provider = provider

        self.clock = (
            clock
            or SystemClock()
        )

        self.cycle_timeout_seconds = float(
            cycle_timeout_seconds
        )

        self.stale_after_seconds = float(
            stale_after_seconds
        )

        self.per_asset_timeout_seconds = float(
            per_asset_timeout_seconds
        )

        self.max_workers = int(
            max_workers
        )

        self._cycle_lock = Lock()

    def _fetch_one(
        self,
        asset_id,
        global_deadline,
    ):
        now = self.clock.monotonic()

        if now >= global_deadline:
            raise TimeoutError(
                "Global market-data deadline exceeded"
            )

        asset_deadline = min(
            global_deadline,
            (
                now
                + self.per_asset_timeout_seconds
            ),
        )

        snapshot = (
            self.provider
            .get_market_snapshot(
                asset_id,
                stale_after_seconds=(
                    self.stale_after_seconds
                ),
                deadline_monotonic=(
                    asset_deadline
                ),
            )
        )

        if not isinstance(
            snapshot,
            MarketSnapshot,
        ):
            raise TypeError(
                "Provider returned non-MarketSnapshot"
            )

        return snapshot

    def run_cycle(
        self,
        asset_ids,
    ) -> MarketDataCycleResult:
        if not self._cycle_lock.acquire(
            blocking=False
        ):
            raise CycleInProgressError(
                "Market-data cycle already in progress"
            )

        started = self.clock.monotonic()

        global_deadline = (
            started
            + self.cycle_timeout_seconds
        )

        asset_ids = tuple(
            asset_ids
        )

        snapshots = {}
        errors = {}
        timed_out = False

        executor = None

        try:
            if not asset_ids:
                return MarketDataCycleResult(
                    snapshots=MappingProxyType(
                        {}
                    ),
                    errors=MappingProxyType(
                        {}
                    ),
                    duration_seconds=0.0,
                    timed_out=False,
                )

            workers = min(
                self.max_workers,
                len(asset_ids),
            )

            executor = ThreadPoolExecutor(
                max_workers=workers,
                thread_name_prefix=(
                    "realistic-market-data"
                ),
            )

            futures = {
                executor.submit(
                    self._fetch_one,
                    asset_id,
                    global_deadline,
                ): asset_id
                for asset_id in asset_ids
            }

            remaining = max(
                0.0,
                (
                    global_deadline
                    - self.clock.monotonic()
                ),
            )

            done, not_done = wait(
                futures,
                timeout=remaining,
            )

            for future in done:
                asset_id = futures[
                    future
                ]

                try:
                    snapshot = future.result()

                except TimeoutError:
                    errors[
                        asset_id
                    ] = "PROVIDER_TIMEOUT"

                except Exception as exc:
                    errors[
                        asset_id
                    ] = (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )

                else:
                    snapshots[
                        asset_id
                    ] = snapshot

            if not_done:
                timed_out = True

                for future in not_done:
                    asset_id = futures[
                        future
                    ]

                    future.cancel()

                    errors.setdefault(
                        asset_id,
                        "PROVIDER_TIMEOUT",
                    )

            duration = max(
                0.0,
                (
                    self.clock.monotonic()
                    - started
                ),
            )

            if (
                duration
                > self.cycle_timeout_seconds
            ):
                timed_out = True

            return MarketDataCycleResult(
                snapshots=MappingProxyType(
                    dict(
                        snapshots
                    )
                ),
                errors=MappingProxyType(
                    dict(
                        errors
                    )
                ),
                duration_seconds=duration,
                timed_out=timed_out,
            )

        finally:
            if executor is not None:
                executor.shutdown(
                    wait=False,
                    cancel_futures=True,
                )

            self._cycle_lock.release()
