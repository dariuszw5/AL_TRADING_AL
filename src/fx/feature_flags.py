from __future__ import annotations

import os
from dataclasses import dataclass


_TRUE_VALUES = {
    "1",
    "true",
    "yes",
    "on",
}

_FALSE_VALUES = {
    "",
    "0",
    "false",
    "no",
    "off",
}


def _parse_bool(
    name,
    value,
    *,
    default,
):
    if value is None:
        return default

    normalized = (
        str(value)
        .strip()
        .lower()
    )

    if normalized in _TRUE_VALUES:
        return True

    if normalized in _FALSE_VALUES:
        return False

    raise ValueError(
        f"{name} must be one of "
        "1/0, true/false, yes/no, on/off"
    )


@dataclass(frozen=True)
class FxFeatureFlags:
    """
    Production FX integration remains fail-closed.
    """

    enabled: bool = False

    @classmethod
    def from_env(
        cls,
        env=None,
    ):
        source = (
            os.environ
            if env is None
            else env
        )

        return cls(
            enabled=_parse_bool(
                "AL_TRADING_FX_ENABLED",
                source.get(
                    "AL_TRADING_FX_ENABLED"
                ),
                default=False,
            )
        )
