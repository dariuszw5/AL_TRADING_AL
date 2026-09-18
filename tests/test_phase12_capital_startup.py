from types import (
    MappingProxyType,
    SimpleNamespace,
)

import pytest

from src.data.assets import (
    get_asset,
)
from src.execution.capital_feature_flags import (
    CapitalAdmissionFeatureFlags,
)
from src.execution.capital_startup import (
    PHASE12_CAPITAL_ADMISSION_FLAG_NOT_ENABLED,
    PHASE12_CAPITAL_LIMIT_FORMULA,
    PHASE12_CAPITAL_SOURCE,
    PHASE12_CONTROLLED_ASSET,
    PHASE12_ENTRY_FEE_SEMANTICS,
    PHASE12_EXECUTION_PRICE_BASIS,
    PHASE12_FX_FRESHNESS_REQUIRED,
    PHASE12_FX_PATH,
    PHASE12_GLOBAL_CONFIG_SCHEMA,
    PHASE12_PROPOSED_EXPOSURE_BASIS,
    Phase12CapitalAdmissionPolicy,
    Phase12StartupPolicyError,
    build_phase12_startup_metadata,
)


def phase10_metadata():
    return SimpleNamespace(
        execution_config_hash=(
            "a8c84046f4919a1c39bcaef86e926a2"
            "87240b14359b9b60b7f626252f7c5e781"
        ),
        global_config_hash=(
            "017d9e3ef4fba21bc17102519cf6b499"
            "4dd50ae3f53a4f05b178b5913fd9127d"
        ),
        asset_registry_hash=(
            "71ddae6f81cdd829caf2431881ee513f"
            "0424553c959625f5e843d4cf3e7fc714"
        ),
        paper_mode="realistic_paper",
        feature_flags=MappingProxyType(
            {
                "AL_TRADING_REALISTIC_V2_ENABLED": True,
                "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED": True,
                "AL_TRADING_FX_ENABLED": True,
                "AL_TRADING_PLN_ACCOUNTING_ENABLED": True,
            }
        ),
        runtime_policy=MappingProxyType(
            {
                "schema": "phase10-accounting-runtime-v1",
                "cycle_timeout_seconds": 20.0,
            }
        ),
        limitations=(),
    )


def capital_policy(
    *,
    max_exposure_percent=None,
):
    if max_exposure_percent is None:
        return (
            Phase12CapitalAdmissionPolicy
            .from_asset(
                get_asset("BTCUSDT")
            )
        )

    return Phase12CapitalAdmissionPolicy(
        controlled_asset_id="BTCUSDT",
        max_exposure_percent=max_exposure_percent,
    )


def enabled_flags():
    return CapitalAdmissionFeatureFlags(
        enabled=True
    )


def test_capital_feature_flag_defaults_disabled():
    flags = (
        CapitalAdmissionFeatureFlags
        .from_env({})
    )

    assert flags.enabled is False


@pytest.mark.parametrize(
    "value",
    ["1", "true", "yes", "on", "TRUE"],
)
def test_capital_feature_flag_accepts_true_values(
    value,
):
    flags = (
        CapitalAdmissionFeatureFlags
        .from_env(
            {
                "AL_TRADING_CAPITAL_ADMISSION_ENABLED": value
            }
        )
    )

    assert flags.enabled is True


@pytest.mark.parametrize(
    "value",
    ["", "0", "false", "no", "off"],
)
def test_capital_feature_flag_accepts_false_values(
    value,
):
    flags = (
        CapitalAdmissionFeatureFlags
        .from_env(
            {
                "AL_TRADING_CAPITAL_ADMISSION_ENABLED": value
            }
        )
    )

    assert flags.enabled is False


def test_invalid_capital_feature_flag_fails_closed():
    with pytest.raises(
        ValueError,
        match="AL_TRADING_CAPITAL_ADMISSION_ENABLED",
    ):
        (
            CapitalAdmissionFeatureFlags
            .from_env(
                {
                    "AL_TRADING_CAPITAL_ADMISSION_ENABLED": "maybe"
                }
            )
        )


def test_policy_is_derived_from_btc_asset_registry():
    asset = get_asset("BTCUSDT")

    policy = (
        Phase12CapitalAdmissionPolicy
        .from_asset(asset)
    )

    assert (
        policy.controlled_asset_id
        == PHASE12_CONTROLLED_ASSET
    )
    assert (
        policy.max_exposure_percent
        == asset.risk.max_exposure_percent
    )


def test_policy_freezes_approved_semantics():
    policy = capital_policy()

    assert policy.capital_source == PHASE12_CAPITAL_SOURCE
    assert (
        policy.capital_limit_formula
        == PHASE12_CAPITAL_LIMIT_FORMULA
    )
    assert (
        policy.proposed_exposure_basis
        == PHASE12_PROPOSED_EXPOSURE_BASIS
    )
    assert (
        policy.execution_price_basis
        == PHASE12_EXECUTION_PRICE_BASIS
    )
    assert policy.fx_path == PHASE12_FX_PATH
    assert (
        policy.fx_freshness_required
        == PHASE12_FX_FRESHNESS_REQUIRED
    )
    assert (
        policy.entry_fee_semantics
        == PHASE12_ENTRY_FEE_SEMANTICS
    )
    assert policy.open_mutates_settled_cash is False
    assert (
        policy.exit_subject_to_capital_admission
        is False
    )
    assert policy.margin_model == "NONE"
    assert policy.collateral_model == "NONE"
    assert policy.leverage_model == "NONE"
    assert policy.short_financing_added is False


def test_disabled_capital_flag_blocks_phase12_metadata():
    with pytest.raises(
        Phase12StartupPolicyError,
        match=(
            PHASE12_CAPITAL_ADMISSION_FLAG_NOT_ENABLED
        ),
    ):
        build_phase12_startup_metadata(
            phase10_metadata=phase10_metadata(),
            capital_flags=(
                CapitalAdmissionFeatureFlags(
                    enabled=False
                )
            ),
            capital_policy=capital_policy(),
        )


def test_phase12_metadata_preserves_phase10_and_adds_capital_fingerprint():
    metadata = build_phase12_startup_metadata(
        phase10_metadata=phase10_metadata(),
        capital_flags=enabled_flags(),
        capital_policy=capital_policy(),
    )

    original = phase10_metadata()

    assert metadata.schema == PHASE12_GLOBAL_CONFIG_SCHEMA
    assert (
        metadata.execution_config_hash
        == original.execution_config_hash
    )
    assert (
        metadata.phase10_global_config_hash
        == original.global_config_hash
    )
    assert (
        metadata.asset_registry_hash
        == original.asset_registry_hash
    )
    assert metadata.paper_mode == "realistic_paper"
    assert (
        metadata.phase12_feature_flags[
            "AL_TRADING_CAPITAL_ADMISSION_ENABLED"
        ]
        is True
    )
    assert (
        metadata.capital_policy["capital_source"]
        == PHASE12_CAPITAL_SOURCE
    )


def test_phase12_hash_is_deterministic():
    first = build_phase12_startup_metadata(
        phase10_metadata=phase10_metadata(),
        capital_flags=enabled_flags(),
        capital_policy=capital_policy(),
    )

    second = build_phase12_startup_metadata(
        phase10_metadata=phase10_metadata(),
        capital_flags=enabled_flags(),
        capital_policy=capital_policy(),
    )

    assert first.global_config_hash == second.global_config_hash


def test_phase12_hash_changes_when_capital_limit_policy_changes():
    full = build_phase12_startup_metadata(
        phase10_metadata=phase10_metadata(),
        capital_flags=enabled_flags(),
        capital_policy=capital_policy(
            max_exposure_percent=100,
        ),
    )

    half = build_phase12_startup_metadata(
        phase10_metadata=phase10_metadata(),
        capital_flags=enabled_flags(),
        capital_policy=capital_policy(
            max_exposure_percent=50,
        ),
    )

    assert full.global_config_hash != half.global_config_hash


@pytest.mark.parametrize(
    "value",
    [0, -1, 100.01, float("nan"), float("inf")],
)
def test_invalid_phase12_max_exposure_is_rejected(
    value,
):
    with pytest.raises(
        Phase12StartupPolicyError,
        match="max_exposure_percent",
    ):
        capital_policy(
            max_exposure_percent=value,
        )


def test_non_btc_controlled_asset_is_rejected():
    with pytest.raises(
        Phase12StartupPolicyError,
        match="BTCUSDT",
    ):
        Phase12CapitalAdmissionPolicy(
            controlled_asset_id="ETHUSDT",
            max_exposure_percent=100,
        )


def test_margin_collateral_leverage_cannot_be_silently_enabled():
    with pytest.raises(
        Phase12StartupPolicyError,
        match="margin_model",
    ):
        Phase12CapitalAdmissionPolicy(
            controlled_asset_id="BTCUSDT",
            max_exposure_percent=100,
            margin_model="MARGIN",
        )

    with pytest.raises(
        Phase12StartupPolicyError,
        match="collateral_model",
    ):
        Phase12CapitalAdmissionPolicy(
            controlled_asset_id="BTCUSDT",
            max_exposure_percent=100,
            collateral_model="RESERVED",
        )

    with pytest.raises(
        Phase12StartupPolicyError,
        match="leverage_model",
    ):
        Phase12CapitalAdmissionPolicy(
            controlled_asset_id="BTCUSDT",
            max_exposure_percent=100,
            leverage_model="2X",
        )


def test_open_cash_mutation_and_exit_blocking_cannot_be_enabled():
    with pytest.raises(
        Phase12StartupPolicyError,
        match="OPEN",
    ):
        Phase12CapitalAdmissionPolicy(
            controlled_asset_id="BTCUSDT",
            max_exposure_percent=100,
            open_mutates_settled_cash=True,
        )

    with pytest.raises(
        Phase12StartupPolicyError,
        match="EXIT",
    ):
        Phase12CapitalAdmissionPolicy(
            controlled_asset_id="BTCUSDT",
            max_exposure_percent=100,
            exit_subject_to_capital_admission=True,
        )


def test_phase12_metadata_does_not_mutate_phase10_metadata():
    original = phase10_metadata()

    before_flags = dict(
        original.feature_flags
    )
    before_policy = dict(
        original.runtime_policy
    )

    build_phase12_startup_metadata(
        phase10_metadata=original,
        capital_flags=enabled_flags(),
        capital_policy=capital_policy(),
    )

    assert dict(original.feature_flags) == before_flags
    assert dict(original.runtime_policy) == before_policy
