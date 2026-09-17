from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from types import MappingProxyType

from src.accounting.instrument_contracts import (
    InstrumentAccountingContractError,
    require_runtime_accounting_contract,
)
from src.accounting.runtime_bridge import (
    Phase09RuntimeAccountingBridge,
)
from src.accounting.runtime_integration import (
    Phase09AccountingRuntime,
    SnapshotCaptureDecisionProvider,
)
from src.core.clock import (
    SystemClock,
)
from src.fx.converter import (
    CurrencyConverter,
)
from src.fx.freshness import (
    production_fx_freshness_policy,
)
from src.fx.providers import (
    CoinbaseUsdtUsdProvider,
    NbpTableAProvider,
    YahooPlnProvider,
)
from src.fx.realized_booking import (
    RealizedFxBooker,
)
from src.fx.realized_selection import (
    RealizedFxSelectionPolicy,
)


PRODUCTION_FX_CYCLE_NOT_STARTED = (
    "PRODUCTION_FX_CYCLE_NOT_STARTED"
)

PRODUCTION_FX_PREFETCH_FAILED = (
    "PRODUCTION_FX_PREFETCH_FAILED"
)


class Phase10ProductionAccountingError(
    ValueError
):
    pass


def _decimal(
    value,
    field_name,
    *,
    nonnegative=False,
    positive=False,
):
    try:
        result = Decimal(
            str(value)
        )
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise Phase10ProductionAccountingError(
            f"{field_name} must be a finite decimal"
        ) from exc

    if not result.is_finite():
        raise Phase10ProductionAccountingError(
            f"{field_name} must be a finite decimal"
        )

    if (
        nonnegative
        and result < 0
    ):
        raise Phase10ProductionAccountingError(
            f"{field_name} must be nonnegative"
        )

    if (
        positive
        and result <= 0
    ):
        raise Phase10ProductionAccountingError(
            f"{field_name} must be positive"
        )

    return result


def _side_name(value):
    raw = getattr(
        value,
        "value",
        value,
    )

    result = (
        str(raw)
        .strip()
        .upper()
    )

    if result not in {
        "LONG",
        "SHORT",
    }:
        raise Phase10ProductionAccountingError(
            "POSITION_SIDE_UNSUPPORTED:"
            + result
        )

    return result


class ProductionFxResolver:
    """
    Per-cycle FX evidence cache for REALISTIC_V2 accounting.

    Quotes are prefetched before execution so a same-day NBP reference
    can be audited as observed no later than a close that occurs in the
    same cycle.

    Provider failures are retained as accounting evidence and do not
    raise from begin_cycle. Missing legs therefore fail closed later in
    the existing Phase 09 accounting layer.
    """

    def __init__(
        self,
        *,
        clock=None,
        nbp_provider=None,
        yahoo_provider=None,
        coinbase_provider=None,
        converter=None,
    ):
        self.clock = (
            clock
            or SystemClock()
        )

        self.nbp_provider = (
            nbp_provider
            or NbpTableAProvider(
                clock=self.clock
            )
        )

        self.yahoo_provider = (
            yahoo_provider
            or YahooPlnProvider(
                clock=self.clock
            )
        )

        self.coinbase_provider = (
            coinbase_provider
            or CoinbaseUsdtUsdProvider(
                clock=self.clock
            )
        )

        self.converter = (
            converter
            or CurrencyConverter(
                freshness_policy=(
                    production_fx_freshness_policy()
                ),
                clock=self.clock,
            )
        )

        self._cycle_started = False
        self._forced_cycle_error = None
        self._mtm_quotes = {}
        self._realized_quotes = {}
        self._provider_errors = {}
        self._contract_errors = {}

    @property
    def provider_errors(self):
        return MappingProxyType(
            dict(
                self._provider_errors
            )
        )

    @property
    def contract_errors(self):
        return MappingProxyType(
            dict(
                self._contract_errors
            )
        )

    @property
    def cycle_started(self):
        return self._cycle_started

    @property
    def mtm_quotes(self):
        return tuple(
            self._mtm_quotes[
                key
            ]
            for key in sorted(
                self._mtm_quotes
            )
        )

    @property
    def realized_quotes(self):
        return tuple(
            self._realized_quotes[
                key
            ]
            for key in sorted(
                self._realized_quotes
            )
        )

    def force_cycle_error(
        self,
        exc,
    ):
        self._cycle_started = True
        self._forced_cycle_error = (
            f"{type(exc).__name__}: {exc}"
        )
        self._mtm_quotes = {}
        self._realized_quotes = {}
        self._provider_errors = {
            "PREFETCH": (
                self._forced_cycle_error
            )
        }

    def _capture(
        self,
        *,
        key,
        fetch,
        mtm=False,
        realized=False,
    ):
        try:
            quote = fetch()

        except Exception as exc:
            self._provider_errors[
                key
            ] = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )
            return None

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

        return quote

    def begin_cycle(
        self,
        asset_ids,
    ):
        self._cycle_started = True
        self._forced_cycle_error = None
        self._mtm_quotes = {}
        self._realized_quotes = {}
        self._provider_errors = {}
        self._contract_errors = {}

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

        if need_usd:
            self._capture(
                key="MTM:USDPLN",
                fetch=(
                    lambda: self
                    .yahoo_provider
                    .get_quote(
                        "USD"
                    )
                ),
                mtm=True,
            )

            self._capture(
                key="REALIZED:USDPLN",
                fetch=(
                    lambda: self
                    .nbp_provider
                    .get_reference(
                        "USD"
                    )
                ),
                realized=True,
            )

        if need_eur:
            self._capture(
                key="MTM:EURPLN",
                fetch=(
                    lambda: self
                    .yahoo_provider
                    .get_quote(
                        "EUR"
                    )
                ),
                mtm=True,
            )

            self._capture(
                key="REALIZED:EURPLN",
                fetch=(
                    lambda: self
                    .nbp_provider
                    .get_reference(
                        "EUR"
                    )
                ),
                realized=True,
            )

        if need_usdt:
            self._capture(
                key="MARKET:USDTUSD",
                fetch=(
                    self.coinbase_provider
                    .get_quote
                ),
                mtm=True,
                realized=True,
            )

    def _require_cycle(
        self,
    ):
        if not self._cycle_started:
            raise Phase10ProductionAccountingError(
                PRODUCTION_FX_CYCLE_NOT_STARTED
            )

        if (
            self._forced_cycle_error
            is not None
        ):
            raise Phase10ProductionAccountingError(
                PRODUCTION_FX_PREFETCH_FAILED
                + ":"
                + self._forced_cycle_error
            )

    @staticmethod
    def _native_currency(
        asset_id,
    ):
        contract = (
            require_runtime_accounting_contract(
                asset_id
            )
        )

        return (
            contract.native_pnl_currency
        )

    def conversion_for(
        self,
        asset_id,
    ):
        self._require_cycle()

        native_currency = (
            self._native_currency(
                asset_id
            )
        )

        return self.converter.convert_to_pln(
            1.0,
            native_currency,
            self.mtm_quotes,
        )

    def realized_quotes_for(
        self,
        asset_id,
    ):
        self._require_cycle()

        native_currency = (
            self._native_currency(
                asset_id
            )
        )

        if native_currency == "PLN":
            return ()

        required_pairs = {
            "USD": {
                "USDPLN",
            },
            "EUR": {
                "EURPLN",
            },
            "USDT": {
                "USDTUSD",
                "USDPLN",
            },
        }.get(
            native_currency
        )

        if required_pairs is None:
            return ()

        return tuple(
            quote
            for quote
            in self.realized_quotes
            if quote.pair
            in required_pairs
        )

    def __call__(
        self,
        *,
        asset_id,
        position,
        market_snapshot,
    ):
        return self.conversion_for(
            asset_id
        )

    def resolve_realized_quotes(
        self,
        *,
        asset_id,
        position,
        entry_execution,
        exit_execution,
    ):
        return self.realized_quotes_for(
            asset_id
        )


class BrokerExitFeeEstimator:
    """
    Estimate the exit fee using the same fee rate as PaperBroker.

    The estimate uses the liquidation-side market mark:
    LONG -> bid
    SHORT -> ask

    It deliberately does not predict exit slippage.
    """

    def __init__(
        self,
        broker,
    ):
        if broker is None:
            raise TypeError(
                "broker is required"
            )

        if not hasattr(
            broker,
            "trading_fee_rate",
        ):
            raise TypeError(
                "broker.trading_fee_rate is required"
            )

        self.broker = broker

        self.trading_fee_rate = (
            _decimal(
                broker.trading_fee_rate,
                "broker.trading_fee_rate",
                nonnegative=True,
            )
        )

    def __call__(
        self,
        *,
        asset_id,
        position,
        market_snapshot,
    ):
        position_asset = str(
            getattr(
                position,
                "asset_id",
                "",
            )
        )

        snapshot_asset = str(
            getattr(
                market_snapshot,
                "asset_id",
                "",
            )
        )

        asset_id = str(
            asset_id
        )

        if (
            position_asset != asset_id
            or snapshot_asset != asset_id
        ):
            raise Phase10ProductionAccountingError(
                "EXIT_FEE_ASSET_MISMATCH"
            )

        side = _side_name(
            getattr(
                position,
                "side",
                None,
            )
        )

        mark = (
            getattr(
                market_snapshot,
                "bid",
                None,
            )
            if side == "LONG"
            else getattr(
                market_snapshot,
                "ask",
                None,
            )
        )

        mark = _decimal(
            mark,
            "exit_fee_mark_price",
            positive=True,
        )

        quantity = _decimal(
            getattr(
                position,
                "quantity",
                None,
            ),
            "position.quantity",
            positive=True,
        )

        return abs(
            mark
            * quantity
            * self.trading_fee_rate
        )


class Phase10ProductionAccountingRuntime:
    """
    Add production FX prefetch to the Phase 09 accounting runtime.

    Prefetch is intentionally best-effort for accounting only.
    An unexpected prefetch exception is converted into fail-closed
    accounting state and execution still proceeds.
    """

    def __init__(
        self,
        *,
        accounting_runtime,
        fx_resolver,
    ):
        if accounting_runtime is None:
            raise TypeError(
                "accounting_runtime is required"
            )

        if not isinstance(
            fx_resolver,
            ProductionFxResolver,
        ):
            raise TypeError(
                "fx_resolver must be ProductionFxResolver"
            )

        self.accounting_runtime = (
            accounting_runtime
        )
        self.fx_resolver = (
            fx_resolver
        )

    @property
    def execution_runtime(self):
        return (
            self.accounting_runtime.runtime
        )

    @property
    def positions(self):
        return (
            self.execution_runtime.positions
        )

    def run_cycle(
        self,
        asset_ids,
    ):
        asset_ids = tuple(
            str(asset_id)
            for asset_id in asset_ids
        )

        try:
            self.fx_resolver.begin_cycle(
                asset_ids
            )

        except Exception as exc:
            self.fx_resolver.force_cycle_error(
                exc
            )

        return (
            self.accounting_runtime
            .run_cycle(
                asset_ids
            )
        )


@dataclass(frozen=True)
class Phase10ProductionAccountingWiring:
    runtime: Phase10ProductionAccountingRuntime
    accounting_runtime: Phase09AccountingRuntime
    accounting_bridge: Phase09RuntimeAccountingBridge
    snapshot_capture: SnapshotCaptureDecisionProvider
    fx_resolver: ProductionFxResolver
    exit_fee_estimator: BrokerExitFeeEstimator


def wire_phase10_production_accounting(
    *,
    runtime,
    broker,
    realized_market_max_age_seconds,
    realized_daily_reference_max_age_days,
    clock=None,
    nbp_provider=None,
    yahoo_provider=None,
    coinbase_provider=None,
    cash_pln_resolver=None,
):
    """
    Wire verified Phase 09 accounting components around an existing
    REALISTIC_V2 runtime without changing PaperBroker execution semantics.

    Feature-flag gating is intentionally left to the caller.
    """

    if runtime is None:
        raise TypeError(
            "runtime is required"
        )

    if broker is None:
        raise TypeError(
            "broker is required"
        )

    runtime_broker = getattr(
        runtime,
        "broker",
        broker,
    )

    if runtime_broker is not broker:
        raise Phase10ProductionAccountingError(
            "RUNTIME_BROKER_MISMATCH"
        )

    delegate = getattr(
        runtime,
        "decision_provider",
        None,
    )

    if not callable(
        delegate
    ):
        raise Phase10ProductionAccountingError(
            "RUNTIME_DECISION_PROVIDER_REQUIRED"
        )

    if isinstance(
        delegate,
        SnapshotCaptureDecisionProvider,
    ):
        raise Phase10ProductionAccountingError(
            "RUNTIME_ALREADY_ACCOUNTING_WRAPPED"
        )

    market_age = _decimal(
        realized_market_max_age_seconds,
        "realized_market_max_age_seconds",
        positive=True,
    )

    reference_age = int(
        realized_daily_reference_max_age_days
    )

    if reference_age <= 0:
        raise Phase10ProductionAccountingError(
            "realized_daily_reference_max_age_days "
            "must be positive"
        )

    resolved_clock = (
        clock
        or getattr(
            runtime,
            "clock",
            None,
        )
        or SystemClock()
    )

    fx_resolver = (
        ProductionFxResolver(
            clock=resolved_clock,
            nbp_provider=nbp_provider,
            yahoo_provider=yahoo_provider,
            coinbase_provider=coinbase_provider,
        )
    )

    exit_fee_estimator = (
        BrokerExitFeeEstimator(
            broker
        )
    )

    accounting_bridge = (
        Phase09RuntimeAccountingBridge(
            fx_enabled=True,
            pln_accounting_enabled=True,
            realized_fx_selection_policy=(
                RealizedFxSelectionPolicy(
                    market_max_age_seconds=float(
                        market_age
                    ),
                    daily_reference_max_age_days=(
                        reference_age
                    ),
                )
            ),
            realized_fx_booker=(
                RealizedFxBooker(
                    clock=resolved_clock
                )
            ),
        )
    )

    snapshot_capture = (
        SnapshotCaptureDecisionProvider(
            delegate
        )
    )

    runtime.decision_provider = (
        snapshot_capture
    )

    try:
        accounting_runtime = (
            Phase09AccountingRuntime(
                runtime=runtime,
                accounting_bridge=(
                    accounting_bridge
                ),
                snapshot_capture=(
                    snapshot_capture
                ),
                fx_conversion_resolver=(
                    fx_resolver
                ),
                estimated_exit_fee_resolver=(
                    exit_fee_estimator
                ),
                realized_quotes_resolver=(
                    fx_resolver
                    .resolve_realized_quotes
                ),
                cash_pln_resolver=(
                    cash_pln_resolver
                ),
            )
        )

    except Exception:
        runtime.decision_provider = (
            delegate
        )
        raise

    wrapped_runtime = (
        Phase10ProductionAccountingRuntime(
            accounting_runtime=(
                accounting_runtime
            ),
            fx_resolver=(
                fx_resolver
            ),
        )
    )

    return Phase10ProductionAccountingWiring(
        runtime=wrapped_runtime,
        accounting_runtime=(
            accounting_runtime
        ),
        accounting_bridge=(
            accounting_bridge
        ),
        snapshot_capture=(
            snapshot_capture
        ),
        fx_resolver=fx_resolver,
        exit_fee_estimator=(
            exit_fee_estimator
        ),
    )
