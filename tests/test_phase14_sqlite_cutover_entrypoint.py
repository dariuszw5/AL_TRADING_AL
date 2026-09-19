from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.run_phase14_sqlite_cutover as entry
from src.persistence.sqlite_cutover_seam import (
    CutoverMode,
)


def test_parser_defaults_to_legacy_construction_only():
    args = entry._parser().parse_args([])

    assert args.mode == "legacy"
    assert args.sqlite_db is None
    assert (
        args.live_db
        == "data/live/trading.db"
    )
    assert (
        args.confirm_temp_sqlite_construction
        is False
    )


def test_default_legacy_path_is_noop_and_never_requests_dependencies(
    monkeypatch,
    capsys,
):
    calls = []

    monkeypatch.setattr(
        entry,
        "build_phase14_runtime",
        lambda **kwargs: (
            calls.append(kwargs)
            or SimpleNamespace(
                mode=CutoverMode.LEGACY,
                runtime=None,
                sqlite_database_path=None,
            )
        ),
    )

    code = entry.main(
        [],
        sqlite_bundle_kwargs_provider=(
            lambda **kwargs: pytest.fail(
                "provider must not run"
            )
        ),
    )

    output = capsys.readouterr().out

    assert code == 0
    assert len(calls) == 1
    assert calls[0]["mode"] == "legacy"
    assert (
        calls[0]["sqlite_bundle_kwargs"]
        is None
    )
    assert "CUTOVER MODE: LEGACY" in output
    assert "SQLITE CONSTRUCTED: NO" in output
    assert "PAPER CYCLE: NOT RUN" in output


def test_sqlite_mode_requires_explicit_confirmation_before_provider(
    tmp_path,
    capsys,
):
    candidate = tmp_path / "candidate.db"
    candidate.write_bytes(b"existing")

    calls = []

    code = entry.main(
        [
            "--mode",
            "sqlite",
            "--sqlite-db",
            str(candidate),
        ],
        sqlite_bundle_kwargs_provider=(
            lambda **kwargs: calls.append(
                kwargs
            )
        ),
    )

    output = capsys.readouterr().out

    assert code == entry.EXIT_CONFIRMATION_REQUIRED
    assert calls == []
    assert (
        "EXPLICIT TEMP SQLITE CONSTRUCTION "
        "CONFIRMATION REQUIRED"
        in output
    )
    assert "SQLITE CONSTRUCTED: NO" in output


def test_sqlite_live_path_is_rejected_before_dependency_provider(
    tmp_path,
    capsys,
):
    live = tmp_path / "data" / "live" / "trading.db"
    live.parent.mkdir(parents=True)
    live.write_bytes(b"live")

    calls = []

    code = entry.main(
        [
            "--mode",
            "sqlite",
            "--sqlite-db",
            str(live),
            "--live-db",
            str(live),
            "--confirm-temp-sqlite-construction",
        ],
        sqlite_bundle_kwargs_provider=(
            lambda **kwargs: calls.append(
                kwargs
            )
        ),
    )

    output = capsys.readouterr().out

    assert code == entry.EXIT_PREFLIGHT_FAILED
    assert calls == []
    assert "CUTOVER PREFLIGHT FAILED" in output
    assert "live database" in output
    assert "SQLITE CONSTRUCTED: NO" in output


def test_sqlite_live_directory_candidate_is_rejected_before_provider(
    tmp_path,
    capsys,
):
    live_dir = tmp_path / "data" / "live"
    live_dir.mkdir(parents=True)

    live = live_dir / "trading.db"
    live.write_bytes(b"live")

    candidate = live_dir / "candidate.db"
    candidate.write_bytes(b"candidate")

    calls = []

    code = entry.main(
        [
            "--mode",
            "sqlite",
            "--sqlite-db",
            str(candidate),
            "--live-db",
            str(live),
            "--confirm-temp-sqlite-construction",
        ],
        sqlite_bundle_kwargs_provider=(
            lambda **kwargs: calls.append(
                kwargs
            )
        ),
    )

    output = capsys.readouterr().out

    assert code == entry.EXIT_PREFLIGHT_FAILED
    assert calls == []
    assert "live directory" in output


def test_sqlite_mode_requires_dependency_provider_after_path_guard(
    tmp_path,
    capsys,
):
    candidate = tmp_path / "candidate.db"
    candidate.write_bytes(b"existing")

    code = entry.main(
        [
            "--mode",
            "sqlite",
            "--sqlite-db",
            str(candidate),
            "--live-db",
            str(
                tmp_path
                / "data"
                / "live"
                / "trading.db"
            ),
            "--confirm-temp-sqlite-construction",
        ],
        sqlite_bundle_kwargs_provider=None,
    )

    output = capsys.readouterr().out

    assert code == entry.EXIT_DEPENDENCIES_REQUIRED
    assert (
        "SQLITE BUNDLE DEPENDENCY PROVIDER REQUIRED"
        in output
    )
    assert "SQLITE CONSTRUCTED: NO" in output


def test_successful_temp_sqlite_construction_closes_bundle_without_cycle(
    tmp_path,
    monkeypatch,
    capsys,
):
    candidate = tmp_path / "candidate.db"
    candidate.write_bytes(b"existing")

    live = (
        tmp_path
        / "data"
        / "live"
        / "trading.db"
    )

    provider_calls = []
    factory_calls = []
    lifecycle = []

    class FakeBundle:
        def close(self):
            lifecycle.append("close")

        def run_cycle(self, asset_ids):
            lifecycle.append(
                ("cycle", tuple(asset_ids))
            )
            raise AssertionError(
                "A.4 must never run a cycle"
            )

    def provider(
        *,
        database_path,
        live_database_path,
    ):
        provider_calls.append(
            (
                Path(database_path),
                Path(live_database_path),
            )
        )

        return {
            "market_data_service": object(),
            "market_session_service": object(),
            "broker": object(),
            "decision_provider": object(),
            "clock": object(),
            "paper_mode": object(),
            "accounting_bridge": object(),
            "fx_conversion_resolver": object(),
            "estimated_exit_fee_resolver": object(),
            "realized_quotes_resolver": object(),
            "cycle_mapper_factory": object(),
        }

    def fake_factory(**kwargs):
        factory_calls.append(kwargs)

        return SimpleNamespace(
            mode=CutoverMode.SQLITE,
            runtime=FakeBundle(),
            sqlite_database_path=(
                Path(
                    kwargs[
                        "sqlite_database_path"
                    ]
                ).resolve()
            ),
        )

    monkeypatch.setattr(
        entry,
        "build_phase14_runtime",
        fake_factory,
    )

    code = entry.main(
        [
            "--mode",
            "sqlite",
            "--sqlite-db",
            str(candidate),
            "--live-db",
            str(live),
            "--confirm-temp-sqlite-construction",
        ],
        sqlite_bundle_kwargs_provider=provider,
    )

    output = capsys.readouterr().out

    assert code == 0

    assert provider_calls == [
        (
            candidate.resolve(),
            live.resolve(),
        )
    ]

    assert len(factory_calls) == 1
    assert (
        factory_calls[0]["mode"]
        == "sqlite"
    )

    assert lifecycle == ["close"]

    assert "CUTOVER MODE: SQLITE" in output
    assert "SQLITE CONSTRUCTED: YES" in output
    assert "SQLITE BUNDLE CLOSED: YES" in output
    assert "PAPER CYCLE: NOT RUN" in output
    assert "HALT CLEAR: NOT REQUESTED" in output


def test_factory_failure_is_fail_closed_and_does_not_report_construction(
    tmp_path,
    monkeypatch,
    capsys,
):
    candidate = tmp_path / "candidate.db"
    candidate.write_bytes(b"existing")

    monkeypatch.setattr(
        entry,
        "build_phase14_runtime",
        lambda **kwargs: (
            (_ for _ in ())
            .throw(
                RuntimeError(
                    "construction boom"
                )
            )
        ),
    )

    code = entry.main(
        [
            "--mode",
            "sqlite",
            "--sqlite-db",
            str(candidate),
            "--live-db",
            str(
                tmp_path
                / "data"
                / "live"
                / "trading.db"
            ),
            "--confirm-temp-sqlite-construction",
        ],
        sqlite_bundle_kwargs_provider=(
            lambda **kwargs: {
                "market_data_service": object(),
                "market_session_service": object(),
                "broker": object(),
                "decision_provider": object(),
                "clock": object(),
                "paper_mode": object(),
                "accounting_bridge": object(),
                "fx_conversion_resolver": object(),
                "estimated_exit_fee_resolver": object(),
                "realized_quotes_resolver": object(),
                "cycle_mapper_factory": object(),
            }
        ),
    )

    output = capsys.readouterr().out

    assert code == entry.EXIT_CONSTRUCTION_FAILED
    assert "SQLITE CONSTRUCTION FAILED" in output
    assert "SQLITE CONSTRUCTED: NO" in output
    assert "PAPER CYCLE: NOT RUN" in output
