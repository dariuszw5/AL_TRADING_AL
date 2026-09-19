from pathlib import Path

import pytest

from src.persistence.sqlite_cutover_seam import (
    CutoverMode,
    SQLiteCutoverSeamError,
    select_runtime_construction,
)


def test_default_mode_is_legacy_and_never_calls_sqlite_builder(
    tmp_path,
):
    calls = []

    def legacy_builder():
        calls.append("legacy")
        return "legacy-runtime"

    def sqlite_builder(**kwargs):
        raise AssertionError(
            "sqlite builder must not run by default"
        )

    result = select_runtime_construction(
        legacy_builder=legacy_builder,
        sqlite_builder=sqlite_builder,
        sqlite_database_path=None,
        live_database_path=(
            tmp_path / "live.db"
        ),
    )

    assert result.mode is CutoverMode.LEGACY
    assert result.runtime == "legacy-runtime"
    assert result.sqlite_database_path is None
    assert calls == ["legacy"]


def test_explicit_legacy_mode_ignores_sqlite_path(
    tmp_path,
):
    candidate = tmp_path / "candidate.db"
    candidate.write_bytes(b"not-opened")

    calls = []

    result = select_runtime_construction(
        mode="legacy",
        legacy_builder=lambda: calls.append(
            "legacy"
        ) or "legacy",
        sqlite_builder=lambda **kwargs: (
            calls.append("sqlite")
        ),
        sqlite_database_path=candidate,
        live_database_path=(
            tmp_path / "live.db"
        ),
    )

    assert result.mode is CutoverMode.LEGACY
    assert result.runtime == "legacy"
    assert result.sqlite_database_path is None
    assert calls == ["legacy"]


def test_sqlite_mode_requires_explicit_database_path(
    tmp_path,
):
    with pytest.raises(
        SQLiteCutoverSeamError,
        match="sqlite_database_path",
    ):
        select_runtime_construction(
            mode="sqlite",
            legacy_builder=lambda: object(),
            sqlite_builder=lambda **kwargs: object(),
            sqlite_database_path=None,
            live_database_path=(
                tmp_path / "live.db"
            ),
        )


def test_sqlite_mode_rejects_exact_live_database(
    tmp_path,
):
    live = tmp_path / "data" / "live" / "trading.db"
    live.parent.mkdir(parents=True)
    live.write_bytes(b"do-not-touch")

    before = live.read_bytes()

    with pytest.raises(
        SQLiteCutoverSeamError,
        match="live database",
    ):
        select_runtime_construction(
            mode="sqlite",
            legacy_builder=lambda: object(),
            sqlite_builder=lambda **kwargs: object(),
            sqlite_database_path=live,
            live_database_path=live,
        )

    assert live.read_bytes() == before


def test_sqlite_mode_rejects_any_path_under_live_directory(
    tmp_path,
):
    live_dir = tmp_path / "data" / "live"
    live_dir.mkdir(parents=True)

    live = live_dir / "trading.db"
    live.write_bytes(b"live")

    candidate = live_dir / "phase14-test.db"
    candidate.write_bytes(b"candidate")

    with pytest.raises(
        SQLiteCutoverSeamError,
        match="live directory",
    ):
        select_runtime_construction(
            mode=CutoverMode.SQLITE,
            legacy_builder=lambda: object(),
            sqlite_builder=lambda **kwargs: object(),
            sqlite_database_path=candidate,
            live_database_path=live,
        )


def test_sqlite_mode_requires_existing_temp_test_database(
    tmp_path,
):
    candidate = tmp_path / "missing.db"
    live = tmp_path / "data" / "live" / "trading.db"

    with pytest.raises(
        SQLiteCutoverSeamError,
        match="must already exist",
    ):
        select_runtime_construction(
            mode="sqlite",
            legacy_builder=lambda: object(),
            sqlite_builder=lambda **kwargs: object(),
            sqlite_database_path=candidate,
            live_database_path=live,
        )


def test_sqlite_mode_calls_only_sqlite_builder_with_resolved_path(
    tmp_path,
):
    candidate = tmp_path / "phase14-a2.db"
    candidate.write_bytes(b"existing")

    live = tmp_path / "data" / "live" / "trading.db"

    calls = []

    def legacy_builder():
        raise AssertionError(
            "legacy builder must not run in sqlite mode"
        )

    def sqlite_builder(
        *,
        database_path,
        live_database_path,
    ):
        calls.append(
            (
                Path(database_path),
                Path(live_database_path),
            )
        )
        return "sqlite-runtime"

    result = select_runtime_construction(
        mode="sqlite",
        legacy_builder=legacy_builder,
        sqlite_builder=sqlite_builder,
        sqlite_database_path=candidate,
        live_database_path=live,
    )

    assert result.mode is CutoverMode.SQLITE
    assert result.runtime == "sqlite-runtime"
    assert result.sqlite_database_path == candidate.resolve()

    assert calls == [
        (
            candidate.resolve(),
            live.resolve(),
        )
    ]


def test_invalid_mode_fails_before_any_builder_is_called(
    tmp_path,
):
    calls = []

    with pytest.raises(
        SQLiteCutoverSeamError,
        match="mode",
    ):
        select_runtime_construction(
            mode="surprise",
            legacy_builder=lambda: calls.append(
                "legacy"
            ),
            sqlite_builder=lambda **kwargs: calls.append(
                "sqlite"
            ),
            sqlite_database_path=tmp_path / "candidate.db",
            live_database_path=tmp_path / "live.db",
        )

    assert calls == []


def test_builders_must_be_callable(
    tmp_path,
):
    with pytest.raises(
        TypeError,
        match="legacy_builder",
    ):
        select_runtime_construction(
            legacy_builder=None,
            sqlite_builder=lambda **kwargs: object(),
            sqlite_database_path=None,
            live_database_path=tmp_path / "live.db",
        )

    with pytest.raises(
        TypeError,
        match="sqlite_builder",
    ):
        select_runtime_construction(
            legacy_builder=lambda: object(),
            sqlite_builder=None,
            sqlite_database_path=None,
            live_database_path=tmp_path / "live.db",
        )
