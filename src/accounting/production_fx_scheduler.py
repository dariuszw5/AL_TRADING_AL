from __future__ import annotations

import time
from concurrent.futures import (
    ThreadPoolExecutor,
    wait,
)

from src.accounting.instrument_contracts import (
    InstrumentAccountingContractError,
    require_runtime_accounting_contract,
)
from src.accounting.production_resolvers import (
    ProductionFxResolver,
)


FX_PREFETCH_TIMEOUT = "FX_PREFETCH_TIMEOUT"
PREVIOUS_FX_PREFETCH_STILL_RUNNING = (
    "PREVIOUS_FX_PREFETCH_STILL_RUNNING"
)


class ProductionFxSchedulerError(
    ValueError
):
    pass


class ParallelProductionFxResolver(
    ProductionFxResolver
):
    """
    Bounded parallel prefetch for production FX evidence.

    This class intentionally requires an explicit timeout and worker
    limit. It does not silently consume the entire REALISTIC_V2 cycle
    budget.

    Running provider threads cannot be force-killed safely by Python.
    If a provider call remains alive after the hard prefetch timeout,
    the next FX prefetch cycle is blocked from starting new work until
    those prior futures have completed. Execution accounting therefore
    fails closed without creating overlapping FX fetch generations.
    """

    def __init__(
        self,
        *,
        prefetch_timeout_seconds,
        max_workers,
        monotonic_fn=None,
        **kwargs,
    ):
        super().__init__(
            **kwargs
        )

        timeout = float(
            prefetch_timeout_seconds
        )

        if timeout <= 0:
            raise ProductionFxSchedulerError(
                "prefetch_timeout_seconds "
                "must be positive"
            )

        workers = int(
            max_workers
        )

        if workers <= 0:
            raise ProductionFxSchedulerError(
                "max_workers must be positive"
            )

        if (
            isinstance(
                max_workers,
                float,
            )
            and not max_workers.is_integer()
        ):
            raise ProductionFxSchedulerError(
                "max_workers must be an integer"
            )

        self.prefetch_timeout_seconds = (
            timeout
        )
        self.max_workers = workers
        self.monotonic_fn = (
            monotonic_fn
            or time.monotonic
        )

        self.last_prefetch_duration_seconds = (
            None
        )
        self.last_prefetch_timed_out = False
        self.last_prefetch_blocked_by_previous = (
            False
        )

        self._previous_futures = ()

    def _reset_cycle_state(
        self,
    ):
        self._cycle_started = True
        self._forced_cycle_error = None
        self._mtm_quotes = {}
        self._realized_quotes = {}
        self._provider_errors = {}
        self._contract_errors = {}

        self.last_prefetch_duration_seconds = (
            None
        )
        self.last_prefetch_timed_out = False
        self.last_prefetch_blocked_by_previous = (
            False
        )

    def _unfinished_previous_futures(
        self,
    ):
        unfinished = tuple(
            future
            for future
            in self._previous_futures
            if not future.done()
        )

        self._previous_futures = (
            unfinished
        )

        return unfinished

    def _native_currencies(
        self,
        asset_ids,
    ):
        native_currencies = set()

        for asset_id in tuple(
            asset_ids
        ):
            normalized = str(
                asset_id
            )

            try:
                contract = (
                    require_runtime_accounting_contract(
                        normalized
                    )
                )

            except (
                InstrumentAccountingContractError,
                ValueError,
            ) as exc:
                self._contract_errors[
                    normalized
                ] = (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )
                continue

            native_currencies.add(
                contract.native_pnl_currency
            )

        return native_currencies

    def _fetch_plan(
        self,
        asset_ids,
    ):
        native_currencies = (
            self._native_currencies(
                asset_ids
            )
        )

        need_usd = bool(
            native_currencies
            & {
                "USD",
                "USDT",
            }
        )

        need_eur = (
            "EUR"
            in native_currencies
        )

        need_usdt = (
            "USDT"
            in native_currencies
        )

        plan = []

        if need_usd:
            plan.extend(
                (
                    (
                        "MTM:USDPLN",
                        lambda: self
                        .yahoo_provider
                        .get_quote(
                            "USD"
                        ),
                        True,
                        False,
                    ),
                    (
                        "REALIZED:USDPLN",
                        lambda: self
                        .nbp_provider
                        .get_reference(
                            "USD"
                        ),
                        False,
                        True,
                    ),
                )
            )

        if need_eur:
            plan.extend(
                (
                    (
                        "MTM:EURPLN",
                        lambda: self
                        .yahoo_provider
                        .get_quote(
                            "EUR"
                        ),
                        True,
                        False,
                    ),
                    (
                        "REALIZED:EURPLN",
                        lambda: self
                        .nbp_provider
                        .get_reference(
                            "EUR"
                        ),
                        False,
                        True,
                    ),
                )
            )

        if need_usdt:
            plan.append(
                (
                    "MARKET:USDTUSD",
                    self.coinbase_provider
                    .get_quote,
                    True,
                    True,
                )
            )

        return tuple(
            plan
        )

    def _store_quote(
        self,
        *,
        key,
        quote,
        mtm,
        realized,
    ):
        pair = str(
            quote.pair
        )

        if mtm:
            existing = (
                self._mtm_quotes.get(
                    pair
                )
            )

            if existing is not None:
                self._provider_errors[
                    key
                ] = (
                    "DUPLICATE_MTM_FX_PAIR:"
                    + pair
                )
            else:
                self._mtm_quotes[
                    pair
                ] = quote

        if realized:
            realized_key = (
                pair,
                str(
                    quote.provider
                ),
            )

            existing = (
                self._realized_quotes.get(
                    realized_key
                )
            )

            if existing is not None:
                self._provider_errors[
                    key
                ] = (
                    "DUPLICATE_REALIZED_FX_EVIDENCE:"
                    + pair
                    + ":"
                    + str(
                        quote.provider
                    )
                )
            else:
                self._realized_quotes[
                    realized_key
                ] = quote

    def begin_cycle(
        self,
        asset_ids,
    ):
        self._reset_cycle_state()

        prior = (
            self._unfinished_previous_futures()
        )

        if prior:
            self.last_prefetch_blocked_by_previous = (
                True
            )

            self._provider_errors[
                "PREFETCH"
            ] = (
                PREVIOUS_FX_PREFETCH_STILL_RUNNING
            )

            self.last_prefetch_duration_seconds = (
                0.0
            )

            return

        plan = self._fetch_plan(
            asset_ids
        )

        if not plan:
            self.last_prefetch_duration_seconds = (
                0.0
            )
            return

        started = float(
            self.monotonic_fn()
        )

        executor = ThreadPoolExecutor(
            max_workers=(
                min(
                    self.max_workers,
                    len(plan),
                )
            ),
            thread_name_prefix=(
                "phase10-fx"
            ),
        )

        future_by_key = {}

        try:
            for (
                key,
                fetch,
                mtm,
                realized,
            ) in plan:
                future_by_key[
                    key
                ] = (
                    executor.submit(
                        fetch
                    )
                )

            done, not_done = wait(
                tuple(
                    future_by_key.values()
                ),
                timeout=(
                    self.prefetch_timeout_seconds
                ),
            )

            for (
                key,
                fetch,
                mtm,
                realized,
            ) in plan:
                future = (
                    future_by_key[
                        key
                    ]
                )

                if future in not_done:
                    self._provider_errors[
                        key
                    ] = (
                        FX_PREFETCH_TIMEOUT
                    )
                    continue

                try:
                    quote = future.result()

                except Exception as exc:
                    self._provider_errors[
                        key
                    ] = (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )
                    continue

                self._store_quote(
                    key=key,
                    quote=quote,
                    mtm=mtm,
                    realized=realized,
                )

            if not_done:
                self.last_prefetch_timed_out = (
                    True
                )

                for future in not_done:
                    future.cancel()

                self._previous_futures = tuple(
                    not_done
                )

            else:
                self._previous_futures = ()

        finally:
            executor.shutdown(
                wait=False,
                cancel_futures=True,
            )

            finished = float(
                self.monotonic_fn()
            )

            duration = (
                finished
                - started
            )

            self.last_prefetch_duration_seconds = (
                max(
                    0.0,
                    duration,
                )
            )
