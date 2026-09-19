from __future__ import annotations

from dataclasses import dataclass

from src.accounting.runtime_bridge import (
    Phase09RuntimeAccountingBridge,
)
from src.execution.models import (
    PaperMode,
)
from src.execution.paper_broker import (
    PaperBroker,
)
from src.execution.slippage import (
    FixedBpsSlippage,
)
from src.fx.realized_booking import (
    RealizedFxBooker,
)
from src.fx.realized_selection import (
    RealizedFxSelectionPolicy,
)
from src.persistence.sqlite_realistic_v2_mapper import (
    RealisticV2SQLiteMapper,
)


class Phase14PaperDependencyError(
    ValueError
):
    pass


@dataclass(
    frozen=True
)
class Phase14PaperDependencyContext:
    market_data_service: object
    market_session_service: object
    decision_provider: object
    clock: object
    asset_resolver: object
    fx_conversion_resolver: object
    estimated_exit_fee_resolver: object
    realized_quotes_resolver: object
    execution_evidence_resolver: object
    realized_evidence_resolver: object
    trading_fee_rate: float = 0.0
    slippage_bps: float = 0.0
    strategy_id: str = "PHASE14"
    realized_market_max_age_seconds: float = 7200.0
    realized_daily_reference_max_age_days: int = 7


def _require_method(
    value,
    method_name,
    field_name,
):
    if value is None:
        raise Phase14PaperDependencyError(
            field_name + " is required"
        )

    method = getattr(
        value,
        method_name,
        None,
    )

    if not callable(
        method
    ):
        raise Phase14PaperDependencyError(
            field_name
            + " must expose "
            + method_name
            + "()"
        )


def _require_callable(
    value,
    field_name,
):
    if not callable(
        value
    ):
        raise Phase14PaperDependencyError(
            field_name
            + " must be callable"
        )


def _validate_context(
    context,
):
    if not isinstance(
        context,
        Phase14PaperDependencyContext,
    ):
        raise TypeError(
            "context must be Phase14PaperDependencyContext"
        )

    _require_method(
        context.market_data_service,
        "run_cycle",
        "market_data_service",
    )

    _require_method(
        context.market_session_service,
        "get_session",
        "market_session_service",
    )

    _require_method(
        context.clock,
        "now",
        "clock",
    )

    for field_name in (
        "decision_provider",
        "asset_resolver",
        "fx_conversion_resolver",
        "estimated_exit_fee_resolver",
        "realized_quotes_resolver",
        "execution_evidence_resolver",
        "realized_evidence_resolver",
    ):
        _require_callable(
            getattr(
                context,
                field_name,
            ),
            field_name,
        )

    if not str(
        context.strategy_id
    ).strip():
        raise Phase14PaperDependencyError(
            "strategy_id must be non-empty"
        )

    if (
        float(
            context.realized_market_max_age_seconds
        )
        <= 0
    ):
        raise Phase14PaperDependencyError(
            "realized_market_max_age_seconds must be > 0"
        )

    if (
        int(
            context.realized_daily_reference_max_age_days
        )
        < 0
    ):
        raise Phase14PaperDependencyError(
            "realized_daily_reference_max_age_days must be >= 0"
        )


def build_phase14_sqlite_bundle_kwargs(
    context,
):
    """
    Compose the real paper-runtime core used by the Phase 13 SQLite bundle.

    Market/session/decision/FX services are explicit injected dependencies.
    This function never opens SQLite and never runs a cycle.
    """

    _validate_context(
        context
    )

    broker = PaperBroker(
        clock=context.clock,
        asset_resolver=context.asset_resolver,
        slippage_model=FixedBpsSlippage(
            float(
                context.slippage_bps
            )
        ),
        trading_fee_rate=float(
            context.trading_fee_rate
        ),
        execution_journal=None,
    )

    accounting_bridge = (
        Phase09RuntimeAccountingBridge(
            fx_enabled=True,
            pln_accounting_enabled=True,
            realized_fx_selection_policy=(
                RealizedFxSelectionPolicy(
                    market_max_age_seconds=float(
                        context.realized_market_max_age_seconds
                    ),
                    daily_reference_max_age_days=int(
                        context.realized_daily_reference_max_age_days
                    ),
                )
            ),
            realized_fx_booker=(
                RealizedFxBooker(
                    clock=context.clock
                )
            ),
        )
    )

    def cycle_mapper_factory(
        repository,
    ):
        return RealisticV2SQLiteMapper(
            order_fingerprint_resolver=(
                broker.order_fingerprint
            ),
            execution_evidence_resolver=(
                context.execution_evidence_resolver
            ),
            realized_evidence_resolver=(
                context.realized_evidence_resolver
            ),
            strategy_id=str(
                context.strategy_id
            ),
        )

    return {
        "market_data_service": (
            context.market_data_service
        ),
        "market_session_service": (
            context.market_session_service
        ),
        "broker": broker,
        "decision_provider": (
            context.decision_provider
        ),
        "clock": context.clock,
        "paper_mode": (
            PaperMode.REALISTIC_PAPER
        ),
        "accounting_bridge": (
            accounting_bridge
        ),
        "fx_conversion_resolver": (
            context.fx_conversion_resolver
        ),
        "estimated_exit_fee_resolver": (
            context.estimated_exit_fee_resolver
        ),
        "realized_quotes_resolver": (
            context.realized_quotes_resolver
        ),
        "cycle_mapper_factory": (
            cycle_mapper_factory
        ),
    }


def make_phase14_sqlite_bundle_kwargs_provider(
    context,
):
    _validate_context(
        context
    )

    def provider(
        *,
        database_path,
        live_database_path,
    ):
        # Paths are intentionally not opened here.
        # A.2/A.4 own path authorization; A.3 owns bundle construction.
        return build_phase14_sqlite_bundle_kwargs(
            context
        )

    return provider
