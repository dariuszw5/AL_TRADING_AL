from pathlib import Path

import pytest

import scripts.run_phase14_sqlite_cutover as entry
from src.persistence.sqlite_application_binding import (
    Phase14ApplicationBindingInputs,
)
from src.persistence.sqlite_bootstrap import (
    bootstrap_fresh_database,
)
from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)


NOW_TEXT = "2026-09-19T12:00:00Z"


class MarketDataStub:
    def run_cycle(
        self,
        asset_ids,
    ):
        raise AssertionError(
            "A.8 construction must not run market cycle"
        )


def decision_provider(
    **kwargs,
):
    raise AssertionError(
        "A.8 construction must not request decision"
    )


def fx_conversion_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.8 construction must not request FX conversion"
    )


def estimated_exit_fee_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.8 construction must not estimate exit fee"
    )


def realized_quotes_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.8 construction must not request realized quotes"
    )


def execution_evidence_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.8 construction must not request execution evidence"
    )


def realized_evidence_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.8 construction must not request realized evidence"
    )


def binding_inputs(
    **overrides,
):
    values = {
        "market_data_service": MarketDataStub(),
        "decision_provider": decision_provider,
        "fx_conversion_resolver": fx_conversion_resolver,
        "estimated_exit_fee_resolver": (
            estimated_exit_fee_resolver
        ),
        "realized_quotes_resolver": (
            realized_quotes_resolver
        ),
        "execution_evidence_resolver": (
            execution_evidence_resolver
        ),
        "realized_evidence_resolver": (
            realized_evidence_resolver
        ),
        "trading_fee_rate": 0.001,
        "slippage_bps": 0.0,
        "strategy_id": "PHASE14_A8",
    }
    values.update(
        overrides
    )

    return Phase14ApplicationBindingInputs(
        **values
    )


def test_default_legacy_path_does_not_touch_application_binding(
    capsys,
):
    class ExplodingInputs:
        def __getattribute__(
            self,
            name,
        ):
            raise AssertionError(
                "legacy path must not inspect application binding inputs"
            )

    code = entry.main(
        [],
        application_binding_inputs=ExplodingInputs(),
    )

    output = capsys.readouterr().out

    assert code == 0
    assert "CUTOVER MODE: LEGACY" in output
    assert "SQLITE CONSTRUCTED: NO" in output


def test_explicit_provider_has_priority_over_application_binding(
    tmp_path,
    monkeypatch,
):
    db = tmp_path / "candidate.db"
    db.write_bytes(b"existing")

    live = (
        tmp_path
        / "data"
        / "live"
        / "trading.db"
    )

    calls = []

    class FakeBundle:
        def close(self):
            calls.append("close")

    class ExplodingInputs:
        def __getattribute__(
            self,
            name,
        ):
            raise AssertionError(
                "explicit provider must win"
            )

    monkeypatch.setattr(
        entry,
        "build_phase14_runtime",
        lambda **kwargs: type(
            "Selection",
            (),
            {
                "runtime": FakeBundle(),
            },
        )(),
    )

    code = entry.main(
        [
            "--mode",
            "sqlite",
            "--sqlite-db",
            str(db),
            "--live-db",
            str(live),
            "--confirm-temp-sqlite-construction",
        ],
        sqlite_bundle_kwargs_provider=(
            lambda **kwargs: (
                calls.append("provider")
                or {}
            )
        ),
        application_binding_inputs=ExplodingInputs(),
    )

    assert code == 0
    assert calls == [
        "provider",
        "close",
    ]


def test_paper_dependency_context_has_priority_over_application_binding(
    tmp_path,
    monkeypatch,
):
    db = tmp_path / "candidate.db"
    db.write_bytes(b"existing")

    live = (
        tmp_path
        / "data"
        / "live"
        / "trading.db"
    )

    calls = []

    paper_context = object()

    class FakeBundle:
        def close(self):
            calls.append("close")

    monkeypatch.setattr(
        entry,
        "make_phase14_sqlite_bundle_kwargs_provider",
        lambda context: (
            calls.append(("context", context))
            or (
                lambda **kwargs: (
                    calls.append("provider")
                    or {}
                )
            )
        ),
    )

    monkeypatch.setattr(
        entry,
        "build_phase14_runtime",
        lambda **kwargs: type(
            "Selection",
            (),
            {
                "runtime": FakeBundle(),
            },
        )(),
    )

    class ExplodingInputs:
        def __getattribute__(
            self,
            name,
        ):
            raise AssertionError(
                "paper dependency context must win"
            )

    code = entry.main(
        [
            "--mode",
            "sqlite",
            "--sqlite-db",
            str(db),
            "--live-db",
            str(live),
            "--confirm-temp-sqlite-construction",
        ],
        paper_dependency_context=paper_context,
        application_binding_inputs=ExplodingInputs(),
    )

    assert code == 0
    assert calls == [
        ("context", paper_context),
        "provider",
        "close",
    ]


def test_live_path_rejection_happens_before_application_binding(
    tmp_path,
    capsys,
):
    live = (
        tmp_path
        / "data"
        / "live"
        / "trading.db"
    )
    live.parent.mkdir(parents=True)
    live.write_bytes(b"live")

    class ExplodingInputs:
        def __getattribute__(
            self,
            name,
        ):
            raise AssertionError(
                "path guard must run first"
            )

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
        application_binding_inputs=ExplodingInputs(),
    )

    output = capsys.readouterr().out

    assert code == entry.EXIT_PREFLIGHT_FAILED
    assert "live database" in output
    assert "SQLITE CONSTRUCTED: NO" in output


def test_invalid_application_binding_fails_closed_before_construction(
    tmp_path,
    monkeypatch,
    capsys,
):
    db = tmp_path / "candidate.db"
    db.write_bytes(b"existing")

    live = (
        tmp_path
        / "data"
        / "live"
        / "trading.db"
    )

    factory_calls = []

    monkeypatch.setattr(
        entry,
        "build_phase14_runtime",
        lambda **kwargs: factory_calls.append(
            kwargs
        ),
    )

    broken = binding_inputs(
        decision_provider=None
    )

    code = entry.main(
        [
            "--mode",
            "sqlite",
            "--sqlite-db",
            str(db),
            "--live-db",
            str(live),
            "--confirm-temp-sqlite-construction",
        ],
        application_binding_inputs=broken,
    )

    output = capsys.readouterr().out

    assert code == entry.EXIT_APPLICATION_BINDING_FAILED
    assert factory_calls == []
    assert "APPLICATION BINDING FAILED" in output
    assert "decision_provider" in output
    assert "SQLITE CONSTRUCTED: NO" in output


def test_missing_all_dependency_sources_preserves_existing_fail_closed_behavior(
    tmp_path,
    capsys,
):
    db = tmp_path / "candidate.db"
    db.write_bytes(b"existing")

    code = entry.main(
        [
            "--mode",
            "sqlite",
            "--sqlite-db",
            str(db),
            "--live-db",
            str(
                tmp_path
                / "data"
                / "live"
                / "trading.db"
            ),
            "--confirm-temp-sqlite-construction",
        ],
    )

    output = capsys.readouterr().out

    assert code == entry.EXIT_DEPENDENCIES_REQUIRED
    assert (
        "SQLITE BUNDLE DEPENDENCY PROVIDER REQUIRED"
        in output
    )


def test_application_binding_inputs_construct_real_temp_sqlite_bundle(
    tmp_path,
    capsys,
):
    db = tmp_path / "phase14-a8.db"

    bootstrap_fresh_database(
        db,
        initial_cash_pln="1000",
        bootstrap_id="phase14-a8",
        created_at_utc=NOW_TEXT,
    )

    live = (
        tmp_path
        / "data"
        / "live"
        / "trading.db"
    )

    code = entry.main(
        [
            "--mode",
            "sqlite",
            "--sqlite-db",
            str(db),
            "--live-db",
            str(live),
            "--confirm-temp-sqlite-construction",
        ],
        application_binding_inputs=binding_inputs(),
    )

    output = capsys.readouterr().out

    assert code == 0
    assert "CUTOVER MODE: SQLITE" in output
    assert "APPLICATION BINDING: PASS" in output
    assert "SQLITE CONSTRUCTED: YES" in output
    assert "SQLITE BUNDLE CLOSED: YES" in output
    assert "PAPER CYCLE: NOT RUN" in output
    assert "HALT CLEAR: NOT REQUESTED" in output

    repo = SQLiteLedgerRepository.open_reader(
        db
    )

    try:
        state = repo.read_system_state()

        assert state["halted"] == 1
        assert repo.count_rows("orders") == 0
        assert repo.count_rows("executions") == 0
        assert repo.count_rows("positions") == 0
        assert repo.count_rows("trades") == 0
        assert repo.count_rows("portfolio_transactions") == 1
        assert repo.reconcile_cash().matches is True
        assert repo.reconcile_realized_pnl()["matches"] is True
    finally:
        repo.close()

    assert not list(
        tmp_path.rglob("*.json")
    )
    assert not list(
        tmp_path.rglob("*.jsonl")
    )


def test_application_binding_path_never_invokes_run_cycle(
    tmp_path,
    monkeypatch,
):
    db = tmp_path / "candidate.db"
    db.write_bytes(b"existing")

    live = (
        tmp_path
        / "data"
        / "live"
        / "trading.db"
    )

    lifecycle = []

    class FakeBundle:
        def close(self):
            lifecycle.append("close")

        def run_cycle(self, asset_ids):
            lifecycle.append(
                ("cycle", tuple(asset_ids))
            )
            raise AssertionError(
                "A.8 must not run cycle"
            )

    monkeypatch.setattr(
        entry,
        "build_phase14_runtime",
        lambda **kwargs: type(
            "Selection",
            (),
            {
                "runtime": FakeBundle(),
            },
        )(),
    )

    code = entry.main(
        [
            "--mode",
            "sqlite",
            "--sqlite-db",
            str(db),
            "--live-db",
            str(live),
            "--confirm-temp-sqlite-construction",
        ],
        application_binding_inputs=binding_inputs(),
    )

    assert code == 0
    assert lifecycle == ["close"]
