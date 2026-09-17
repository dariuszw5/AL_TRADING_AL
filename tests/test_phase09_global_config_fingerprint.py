import pytest

from scripts.run_realistic_v2_execution_benchmark import run_benchmark
from src.accounting.feature_flags import PlnAccountingFeatureFlags
from src.config_fingerprint import (
    asset_registry_hash,
    build_phase09_feature_flags,
    global_config_hash,
    normalized_asset_registry,
)
from src.data.assets import SUPPORTED_ASSETS
from src.execution.models import PaperMode


def test_pln_accounting_flag_defaults_off():
    flags = PlnAccountingFeatureFlags.from_env({})
    assert flags.enabled is False


def test_pln_accounting_flag_explicit_enable():
    flags = PlnAccountingFeatureFlags.from_env(
        {"AL_TRADING_PLN_ACCOUNTING_ENABLED": "1"}
    )
    assert flags.enabled is True


def test_pln_accounting_flag_invalid_value_fails_closed():
    with pytest.raises(
        ValueError,
        match="AL_TRADING_PLN_ACCOUNTING_ENABLED",
    ):
        PlnAccountingFeatureFlags.from_env(
            {"AL_TRADING_PLN_ACCOUNTING_ENABLED": "maybe"}
        )


def test_normalized_asset_registry_is_order_independent():
    forward = normalized_asset_registry(SUPPORTED_ASSETS)
    reverse = normalized_asset_registry(
        tuple(reversed(SUPPORTED_ASSETS))
    )
    assert forward == reverse


def test_normalized_asset_registry_uses_canonical_asset_ids():
    payload = normalized_asset_registry(SUPPORTED_ASSETS)

    assert tuple(
        item["asset_id"]
        for item in payload
    ) == (
        "AAPL",
        "BNBUSDT",
        "BTCUSDT",
        "ETHUSDT",
        "EURUSD",
        "GOLD_FUT_CONT",
        "SOLUSDT",
        "WTI_FUT_CONT",
        "XRPUSDT",
    )


def test_asset_registry_hash_is_deterministic():
    first = asset_registry_hash(SUPPORTED_ASSETS)
    second = asset_registry_hash(
        tuple(reversed(SUPPORTED_ASSETS))
    )
    assert first == second
    assert len(first) == 64


def test_asset_registry_hash_changes_when_registry_changes():
    reduced = tuple(
        asset
        for asset in SUPPORTED_ASSETS
        if asset.asset_id != "AAPL"
    )

    assert (
        asset_registry_hash(SUPPORTED_ASSETS)
        != asset_registry_hash(reduced)
    )


def _base_feature_flags():
    return build_phase09_feature_flags(
        realistic_v2_enabled=True,
        realistic_v2_execution_enabled=True,
        fx_enabled=False,
        pln_accounting_enabled=False,
    )


def _global_hash(
    *,
    execution_config_hash="0" * 64,
    feature_flags=None,
    paper_mode=PaperMode.REALISTIC_PAPER,
    assets=SUPPORTED_ASSETS,
):
    return global_config_hash(
        execution_config_hash=execution_config_hash,
        paper_mode=paper_mode,
        feature_flags=(
            _base_feature_flags()
            if feature_flags is None
            else feature_flags
        ),
        assets=assets,
    )


def test_global_config_hash_is_deterministic():
    assert _global_hash() == _global_hash()
    assert len(_global_hash()) == 64


def test_global_config_hash_changes_with_execution_config_hash():
    assert (
        _global_hash(execution_config_hash="0" * 64)
        != _global_hash(execution_config_hash="1" * 64)
    )


def test_global_config_hash_changes_with_fx_flag():
    flags = _base_feature_flags()
    changed = dict(flags)
    changed["AL_TRADING_FX_ENABLED"] = True

    assert (
        _global_hash(feature_flags=flags)
        != _global_hash(feature_flags=changed)
    )


def test_global_config_hash_changes_with_pln_flag():
    flags = _base_feature_flags()
    changed = dict(flags)
    changed["AL_TRADING_PLN_ACCOUNTING_ENABLED"] = True

    assert (
        _global_hash(feature_flags=flags)
        != _global_hash(feature_flags=changed)
    )


def test_global_config_hash_changes_with_paper_mode():
    assert (
        _global_hash(paper_mode=PaperMode.REALISTIC_PAPER)
        != _global_hash(paper_mode=PaperMode.RESEARCH_PAPER)
    )


def test_global_config_hash_changes_with_registry():
    reduced = tuple(
        asset
        for asset in SUPPORTED_ASSETS
        if asset.asset_id != "AAPL"
    )

    assert (
        _global_hash(assets=SUPPORTED_ASSETS)
        != _global_hash(assets=reduced)
    )


def test_global_hash_rejects_invalid_execution_hash():
    with pytest.raises(
        ValueError,
        match="execution_config_hash",
    ):
        global_config_hash(
            execution_config_hash="not-a-sha256",
            paper_mode=PaperMode.REALISTIC_PAPER,
            feature_flags=_base_feature_flags(),
            assets=SUPPORTED_ASSETS,
        )


def test_feature_flag_payload_contains_phase09_flags():
    assert _base_feature_flags() == {
        "AL_TRADING_REALISTIC_V2_ENABLED": True,
        "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED": True,
        "AL_TRADING_FX_ENABLED": False,
        "AL_TRADING_PLN_ACCOUNTING_ENABLED": False,
    }


def test_feature_flag_payload_rejects_unresolved_string_values():
    with pytest.raises(
        TypeError,
        match="fx_enabled must be bool",
    ):
        build_phase09_feature_flags(
            realistic_v2_enabled=True,
            realistic_v2_execution_enabled=True,
            fx_enabled="false",
            pln_accounting_enabled=False,
        )


def test_realistic_v2_benchmark_has_global_config_metadata():
    result = run_benchmark()
    metadata = result["benchmark_metadata"]

    assert metadata["metadata_schema"] == "phase09-a11-v1"
    assert metadata["execution_profile"] == "REALISTIC_V2"
    assert metadata["paper_mode"] == "realistic_paper"

    assert (
        metadata["execution_config_hash"]
        == result["entry_config_hash"]
        == result["exit_config_hash"]
    )

    assert len(metadata["asset_registry_hash"]) == 64
    assert len(metadata["global_config_hash"]) == 64

    assert metadata["feature_flags"] == {
        "AL_TRADING_REALISTIC_V2_ENABLED": True,
        "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED": True,
        "AL_TRADING_FX_ENABLED": False,
        "AL_TRADING_PLN_ACCOUNTING_ENABLED": False,
    }


def test_benchmark_global_hash_rebuilds_exactly():
    result = run_benchmark()
    metadata = result["benchmark_metadata"]

    rebuilt = global_config_hash(
        execution_config_hash=(
            metadata["execution_config_hash"]
        ),
        paper_mode=metadata["paper_mode"],
        feature_flags=metadata["feature_flags"],
        assets=SUPPORTED_ASSETS,
    )

    assert rebuilt == metadata["global_config_hash"]


def test_paper_broker_execution_hash_contract_remains_separate():
    result = run_benchmark()
    metadata = result["benchmark_metadata"]

    assert (
        result["entry_config_hash"]
        == metadata["execution_config_hash"]
    )
    assert (
        result["entry_config_hash"]
        != metadata["global_config_hash"]
    )