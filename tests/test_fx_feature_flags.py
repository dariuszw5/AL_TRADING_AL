import pytest

from src.fx.feature_flags import (
    FxFeatureFlags,
)


def test_fx_feature_flag_defaults_off():
    flags = FxFeatureFlags.from_env(
        {}
    )

    assert flags.enabled is False


def test_fx_feature_flag_can_be_enabled():
    flags = FxFeatureFlags.from_env(
        {
            "AL_TRADING_FX_ENABLED": "1",
        }
    )

    assert flags.enabled is True


def test_fx_feature_flag_rejects_invalid_value():
    with pytest.raises(
        ValueError,
        match="AL_TRADING_FX_ENABLED",
    ):
        FxFeatureFlags.from_env(
            {
                "AL_TRADING_FX_ENABLED": "maybe",
            }
        )
