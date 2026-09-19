from __future__ import annotations

from collections.abc import Mapping

from src.persistence.sqlite_cutover_seam import (
    CutoverMode,
    select_runtime_construction,
)
from src.persistence.sqlite_runtime_bundle import (
    build_sqlite_only_runtime_bundle,
)


class Phase14CutoverFactoryError(
    ValueError
):
    pass


_REQUIRED_SQLITE_BUNDLE_KEYS = frozenset(
    {
        "market_data_service",
        "market_session_service",
        "broker",
        "decision_provider",
        "clock",
        "paper_mode",
        "accounting_bridge",
        "fx_conversion_resolver",
        "estimated_exit_fee_resolver",
        "realized_quotes_resolver",
        "cycle_mapper_factory",
    }
)


def required_bundle_placeholders():
    """
    Test/helper surface for the exact Phase 13 bundle dependency contract.
    Values are placeholders only; production callers provide real objects.
    """

    return {
        key: object()
        for key in _REQUIRED_SQLITE_BUNDLE_KEYS
    }


def _validated_sqlite_bundle_kwargs(
    value,
):
    if value is None:
        raise Phase14CutoverFactoryError(
            "sqlite_bundle_kwargs are required in sqlite mode"
        )

    if not isinstance(
        value,
        Mapping,
    ):
        raise Phase14CutoverFactoryError(
            "sqlite_bundle_kwargs must be a mapping"
        )

    payload = dict(
        value
    )

    keys = set(
        payload
    )

    unexpected = (
        keys
        - _REQUIRED_SQLITE_BUNDLE_KEYS
    )

    if unexpected:
        raise Phase14CutoverFactoryError(
            "unexpected sqlite bundle keys: "
            + ", ".join(
                sorted(
                    unexpected
                )
            )
        )

    missing = (
        _REQUIRED_SQLITE_BUNDLE_KEYS
        - keys
    )

    if missing:
        raise Phase14CutoverFactoryError(
            "missing sqlite bundle keys: "
            + ", ".join(
                sorted(
                    missing
                )
            )
        )

    return payload


def build_phase14_runtime(
    *,
    legacy_builder,
    sqlite_database_path=None,
    live_database_path="data/live/trading.db",
    sqlite_bundle_kwargs=None,
    mode=CutoverMode.LEGACY,
):
    """
    Phase 14 construction boundary.

    Default mode delegates only to the legacy builder.

    Explicit SQLite mode passes through the A.2 path safety seam and,
    only after those checks succeed, constructs the real Phase 13
    SQLite-only runtime bundle.
    """

    selected_text = (
        mode.value
        if isinstance(
            mode,
            CutoverMode,
        )
        else str(
            mode
        )
    )

    sqlite_payload = None

    if selected_text == CutoverMode.SQLITE.value:
        sqlite_payload = (
            _validated_sqlite_bundle_kwargs(
                sqlite_bundle_kwargs
            )
        )

    def sqlite_builder(
        *,
        database_path,
        live_database_path,
    ):
        return build_sqlite_only_runtime_bundle(
            database_path=database_path,
            live_database_path=live_database_path,
            **sqlite_payload,
        )

    return select_runtime_construction(
        mode=mode,
        legacy_builder=legacy_builder,
        sqlite_builder=sqlite_builder,
        sqlite_database_path=sqlite_database_path,
        live_database_path=live_database_path,
    )
