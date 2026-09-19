from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SQLiteCutoverSeamError(
    ValueError
):
    pass


class CutoverMode(
    str,
    Enum,
):
    LEGACY = "legacy"
    SQLITE = "sqlite"


@dataclass(
    frozen=True
)
class RuntimeConstructionSelection:
    mode: CutoverMode
    runtime: object
    sqlite_database_path: Path | None


def _coerce_mode(
    value,
):
    if isinstance(
        value,
        CutoverMode,
    ):
        return value

    try:
        return CutoverMode(
            str(value)
        )
    except ValueError as exc:
        raise SQLiteCutoverSeamError(
            "mode must be legacy or sqlite"
        ) from exc


def _resolve(
    value,
):
    return Path(
        value
    ).resolve()


def _is_relative_to(
    path,
    parent,
):
    try:
        path.relative_to(
            parent
        )
    except ValueError:
        return False

    return True


def select_runtime_construction(
    *,
    legacy_builder,
    sqlite_builder,
    sqlite_database_path=None,
    live_database_path="data/live/trading.db",
    mode=CutoverMode.LEGACY,
):
    """
    Explicit construction seam for Phase 14.

    Default behavior is legacy. SQLite mode is opt-in and, in A.2,
    is intentionally restricted away from the real data/live tree.
    """

    if not callable(
        legacy_builder
    ):
        raise TypeError(
            "legacy_builder must be callable"
        )

    if not callable(
        sqlite_builder
    ):
        raise TypeError(
            "sqlite_builder must be callable"
        )

    selected = _coerce_mode(
        mode
    )

    if selected is CutoverMode.LEGACY:
        return RuntimeConstructionSelection(
            mode=selected,
            runtime=legacy_builder(),
            sqlite_database_path=None,
        )

    if sqlite_database_path is None:
        raise SQLiteCutoverSeamError(
            "sqlite_database_path is required in sqlite mode"
        )

    candidate = _resolve(
        sqlite_database_path
    )
    live = _resolve(
        live_database_path
    )
    live_dir = live.parent

    if candidate == live:
        raise SQLiteCutoverSeamError(
            "real live database is forbidden in Phase 14 A.2"
        )

    if _is_relative_to(
        candidate,
        live_dir,
    ):
        raise SQLiteCutoverSeamError(
            "SQLite candidate under live directory is forbidden "
            "in Phase 14 A.2"
        )

    if not candidate.exists():
        raise SQLiteCutoverSeamError(
            "sqlite_database_path must already exist"
        )

    if not candidate.is_file():
        raise SQLiteCutoverSeamError(
            "sqlite_database_path must be a file"
        )

    runtime = sqlite_builder(
        database_path=candidate,
        live_database_path=live,
    )

    return RuntimeConstructionSelection(
        mode=selected,
        runtime=runtime,
        sqlite_database_path=candidate,
    )
