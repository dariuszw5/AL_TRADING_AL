from __future__ import annotations

from dataclasses import dataclass

from src.core.clock import SystemClock
from src.data.assets import get_asset
from src.market.market_session import (
    MarketSessionService,
)
from src.persistence.sqlite_cutover_dependencies import (
    Phase14PaperDependencyContext,
)


class Phase14ApplicationBindingError(
    ValueError
):
    pass


@dataclass(
    frozen=True
)
class Phase14ApplicationBindingInputs:
    market_data_service: object
    decision_provider: object
    fx_conversion_resolver: object
    estimated_exit_fee_resolver: object
    realized_quotes_resolver: object
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
        raise Phase14ApplicationBindingError(
            name
            + " must be callable"
        )


def _require_method(
    value,
    method_name,
    name,
):
    if value is None:
        raise Phase14ApplicationBindingError(
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
        raise Phase14ApplicationBindingError(
            name
            + " must expose "
            + method_name
            + "()"
        )


def build_phase14_application_context(
    inputs,
):
    """
    Bind only application components that A.6 identified unambiguously.

    Automatic application defaults:
    - MarketSessionService
    - SystemClock
    - get_asset

    Ambiguous or evidence-bearing dependencies remain explicit and
    fail closed when missing.
    """

    if not isinstance(
        inputs,
        Phase14ApplicationBindingInputs,
    ):
        raise TypeError(
            "inputs must be Phase14ApplicationBindingInputs"
        )

    _require_method(
        inputs.market_data_service,
        "run_cycle",
        "market_data_service",
    )

    for name in (
        "decision_provider",
        "fx_conversion_resolver",
        "estimated_exit_fee_resolver",
        "realized_quotes_resolver",
        "execution_evidence_resolver",
        "realized_evidence_resolver",
    ):
        _require_callable(
            getattr(
                inputs,
                name,
            ),
            name,
        )

    market_session_service = (
        inputs.market_session_service
        if inputs.market_session_service is not None
        else MarketSessionService()
    )

    clock = (
        inputs.clock
        if inputs.clock is not None
        else SystemClock()
    )

    asset_resolver = (
        inputs.asset_resolver
        if inputs.asset_resolver is not None
        else get_asset
    )

    _require_method(
        market_session_service,
        "get_session",
        "market_session_service",
    )

    _require_method(
        clock,
        "now",
        "clock",
    )

    _require_callable(
        asset_resolver,
        "asset_resolver",
    )

    strategy_id = str(
        inputs.strategy_id
    ).strip()

    if not strategy_id:
        raise Phase14ApplicationBindingError(
            "strategy_id must be non-empty"
        )

    return Phase14PaperDependencyContext(
        market_data_service=(
            inputs.market_data_service
        ),
        market_session_service=(
            market_session_service
        ),
        decision_provider=(
            inputs.decision_provider
        ),
        clock=clock,
        asset_resolver=asset_resolver,
        fx_conversion_resolver=(
            inputs.fx_conversion_resolver
        ),
        estimated_exit_fee_resolver=(
            inputs.estimated_exit_fee_resolver
        ),
        realized_quotes_resolver=(
            inputs.realized_quotes_resolver
        ),
        execution_evidence_resolver=(
            inputs.execution_evidence_resolver
        ),
        realized_evidence_resolver=(
            inputs.realized_evidence_resolver
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
