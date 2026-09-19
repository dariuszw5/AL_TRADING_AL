from __future__ import annotations

from dataclasses import dataclass

from src.accounting.production_resolvers import (
    BrokerExitFeeEstimator,
    ProductionFxResolver,
)
from src.persistence.sqlite_application_binding import (
    Phase14ApplicationBindingInputs,
    build_phase14_application_context,
)


class Phase14ProductionApplicationProviderError(
    ValueError
):
    pass


@dataclass(
    frozen=True
)
class Phase14ProductionBindingInputs:
    market_data_service: object
    decision_provider: object
    production_fx_resolver: object
    exit_fee_estimator: object
    execution_evidence_resolver: object
    realized_evidence_resolver: object
    market_session_service: object | None = None
    clock: object | None = None
    asset_resolver: object | None = None
    trading_fee_rate: float = 0.0
    slippage_bps: float = 0.0
    strategy_id: str = "PHASE14"
    realized_market_max_age_seconds: float = 7200.0
    realized_daily_reference_max_age_days: int = 7


def _require_callable(
    value,
    name,
):
    if not callable(
        value
    ):
        raise Phase14ProductionApplicationProviderError(
            name
            + " must be callable"
        )


def _require_method(
    value,
    method_name,
    name,
):
    if value is None:
        raise Phase14ProductionApplicationProviderError(
            name
            + " is required"
        )

    method = getattr(
        value,
        method_name,
        None,
    )

    if not callable(
        method
    ):
        raise Phase14ProductionApplicationProviderError(
            name
            + " must expose "
            + method_name
            + "()"
        )


def build_phase14_production_application_inputs(
    inputs,
):
    """
    Bind existing production accounting resolver objects into A.7 inputs.

    This function performs no provider I/O and does not run any cycle.
    ProductionFxResolver methods are passed as callables; they are not
    invoked during construction.
    """

    if not isinstance(
        inputs,
        Phase14ProductionBindingInputs,
    ):
        raise TypeError(
            "inputs must be Phase14ProductionBindingInputs"
        )

    _require_method(
        inputs.market_data_service,
        "run_cycle",
        "market_data_service",
    )

    _require_callable(
        inputs.decision_provider,
        "decision_provider",
    )

    _require_callable(
        inputs.execution_evidence_resolver,
        "execution_evidence_resolver",
    )

    _require_callable(
        inputs.realized_evidence_resolver,
        "realized_evidence_resolver",
    )

    if not isinstance(
        inputs.production_fx_resolver,
        ProductionFxResolver,
    ):
        raise Phase14ProductionApplicationProviderError(
            "production_fx_resolver must be ProductionFxResolver"
        )

    if not isinstance(
        inputs.exit_fee_estimator,
        BrokerExitFeeEstimator,
    ):
        raise Phase14ProductionApplicationProviderError(
            "exit_fee_estimator must be BrokerExitFeeEstimator"
        )

    _require_method(
        inputs.production_fx_resolver,
        "conversion_for",
        "production_fx_resolver",
    )

    _require_method(
        inputs.production_fx_resolver,
        "resolve_realized_quotes",
        "production_fx_resolver",
    )

    if not callable(
        inputs.exit_fee_estimator
    ):
        raise Phase14ProductionApplicationProviderError(
            "exit_fee_estimator must be callable"
        )

    strategy_id = str(
        inputs.strategy_id
    ).strip()

    if not strategy_id:
        raise Phase14ProductionApplicationProviderError(
            "strategy_id must be non-empty"
        )

    return Phase14ApplicationBindingInputs(
        market_data_service=(
            inputs.market_data_service
        ),
        decision_provider=(
            inputs.decision_provider
        ),
        fx_conversion_resolver=(
            inputs.production_fx_resolver.conversion_for
        ),
        estimated_exit_fee_resolver=(
            inputs.exit_fee_estimator
        ),
        realized_quotes_resolver=(
            inputs.production_fx_resolver.resolve_realized_quotes
        ),
        execution_evidence_resolver=(
            inputs.execution_evidence_resolver
        ),
        realized_evidence_resolver=(
            inputs.realized_evidence_resolver
        ),
        market_session_service=(
            inputs.market_session_service
        ),
        clock=inputs.clock,
        asset_resolver=(
            inputs.asset_resolver
        ),
        trading_fee_rate=float(
            inputs.trading_fee_rate
        ),
        slippage_bps=float(
            inputs.slippage_bps
        ),
        strategy_id=strategy_id,
        realized_market_max_age_seconds=float(
            inputs.realized_market_max_age_seconds
        ),
        realized_daily_reference_max_age_days=int(
            inputs.realized_daily_reference_max_age_days
        ),
    )


def build_phase14_production_application_context(
    inputs,
):
    return build_phase14_application_context(
        build_phase14_production_application_inputs(
            inputs
        )
    )
