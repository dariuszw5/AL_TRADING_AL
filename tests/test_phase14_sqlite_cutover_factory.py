from pathlib import Path

import pytest

import src.persistence.sqlite_cutover_factory as factory
from src.persistence.sqlite_cutover_factory import (
    Phase14CutoverFactoryError,
    build_phase14_runtime,
)
from src.persistence.sqlite_cutover_seam import (
    CutoverMode,
    SQLiteCutoverSeamError,
)


def test_default_path_calls_only_legacy_builder(
    tmp_path,
):
    calls = []

    result = build_phase14_runtime(
        legacy_builder=lambda: (
            calls.append("legacy")
            or "legacy-runtime"
        ),
        sqlite_database_path=None,
        live_database_path=(
            tmp_path / "live.db"
        ),
    )

    assert result.mode is CutoverMode.LEGACY
    assert result.runtime == "legacy-runtime"
    assert calls == ["legacy"]


def test_default_path_does_not_require_sqlite_bundle_kwargs(
    tmp_path,
):
    result = build_phase14_runtime(
        legacy_builder=lambda: "legacy",
        sqlite_database_path=None,
        live_database_path=tmp_path / "live.db",
        sqlite_bundle_kwargs=None,
    )

    assert result.mode is CutoverMode.LEGACY
    assert result.runtime == "legacy"


def test_sqlite_mode_calls_phase13_bundle_builder(
    tmp_path,
    monkeypatch,
):
    candidate = tmp_path / "candidate.db"
    candidate.write_bytes(b"existing")

    live = (
        tmp_path
        / "data"
        / "live"
        / "trading.db"
    )

    calls = []

    def fake_bundle_builder(**kwargs):
        calls.append(kwargs)
        return "sqlite-bundle"

    monkeypatch.setattr(
        factory,
        "build_sqlite_only_runtime_bundle",
        fake_bundle_builder,
    )

    result = build_phase14_runtime(
        mode="sqlite",
        legacy_builder=lambda: (
            pytest.fail(
                "legacy builder must not run"
            )
        ),
        sqlite_database_path=candidate,
        live_database_path=live,
        sqlite_bundle_kwargs={
            "market_data_service": "market",
            "market_session_service": "session",
            "broker": "broker",
            "decision_provider": "decision",
            "clock": "clock",
            "paper_mode": "paper-mode",
            "accounting_bridge": "accounting",
            "fx_conversion_resolver": "fx",
            "estimated_exit_fee_resolver": "fee",
            "realized_quotes_resolver": "quotes",
            "cycle_mapper_factory": "mapper",
        },
    )

    assert result.mode is CutoverMode.SQLITE
    assert result.runtime == "sqlite-bundle"
    assert result.sqlite_database_path == candidate.resolve()

    assert len(calls) == 1

    payload = calls[0]

    assert payload["database_path"] == candidate.resolve()
    assert payload["live_database_path"] == live.resolve()
    assert payload["market_data_service"] == "market"
    assert payload["cycle_mapper_factory"] == "mapper"


def test_sqlite_mode_requires_bundle_kwargs(
    tmp_path,
):
    candidate = tmp_path / "candidate.db"
    candidate.write_bytes(b"existing")

    with pytest.raises(
        Phase14CutoverFactoryError,
        match="sqlite_bundle_kwargs",
    ):
        build_phase14_runtime(
            mode="sqlite",
            legacy_builder=lambda: object(),
            sqlite_database_path=candidate,
            live_database_path=(
                tmp_path
                / "data"
                / "live"
                / "trading.db"
            ),
            sqlite_bundle_kwargs=None,
        )


def test_sqlite_mode_rejects_unknown_bundle_keys_before_builder(
    tmp_path,
    monkeypatch,
):
    candidate = tmp_path / "candidate.db"
    candidate.write_bytes(b"existing")

    calls = []

    monkeypatch.setattr(
        factory,
        "build_sqlite_only_runtime_bundle",
        lambda **kwargs: (
            calls.append(kwargs)
        ),
    )

    with pytest.raises(
        Phase14CutoverFactoryError,
        match="unexpected sqlite bundle keys",
    ):
        build_phase14_runtime(
            mode="sqlite",
            legacy_builder=lambda: object(),
            sqlite_database_path=candidate,
            live_database_path=(
                tmp_path
                / "data"
                / "live"
                / "trading.db"
            ),
            sqlite_bundle_kwargs={
                "surprise": object(),
            },
        )

    assert calls == []


def test_sqlite_mode_requires_all_phase13_bundle_dependencies(
    tmp_path,
):
    candidate = tmp_path / "candidate.db"
    candidate.write_bytes(b"existing")

    with pytest.raises(
        Phase14CutoverFactoryError,
        match="missing sqlite bundle keys",
    ):
        build_phase14_runtime(
            mode="sqlite",
            legacy_builder=lambda: object(),
            sqlite_database_path=candidate,
            live_database_path=(
                tmp_path
                / "data"
                / "live"
                / "trading.db"
            ),
            sqlite_bundle_kwargs={
                "market_data_service": object(),
            },
        )


def test_live_database_rejection_happens_before_bundle_builder(
    tmp_path,
    monkeypatch,
):
    live = (
        tmp_path
        / "data"
        / "live"
        / "trading.db"
    )
    live.parent.mkdir(parents=True)
    live.write_bytes(b"live")

    calls = []

    monkeypatch.setattr(
        factory,
        "build_sqlite_only_runtime_bundle",
        lambda **kwargs: calls.append(kwargs),
    )

    with pytest.raises(
        SQLiteCutoverSeamError,
        match="live database",
    ):
        build_phase14_runtime(
            mode="sqlite",
            legacy_builder=lambda: object(),
            sqlite_database_path=live,
            live_database_path=live,
            sqlite_bundle_kwargs=factory.required_bundle_placeholders(),
        )

    assert calls == []


def test_live_directory_rejection_happens_before_bundle_builder(
    tmp_path,
    monkeypatch,
):
    live_dir = tmp_path / "data" / "live"
    live_dir.mkdir(parents=True)

    live = live_dir / "trading.db"
    live.write_bytes(b"live")

    candidate = live_dir / "candidate.db"
    candidate.write_bytes(b"candidate")

    calls = []

    monkeypatch.setattr(
        factory,
        "build_sqlite_only_runtime_bundle",
        lambda **kwargs: calls.append(kwargs),
    )

    with pytest.raises(
        SQLiteCutoverSeamError,
        match="live directory",
    ):
        build_phase14_runtime(
            mode=CutoverMode.SQLITE,
            legacy_builder=lambda: object(),
            sqlite_database_path=candidate,
            live_database_path=live,
            sqlite_bundle_kwargs=factory.required_bundle_placeholders(),
        )

    assert calls == []


def test_invalid_mode_fails_before_bundle_validation(
    tmp_path,
):
    with pytest.raises(
        SQLiteCutoverSeamError,
        match="mode",
    ):
        build_phase14_runtime(
            mode="invalid",
            legacy_builder=lambda: object(),
            sqlite_database_path=(
                tmp_path / "missing.db"
            ),
            live_database_path=(
                tmp_path / "live.db"
            ),
            sqlite_bundle_kwargs=None,
        )


def test_required_bundle_placeholders_match_phase13_contract():
    values = factory.required_bundle_placeholders()

    assert set(values) == {
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
