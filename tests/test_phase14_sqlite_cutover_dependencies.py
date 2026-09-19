from datetime import datetime, timezone
from pathlib import Path

import pytest

import scripts.run_phase14_sqlite_cutover as entry
from src.accounting.runtime_bridge import (
    Phase09RuntimeAccountingBridge,
)
from src.core.clock import FixedClock
from src.execution.models import (
    PaperMode,
)
from src.execution.paper_broker import (
    PaperBroker,
)
from src.persistence.sqlite_bootstrap import (
    bootstrap_fresh_database,
)
from src.persistence.sqlite_cutover_dependencies import (
    Phase14PaperDependencyContext,
    Phase14PaperDependencyError,
    build_phase14_sqlite_bundle_kwargs,
    make_phase14_sqlite_bundle_kwargs_provider,
)
from src.persistence.sqlite_realistic_v2_mapper import (
    RealisticV2SQLiteMapper,
)
from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)


UTC = timezone.utc
NOW = datetime(
    2026,
    9,
    19,
    12,
    0,
    tzinfo=UTC,
)
NOW_TEXT = "2026-09-19T12:00:00Z"


class FakeAsset:
    def __init__(
        self,
        asset_id,
    ):
        self.asset_id = asset_id
        self.allow_long = True
        self.allow_short = False
        self.short_mechanism = "NONE"
        self.short_financing_model = None


def asset_resolver(
    asset_id,
):
    return FakeAsset(
        asset_id
    )


class MarketDataService:
    def run_cycle(
        self,
        asset_ids,
    ):
        raise AssertionError(
            "A.5 construction must not run market cycle"
        )


class MarketSessionService:
    def get_session(
        self,
        asset_id,
        at,
    ):
        raise AssertionError(
            "A.5 construction must not resolve session"
        )


def decision_provider(
    **kwargs,
):
    raise AssertionError(
        "A.5 construction must not request decision"
    )


def fx_conversion_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.5 construction must not request FX conversion"
    )


def estimated_exit_fee_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.5 construction must not estimate exit fee"
    )


def realized_quotes_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.5 construction must not request realized FX quotes"
    )


def execution_evidence_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.5 construction must not map execution evidence"
    )


def realized_evidence_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.5 construction must not map realized evidence"
    )


def context():
    return Phase14PaperDependencyContext(
        market_data_service=MarketDataService(),
        market_session_service=MarketSessionService(),
        decision_provider=decision_provider,
        clock=FixedClock(NOW),
        asset_resolver=asset_resolver,
        fx_conversion_resolver=fx_conversion_resolver,
        estimated_exit_fee_resolver=(
            estimated_exit_fee_resolver
        ),
        realized_quotes_resolver=(
            realized_quotes_resolver
        ),
        execution_evidence_resolver=(
            execution_evidence_resolver
        ),
        realized_evidence_resolver=(
            realized_evidence_resolver
        ),
        trading_fee_rate=0.001,
        slippage_bps=0.0,
        strategy_id="PHASE14_A5",
        realized_market_max_age_seconds=7200.0,
        realized_daily_reference_max_age_days=7,
    )


def seed_database(
    path,
):
    bootstrap_fresh_database(
        path,
        initial_cash_pln="1000",
        bootstrap_id="phase14-a5",
        created_at_utc=NOW_TEXT,
    )


def test_dependency_composition_uses_real_paper_components():
    kwargs = build_phase14_sqlite_bundle_kwargs(
        context()
    )

    assert isinstance(
        kwargs["broker"],
        PaperBroker,
    )

    assert (
        kwargs["broker"].execution_journal
        is None
    )

    assert isinstance(
        kwargs["accounting_bridge"],
        Phase09RuntimeAccountingBridge,
    )

    assert (
        kwargs["paper_mode"]
        is PaperMode.REALISTIC_PAPER
    )

    assert kwargs["market_data_service"].__class__ is MarketDataService
    assert kwargs["market_session_service"].__class__ is MarketSessionService
    assert kwargs["decision_provider"] is decision_provider


def test_mapper_factory_uses_real_mapper_and_broker_fingerprint(
    tmp_path,
):
    db = tmp_path / "mapper.db"
    seed_database(
        db
    )

    kwargs = build_phase14_sqlite_bundle_kwargs(
        context()
    )

    repo = SQLiteLedgerRepository.open_writer(
        db
    )

    try:
        mapper = kwargs[
            "cycle_mapper_factory"
        ](
            repo
        )

        assert isinstance(
            mapper,
            RealisticV2SQLiteMapper,
        )

        assert (
            mapper.order_fingerprint_resolver
            == kwargs["broker"].order_fingerprint
        )
    finally:
        repo.close()


def test_context_rejects_non_callable_execution_evidence():
    value = context()

    broken = Phase14PaperDependencyContext(
        **{
            **value.__dict__,
            "execution_evidence_resolver": None,
        }
    )

    with pytest.raises(
        Phase14PaperDependencyError,
        match="execution_evidence_resolver",
    ):
        build_phase14_sqlite_bundle_kwargs(
            broken
        )


def test_context_rejects_non_callable_realized_evidence():
    value = context()

    broken = Phase14PaperDependencyContext(
        **{
            **value.__dict__,
            "realized_evidence_resolver": None,
        }
    )

    with pytest.raises(
        Phase14PaperDependencyError,
        match="realized_evidence_resolver",
    ):
        build_phase14_sqlite_bundle_kwargs(
            broken
        )


def test_provider_returns_fresh_bundle_kwargs_without_opening_database(
    tmp_path,
):
    db = tmp_path / "candidate.db"
    db.write_bytes(b"not-a-database-yet")

    provider = (
        make_phase14_sqlite_bundle_kwargs_provider(
            context()
        )
    )

    first = provider(
        database_path=db,
        live_database_path=(
            tmp_path
            / "data"
            / "live"
            / "trading.db"
        ),
    )

    second = provider(
        database_path=db,
        live_database_path=(
            tmp_path
            / "data"
            / "live"
            / "trading.db"
        ),
    )

    assert first is not second
    assert first["broker"] is not second["broker"]
    assert db.read_bytes() == b"not-a-database-yet"


def test_dedicated_entrypoint_constructs_real_phase13_bundle_on_temp_sqlite(
    tmp_path,
    capsys,
):
    db = tmp_path / "phase14-a5.db"
    seed_database(
        db
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
        paper_dependency_context=context(),
    )

    output = capsys.readouterr().out

    assert code == 0

    assert "CUTOVER MODE: SQLITE" in output
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
        assert (
            state["halt_reason"]
            == "FRESH_BOOTSTRAP_REQUIRES_EXPLICIT_ACTIVATION"
        )

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


def test_entrypoint_context_is_not_used_in_default_legacy_mode(
    monkeypatch,
    capsys,
):
    class ExplodingContext:
        def __getattribute__(
            self,
            name,
        ):
            raise AssertionError(
                "legacy path must not touch dependency context"
            )

    code = entry.main(
        [],
        paper_dependency_context=ExplodingContext(),
    )

    output = capsys.readouterr().out

    assert code == 0
    assert "CUTOVER MODE: LEGACY" in output
    assert "SQLITE CONSTRUCTED: NO" in output


def test_explicit_provider_has_priority_over_context(
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
                calls.append("explicit-provider")
                or {}
            )
        ),
        paper_dependency_context=object(),
    )

    assert code == 0
    assert calls == [
        "explicit-provider",
        "close",
    ]
