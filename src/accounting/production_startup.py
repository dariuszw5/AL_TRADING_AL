from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from src.accounting.production_fx_scheduler import (
    ParallelProductionFxResolver,
)
from src.accounting.production_resolvers import (
    BrokerExitFeeEstimator,
    Phase10ProductionAccountingRuntime,
    Phase10ProductionAccountingWiring,
)
from src.accounting.runtime_bridge import (
    Phase09RuntimeAccountingBridge,
)
from src.accounting.runtime_integration import (
    Phase09AccountingRuntime,
    SnapshotCaptureDecisionProvider,
)
from src.config_fingerprint import (
    asset_registry_hash,
    global_config_hash,
)
from src.core.clock import (
    SystemClock,
)
from src.data.assets import (
    SUPPORTED_ASSETS,
)
from src.fx.freshness import (
    production_fx_freshness_policy,
)
from src.fx.realized_booking import (
    RealizedFxBooker,
)
from src.fx.realized_selection import (
    RealizedFxSelectionPolicy,
)


PHASE10_GLOBAL_CONFIG_SCHEMA = (
    "phase10-accounting-runtime-v1"
)

FX_PREFETCH_BUDGET_ABOVE_50_PERCENT = (
    "FX_PREFETCH_BUDGET_ABOVE_50_PERCENT"
)

PHASE10_ACCOUNTING_FLAGS_NOT_ENABLED = (
    "PHASE10_ACCOUNTING_FLAGS_NOT_ENABLED"
)


class Phase10StartupPolicyError(
    ValueError
):
    pass


def _positive_float(
    value,
    field_name,
):
    try:
        result = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise Phase10StartupPolicyError(
            f"{field_name} must be a positive finite number"
        ) from exc

    if (
        not math.isfinite(
            result
        )
        or result <= 0
    ):
        raise Phase10StartupPolicyError(
            f"{field_name} must be a positive finite number"
        )

    return result


def _positive_int(
    value,
    field_name,
):
    if isinstance(
        value,
        bool,
    ):
        raise Phase10StartupPolicyError(
            f"{field_name} must be a positive integer"
        )

    try:
        numeric = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise Phase10StartupPolicyError(
            f"{field_name} must be a positive integer"
        ) from exc

    if (
        not math.isfinite(
            numeric
        )
        or not numeric.is_integer()
    ):
        raise Phase10StartupPolicyError(
            f"{field_name} must be a positive integer"
        )

    result = int(
        numeric
    )

    if result <= 0:
        raise Phase10StartupPolicyError(
            f"{field_name} must be a positive integer"
        )

    return result


def _paper_mode_text(
    paper_mode,
):
    value = getattr(
        paper_mode,
        "value",
        paper_mode,
    )

    result = str(
        value
    ).strip()

    if not result:
        raise Phase10StartupPolicyError(
            "paper_mode is required"
        )

    return result


def _sha256_payload(
    payload,
):
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
        allow_nan=False,
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        encoded
    ).hexdigest()


@dataclass(frozen=True)
class Phase10AccountingRuntimePolicy:
    """
    Explicit production accounting policy.

    No default is supplied for the realized daily-reference age.
    The caller must choose it intentionally.

    The accepted Phase 09 MTM freshness thresholds are read from the
    frozen production FX freshness policy and included in the startup
    fingerprint.
    """

    realized_market_max_age_seconds: float
    realized_daily_reference_max_age_days: int
    fx_prefetch_timeout_seconds: float
    fx_prefetch_max_workers: int
    cycle_timeout_seconds: float

    def __post_init__(
        self,
    ):
        market_age = (
            _positive_float(
                self.realized_market_max_age_seconds,
                "realized_market_max_age_seconds",
            )
        )

        reference_days = (
            _positive_int(
                self.realized_daily_reference_max_age_days,
                "realized_daily_reference_max_age_days",
            )
        )

        prefetch_timeout = (
            _positive_float(
                self.fx_prefetch_timeout_seconds,
                "fx_prefetch_timeout_seconds",
            )
        )

        workers = (
            _positive_int(
                self.fx_prefetch_max_workers,
                "fx_prefetch_max_workers",
            )
        )

        cycle_timeout = (
            _positive_float(
                self.cycle_timeout_seconds,
                "cycle_timeout_seconds",
            )
        )

        if (
            prefetch_timeout
            >= cycle_timeout
        ):
            raise Phase10StartupPolicyError(
                "fx_prefetch_timeout_seconds must be "
                "strictly less than cycle_timeout_seconds"
            )

        object.__setattr__(
            self,
            "realized_market_max_age_seconds",
            market_age,
        )

        object.__setattr__(
            self,
            "realized_daily_reference_max_age_days",
            reference_days,
        )

        object.__setattr__(
            self,
            "fx_prefetch_timeout_seconds",
            prefetch_timeout,
        )

        object.__setattr__(
            self,
            "fx_prefetch_max_workers",
            workers,
        )

        object.__setattr__(
            self,
            "cycle_timeout_seconds",
            cycle_timeout,
        )

    @property
    def prefetch_budget_fraction(
        self,
    ):
        return (
            self.fx_prefetch_timeout_seconds
            / self.cycle_timeout_seconds
        )

    @property
    def limitations(
        self,
    ):
        if (
            self.prefetch_budget_fraction
            > 0.5
        ):
            return (
                FX_PREFETCH_BUDGET_ABOVE_50_PERCENT,
            )

        return ()

    def fingerprint_payload(
        self,
    ):
        freshness = (
            production_fx_freshness_policy()
        )

        return {
            "schema": (
                PHASE10_GLOBAL_CONFIG_SCHEMA
            ),
            "mtm_weekday_max_fx_age_seconds": (
                freshness.weekday_max_age_seconds
            ),
            "mtm_weekend_max_fx_age_seconds": (
                freshness.weekend_max_age_seconds
            ),
            "fx_unavailable_after_seconds": (
                freshness.unavailable_after_seconds
            ),
            "realized_market_max_age_seconds": (
                self.realized_market_max_age_seconds
            ),
            "realized_daily_reference_max_age_days": (
                self.realized_daily_reference_max_age_days
            ),
            "fx_prefetch_timeout_seconds": (
                self.fx_prefetch_timeout_seconds
            ),
            "fx_prefetch_max_workers": (
                self.fx_prefetch_max_workers
            ),
            "cycle_timeout_seconds": (
                self.cycle_timeout_seconds
            ),
        }


@dataclass(frozen=True)
class Phase10StartupMetadata:
    schema: str
    execution_config_hash: str
    base_global_config_hash: str
    global_config_hash: str
    asset_registry_hash: str
    paper_mode: str
    feature_flags: object
    runtime_policy: object
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class Phase10ProductionRuntimeBundle:
    wiring: Phase10ProductionAccountingWiring
    startup_metadata: Phase10StartupMetadata
    policy: Phase10AccountingRuntimePolicy


def _feature_flags(
    runtime_flags,
):
    fingerprint = getattr(
        runtime_flags,
        "fingerprint_flags",
        None,
    )

    if not callable(
        fingerprint
    ):
        raise TypeError(
            "runtime_flags.fingerprint_flags is required"
        )

    flags = dict(
        fingerprint()
    )

    for key, value in flags.items():
        if not isinstance(
            value,
            bool,
        ):
            raise TypeError(
                "runtime feature flags must resolve to bool"
            )

        if not str(
            key
        ).strip():
            raise TypeError(
                "runtime feature flag key is required"
            )

    return flags


def require_phase10_accounting_flags(
    runtime_flags,
):
    flags = _feature_flags(
        runtime_flags
    )

    required = (
        "AL_TRADING_REALISTIC_V2_ENABLED",
        "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED",
        "AL_TRADING_FX_ENABLED",
        "AL_TRADING_PLN_ACCOUNTING_ENABLED",
    )

    disabled = tuple(
        key
        for key in required
        if flags.get(
            key
        ) is not True
    )

    if disabled:
        raise Phase10StartupPolicyError(
            PHASE10_ACCOUNTING_FLAGS_NOT_ENABLED
            + ":"
            + ",".join(
                disabled
            )
        )

    return flags


def build_phase10_startup_metadata(
    *,
    broker,
    paper_mode,
    runtime_flags,
    policy,
    assets=SUPPORTED_ASSETS,
):
    if not isinstance(
        policy,
        Phase10AccountingRuntimePolicy,
    ):
        raise TypeError(
            "policy must be Phase10AccountingRuntimePolicy"
        )

    if broker is None:
        raise TypeError(
            "broker is required"
        )

    config_hash_for = getattr(
        broker,
        "config_hash_for",
        None,
    )

    if not callable(
        config_hash_for
    ):
        raise TypeError(
            "broker.config_hash_for is required"
        )

    flags = _feature_flags(
        runtime_flags
    )

    execution_hash = str(
        config_hash_for(
            paper_mode
        )
    ).strip().lower()

    base_hash = (
        global_config_hash(
            execution_config_hash=(
                execution_hash
            ),
            paper_mode=paper_mode,
            feature_flags=flags,
            assets=assets,
        )
    )

    policy_payload = (
        policy.fingerprint_payload()
    )

    phase10_payload = {
        "schema": (
            PHASE10_GLOBAL_CONFIG_SCHEMA
        ),
        "base_global_config_hash": (
            base_hash
        ),
        "runtime_policy": (
            policy_payload
        ),
    }

    phase10_hash = (
        _sha256_payload(
            phase10_payload
        )
    )

    return Phase10StartupMetadata(
        schema=(
            PHASE10_GLOBAL_CONFIG_SCHEMA
        ),
        execution_config_hash=(
            execution_hash
        ),
        base_global_config_hash=(
            base_hash
        ),
        global_config_hash=(
            phase10_hash
        ),
        asset_registry_hash=(
            asset_registry_hash(
                assets
            )
        ),
        paper_mode=(
            _paper_mode_text(
                paper_mode
            )
        ),
        feature_flags=(
            MappingProxyType(
                dict(
                    flags
                )
            )
        ),
        runtime_policy=(
            MappingProxyType(
                dict(
                    policy_payload
                )
            )
        ),
        limitations=(
            policy.limitations
        ),
    )


def wire_phase10_production_runtime(
    *,
    runtime,
    broker,
    runtime_flags,
    policy,
    clock=None,
    nbp_provider=None,
    yahoo_provider=None,
    coinbase_provider=None,
    cash_pln_resolver=None,
    assets=SUPPORTED_ASSETS,
):
    """
    Construct the bounded, fingerprinted production accounting wrapper.

    This function does not enable an entrypoint. The caller must already
    have resolved and enabled all four Phase 10 feature flags.
    """

    if runtime is None:
        raise TypeError(
            "runtime is required"
        )

    if broker is None:
        raise TypeError(
            "broker is required"
        )

    if not isinstance(
        policy,
        Phase10AccountingRuntimePolicy,
    ):
        raise TypeError(
            "policy must be Phase10AccountingRuntimePolicy"
        )

    require_phase10_accounting_flags(
        runtime_flags
    )

    runtime_broker = getattr(
        runtime,
        "broker",
        broker,
    )

    if runtime_broker is not broker:
        raise Phase10StartupPolicyError(
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
        raise Phase10StartupPolicyError(
            "RUNTIME_DECISION_PROVIDER_REQUIRED"
        )

    if isinstance(
        delegate,
        SnapshotCaptureDecisionProvider,
    ):
        raise Phase10StartupPolicyError(
            "RUNTIME_ALREADY_ACCOUNTING_WRAPPED"
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

    paper_mode = getattr(
        runtime,
        "paper_mode",
        None,
    )

    if paper_mode is None:
        raise Phase10StartupPolicyError(
            "RUNTIME_PAPER_MODE_REQUIRED"
        )

    metadata = (
        build_phase10_startup_metadata(
            broker=broker,
            paper_mode=paper_mode,
            runtime_flags=runtime_flags,
            policy=policy,
            assets=assets,
        )
    )

    fx_resolver = (
        ParallelProductionFxResolver(
            prefetch_timeout_seconds=(
                policy.fx_prefetch_timeout_seconds
            ),
            max_workers=(
                policy.fx_prefetch_max_workers
            ),
            clock=resolved_clock,
            nbp_provider=nbp_provider,
            yahoo_provider=yahoo_provider,
            coinbase_provider=(
                coinbase_provider
            ),
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
                    market_max_age_seconds=(
                        policy
                        .realized_market_max_age_seconds
                    ),
                    daily_reference_max_age_days=(
                        policy
                        .realized_daily_reference_max_age_days
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

    wiring = (
        Phase10ProductionAccountingWiring(
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
            fx_resolver=(
                fx_resolver
            ),
            exit_fee_estimator=(
                exit_fee_estimator
            ),
        )
    )

    return Phase10ProductionRuntimeBundle(
        wiring=wiring,
        startup_metadata=(
            metadata
        ),
        policy=policy,
    )
