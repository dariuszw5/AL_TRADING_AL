from __future__ import annotations

import os
from dataclasses import dataclass

from .models import PaperMode


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
    name: str,
    value: str | None,
    *,
    default: bool,
) -> bool:
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


def _parse_paper_mode(
    value: str | None,
) -> PaperMode:
    if value is None:
        return PaperMode.REALISTIC_PAPER

    normalized = (
        str(value)
        .strip()
        .lower()
    )

    for mode in PaperMode:
        if mode.value.lower() == normalized:
            return mode

    raise ValueError(
        "AL_TRADING_REALISTIC_V2_PAPER_MODE "
        "must be realistic_paper or research_paper"
    )


@dataclass(frozen=True)
class RealisticV2FeatureFlags:
    """
    REALISTIC_V2 is fail-closed.

    Merely importing the execution package never
    enables the new runtime.
    """

    enabled: bool = False
    execution_enabled: bool = False

    paper_mode: PaperMode = (
        PaperMode.REALISTIC_PAPER
    )

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

        enabled = _parse_bool(
            "AL_TRADING_REALISTIC_V2_ENABLED",
            source.get(
                "AL_TRADING_REALISTIC_V2_ENABLED"
            ),
            default=False,
        )

        execution_enabled = _parse_bool(
            "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED",
            source.get(
                "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED"
            ),
            default=False,
        )

        paper_mode = _parse_paper_mode(
            source.get(
                "AL_TRADING_REALISTIC_V2_PAPER_MODE"
            )
        )

        return cls(
            enabled=enabled,
            execution_enabled=execution_enabled,
            paper_mode=paper_mode,
        )
