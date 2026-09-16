from dataclasses import replace

import pytest

from src.agent.multi_asset_runner import MultiAssetPaperLive
from src.data.assets import (
    AssetClass,
    AssetConfig,
    ExecutionConfig,
    RiskConfig,
    ShortMechanism,
    StrategyConfig,
    ValidationStatus,
    asset_payload,
    get_asset,
    get_provider_config,
)


CANONICAL_ASSETS = {
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "GOLD_FUT_CONT",
    "WTI_FUT_CONT",
    "EURUSD",
    "AAPL",
}


def test_all_canonical_assets_exist():
    from src.data.assets import SUPPORTED_ASSETS

    assert {
        asset.asset_id
        for asset in SUPPORTED_ASSETS
    } == CANONICAL_ASSETS


def test_config_models_are_present():
    assert StrategyConfig
    assert RiskConfig
    assert ExecutionConfig
    assert AssetConfig


def test_asset_configs_do_not_share_nested_config_objects():
    btc = get_asset("BTCUSDT")
    eth = get_asset("ETHUSDT")

    assert btc.strategy is not eth.strategy
    assert btc.risk is not eth.risk
    assert btc.execution is not eth.execution


def test_invalid_config_fails_fast():
    btc = get_asset("BTCUSDT")

    with pytest.raises(ValueError):
        replace(
            btc,
            provider="provider_that_does_not_exist",
        )

    with pytest.raises(ValueError):
        replace(
            btc,
            tick_size=0.0,
        )


def test_short_mechanism_matches_allow_short():
    btc = get_asset("BTCUSDT")

    with pytest.raises(ValueError):
        replace(
            btc,
            allow_short=True,
            short_mechanism=ShortMechanism.NONE,
        )

    with pytest.raises(ValueError):
        replace(
            btc,
            allow_short=False,
            short_mechanism=ShortMechanism.SYNTHETIC,
            short_financing_model=None,
        )


def test_validated_requires_validation_reference():
    eth = get_asset("ETHUSDT")

    with pytest.raises(ValueError):
        replace(
            eth,
            validation_status=ValidationStatus.VALIDATED,
            validation_reference=None,
        )

    validated = replace(
        eth,
        validation_status=ValidationStatus.VALIDATED,
        validation_reference="tests/validation/ETHUSDT.md",
    )

    assert (
        validated.validation_status
        is ValidationStatus.VALIDATED
    )


def test_btc_frozen_config_is_unchanged():
    btc = get_asset("BTCUSDT")

    assert btc.asset_class is AssetClass.CRYPTO
    assert btc.validation_status is ValidationStatus.FROZEN

    runtime = MultiAssetPaperLive._config_for(btc)

    assert runtime.symbol == "BTCUSDT"
    assert runtime.interval == "1m"

    assert runtime.buy_rsi == 33.8
    assert runtime.sell_rsi == 68.5
    assert runtime.min_difference == 1.0
    assert runtime.rsi_method == "classic"

    assert runtime.risk_percent == 5.0
    assert runtime.stop_loss_percent == 5.0
    assert runtime.max_daily_loss_percent == 10.0
    assert runtime.max_exposure_percent == 100.0
    assert runtime.risk_reward_ratio == 2.0

    assert runtime.initial_balance == 1000.0
    assert runtime.trading_fee == 0.0004
    assert runtime.max_position_candles == 241


def test_gold_and_wti_have_canonical_proxy_identity():
    gold = get_asset("GOLD_FUT_CONT")
    wti = get_asset("WTI_FUT_CONT")

    assert gold.provider_symbol == "GC=F"
    assert wti.provider_symbol == "CL=F"

    assert (
        gold.instrument_type
        == "continuous_future_proxy"
    )
    assert (
        wti.instrument_type
        == "continuous_future_proxy"
    )

    assert (
        gold.validation_status
        is ValidationStatus.EXPERIMENTAL
    )
    assert (
        wti.validation_status
        is ValidationStatus.EXPERIMENTAL
    )


def test_legacy_proxy_names_are_aliases_only():
    gold = get_asset("XAUUSD")
    wti = get_asset("WTIUSD")

    assert gold.asset_id == "GOLD_FUT_CONT"
    assert wti.asset_id == "WTI_FUT_CONT"

    # Existing persisted state is not migrated in Phase 05.
    assert gold.state_key == "XAUUSD"
    assert wti.state_key == "WTIUSD"

    # Public payload uses truthful canonical identity.
    assert asset_payload(gold)["symbol"] == "GOLD_FUT_CONT"
    assert asset_payload(wti)["symbol"] == "WTI_FUT_CONT"


def test_every_non_btc_asset_is_experimental():
    from src.data.assets import SUPPORTED_ASSETS

    for asset in SUPPORTED_ASSETS:
        if asset.asset_id == "BTCUSDT":
            continue

        assert (
            asset.validation_status
            is ValidationStatus.EXPERIMENTAL
        )


def test_provider_metadata_is_centralized():
    yahoo = get_provider_config("yahoo")
    binance = get_provider_config("binance")

    assert yahoo.unofficial is True
    assert yahoo.degraded_by_design is True

    assert binance.unofficial is False


def test_proxy_cannot_be_promoted_above_experimental():
    gold = get_asset("GOLD_FUT_CONT")

    with pytest.raises(ValueError):
        replace(
            gold,
            validation_status=ValidationStatus.VALIDATED,
            validation_reference="not-allowed.md",
        )
