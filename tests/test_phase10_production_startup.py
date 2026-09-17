from types import SimpleNamespace

import pytest

from src.accounting.production_fx_scheduler import (
    ParallelProductionFxResolver,
)
from src.accounting.production_startup import (
    FX_PREFETCH_BUDGET_ABOVE_50_PERCENT,
    PHASE10_ACCOUNTING_FLAGS_NOT_ENABLED,
    PHASE10_GLOBAL_CONFIG_SCHEMA,
    Phase10AccountingRuntimePolicy,
    Phase10StartupPolicyError,
    build_phase10_startup_metadata,
    wire_phase10_production_runtime,
)
from src.accounting.runtime_integration import (
    SnapshotCaptureDecisionProvider,
)
from src.execution.models import (
    PaperMode,
)


def policy(
    **overrides,
):
    values = {
        "realized_market_max_age_seconds": 7200,
        "realized_daily_reference_max_age_days": 7,
        "fx_prefetch_timeout_seconds": 4,
        "fx_prefetch_max_workers": 3,
        "cycle_timeout_seconds": 20,
    }

    values.update(
        overrides
    )

    return Phase10AccountingRuntimePolicy(
        **values
    )


class FakeFlags:
    def __init__(
        self,
        *,
        execution=True,
        execution_orders=True,
        fx=True,
        pln=True,
    ):
        self.values = {
            "AL_TRADING_REALISTIC_V2_ENABLED": (
                execution
            ),
            "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED": (
                execution_orders
            ),
            "AL_TRADING_FX_ENABLED": fx,
            "AL_TRADING_PLN_ACCOUNTING_ENABLED": pln,
        }

    def fingerprint_flags(
        self,
    ):
        return dict(
            self.values
        )


class FakeBroker:
    def __init__(
        self,
        execution_hash="a" * 64,
    ):
        self.execution_hash = (
            execution_hash
        )
        self.trading_fee_rate = 0.0004
        self.calls = []

    def config_hash_for(
        self,
        paper_mode,
    ):
        self.calls.append(
            paper_mode
        )

        return self.execution_hash


class Delegate:
    def __call__(
        self,
        *,
        asset_id,
        snapshot,
        position,
    ):
        return "UNCHANGED"


class FakeRuntime:
    def __init__(
        self,
        *,
        broker,
    ):
        self.broker = broker
        self.decision_provider = (
            Delegate()
        )
        self.paper_mode = (
            PaperMode.REALISTIC_PAPER
        )
        self.clock = SimpleNamespace(
            now=lambda: None
        )
        self.positions = {}

    def run_cycle(
        self,
        asset_ids,
    ):
        return SimpleNamespace(
            results={},
        )


def test_policy_fingerprints_accepted_mtm_freshness_and_explicit_runtime_values():
    value = policy()

    payload = (
        value.fingerprint_payload()
    )

    assert (
        payload["schema"]
        == PHASE10_GLOBAL_CONFIG_SCHEMA
    )

    assert (
        payload[
            "mtm_weekday_max_fx_age_seconds"
        ]
        == 7200.0
    )

    assert (
        payload[
            "mtm_weekend_max_fx_age_seconds"
        ]
        == 7200.0
    )

    assert (
        payload[
            "fx_unavailable_after_seconds"
        ]
        == 345600.0
    )

    assert (
        payload[
            "realized_daily_reference_max_age_days"
        ]
        == 7
    )

    assert (
        payload[
            "fx_prefetch_timeout_seconds"
        ]
        == 4.0
    )

    assert (
        payload[
            "fx_prefetch_max_workers"
        ]
        == 3
    )

    assert (
        payload[
            "cycle_timeout_seconds"
        ]
        == 20.0
    )


@pytest.mark.parametrize(
    "kwargs,match",
    [
        (
            {
                "realized_market_max_age_seconds": 0,
            },
            "realized_market_max_age_seconds",
        ),
        (
            {
                "realized_daily_reference_max_age_days": 0,
            },
            "realized_daily_reference_max_age_days",
        ),
        (
            {
                "realized_daily_reference_max_age_days": 1.5,
            },
            "realized_daily_reference_max_age_days",
        ),
        (
            {
                "fx_prefetch_timeout_seconds": 0,
            },
            "fx_prefetch_timeout_seconds",
        ),
        (
            {
                "fx_prefetch_max_workers": 0,
            },
            "fx_prefetch_max_workers",
        ),
        (
            {
                "cycle_timeout_seconds": 0,
            },
            "cycle_timeout_seconds",
        ),
        (
            {
                "fx_prefetch_timeout_seconds": 20,
                "cycle_timeout_seconds": 20,
            },
            "strictly less",
        ),
        (
            {
                "fx_prefetch_timeout_seconds": 21,
                "cycle_timeout_seconds": 20,
            },
            "strictly less",
        ),
    ],
)
def test_policy_fails_closed_for_invalid_values(
    kwargs,
    match,
):
    with pytest.raises(
        Phase10StartupPolicyError,
        match=match,
    ):
        policy(
            **kwargs
        )


def test_policy_labels_prefetch_budget_above_half():
    value = policy(
        fx_prefetch_timeout_seconds=11,
        cycle_timeout_seconds=20,
    )

    assert (
        value.prefetch_budget_fraction
        == pytest.approx(
            0.55
        )
    )

    assert (
        value.limitations
        == (
            FX_PREFETCH_BUDGET_ABOVE_50_PERCENT,
        )
    )


def test_policy_at_exactly_half_has_no_warning():
    value = policy(
        fx_prefetch_timeout_seconds=10,
        cycle_timeout_seconds=20,
    )

    assert value.limitations == ()


def test_startup_metadata_keeps_execution_hash_separate_and_builds_phase10_hash():
    broker = FakeBroker(
        "b" * 64
    )

    metadata = (
        build_phase10_startup_metadata(
            broker=broker,
            paper_mode=(
                PaperMode.REALISTIC_PAPER
            ),
            runtime_flags=FakeFlags(),
            policy=policy(),
        )
    )

    assert (
        metadata.execution_config_hash
        == "b" * 64
    )

    assert (
        metadata.global_config_hash
        != metadata.execution_config_hash
    )

    assert len(
        metadata.base_global_config_hash
    ) == 64

    assert len(
        metadata.global_config_hash
    ) == 64

    assert (
        metadata.schema
        == PHASE10_GLOBAL_CONFIG_SCHEMA
    )

    assert (
        metadata.paper_mode
        == PaperMode.REALISTIC_PAPER.value
    )

    assert (
        metadata.runtime_policy[
            "fx_prefetch_timeout_seconds"
        ]
        == 4.0
    )


def test_startup_hash_is_deterministic():
    first = (
        build_phase10_startup_metadata(
            broker=FakeBroker(),
            paper_mode=(
                PaperMode.REALISTIC_PAPER
            ),
            runtime_flags=FakeFlags(),
            policy=policy(),
        )
    )

    second = (
        build_phase10_startup_metadata(
            broker=FakeBroker(),
            paper_mode=(
                PaperMode.REALISTIC_PAPER
            ),
            runtime_flags=FakeFlags(),
            policy=policy(),
        )
    )

    assert (
        first.global_config_hash
        == second.global_config_hash
    )


def test_startup_hash_changes_with_runtime_policy():
    first = (
        build_phase10_startup_metadata(
            broker=FakeBroker(),
            paper_mode=(
                PaperMode.REALISTIC_PAPER
            ),
            runtime_flags=FakeFlags(),
            policy=policy(),
        )
    )

    second = (
        build_phase10_startup_metadata(
            broker=FakeBroker(),
            paper_mode=(
                PaperMode.REALISTIC_PAPER
            ),
            runtime_flags=FakeFlags(),
            policy=policy(
                fx_prefetch_timeout_seconds=5,
            ),
        )
    )

    assert (
        first.global_config_hash
        != second.global_config_hash
    )


def test_startup_hash_changes_with_feature_flags():
    first = (
        build_phase10_startup_metadata(
            broker=FakeBroker(),
            paper_mode=(
                PaperMode.REALISTIC_PAPER
            ),
            runtime_flags=FakeFlags(),
            policy=policy(),
        )
    )

    second = (
        build_phase10_startup_metadata(
            broker=FakeBroker(),
            paper_mode=(
                PaperMode.REALISTIC_PAPER
            ),
            runtime_flags=FakeFlags(
                pln=False
            ),
            policy=policy(),
        )
    )

    assert (
        first.global_config_hash
        != second.global_config_hash
    )


@pytest.mark.parametrize(
    "flag_name,kwargs",
    [
        (
            "AL_TRADING_REALISTIC_V2_ENABLED",
            {
                "execution": False,
            },
        ),
        (
            "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED",
            {
                "execution_orders": False,
            },
        ),
        (
            "AL_TRADING_FX_ENABLED",
            {
                "fx": False,
            },
        ),
        (
            "AL_TRADING_PLN_ACCOUNTING_ENABLED",
            {
                "pln": False,
            },
        ),
    ],
)
def test_production_wiring_requires_all_flags(
    flag_name,
    kwargs,
):
    broker = FakeBroker()

    runtime = FakeRuntime(
        broker=broker
    )

    original = (
        runtime.decision_provider
    )

    with pytest.raises(
        Phase10StartupPolicyError,
        match=(
            PHASE10_ACCOUNTING_FLAGS_NOT_ENABLED
        ),
    ) as excinfo:
        wire_phase10_production_runtime(
            runtime=runtime,
            broker=broker,
            runtime_flags=FakeFlags(
                **kwargs
            ),
            policy=policy(),
        )

    assert (
        flag_name
        in str(
            excinfo.value
        )
    )

    assert (
        runtime.decision_provider
        is original
    )


def test_production_wiring_uses_parallel_resolver_and_capture_wrapper():
    broker = FakeBroker(
        "c" * 64
    )

    runtime = FakeRuntime(
        broker=broker
    )

    original = (
        runtime.decision_provider
    )

    bundle = (
        wire_phase10_production_runtime(
            runtime=runtime,
            broker=broker,
            runtime_flags=FakeFlags(),
            policy=policy(),
        )
    )

    assert isinstance(
        bundle.wiring.fx_resolver,
        ParallelProductionFxResolver,
    )

    assert (
        bundle.wiring.fx_resolver
        .prefetch_timeout_seconds
        == 4.0
    )

    assert (
        bundle.wiring.fx_resolver
        .max_workers
        == 3
    )

    assert isinstance(
        runtime.decision_provider,
        SnapshotCaptureDecisionProvider,
    )

    assert (
        runtime.decision_provider.delegate
        is original
    )

    assert (
        bundle.startup_metadata
        .execution_config_hash
        == "c" * 64
    )

    assert (
        bundle.wiring.accounting_runtime
        .cash_pln_resolver
        is None
    )


def test_production_wiring_rejects_runtime_broker_mismatch_before_wrapping():
    broker = FakeBroker()

    runtime = FakeRuntime(
        broker=FakeBroker()
    )

    original = (
        runtime.decision_provider
    )

    with pytest.raises(
        Phase10StartupPolicyError,
        match="RUNTIME_BROKER_MISMATCH",
    ):
        wire_phase10_production_runtime(
            runtime=runtime,
            broker=broker,
            runtime_flags=FakeFlags(),
            policy=policy(),
        )

    assert (
        runtime.decision_provider
        is original
    )
