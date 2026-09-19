from datetime import datetime, timezone

import pytest

import scripts.run_phase14_sqlite_cutover as entry
from src.core.clock import SystemClock
from src.data.assets import get_asset
from src.market.market_session import (
    MarketSessionService,
)
from src.persistence.sqlite_application_binding import (
    Phase14ApplicationBindingError,
    Phase14ApplicationBindingInputs,
    build_phase14_application_context,
)
from src.persistence.sqlite_bootstrap import (
    bootstrap_fresh_database,
)
from src.persistence.sqlite_cutover_dependencies import (
    Phase14PaperDependencyContext,
    build_phase14_sqlite_bundle_kwargs,
)
from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)


UTC = timezone.utc
NOW_TEXT = "2026-09-19T12:00:00Z"


class MarketDataStub:
    def run_cycle(
        self,
        asset_ids,
    ):
        raise AssertionError(
            "A.7 construction must not run market cycle"
        )


def decision_provider(
    **kwargs,
):
    raise AssertionError(
        "A.7 construction must not request a decision"
    )


def fx_conversion_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.7 construction must not request FX conversion"
    )


def estimated_exit_fee_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.7 construction must not estimate exit fee"
    )


def realized_quotes_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.7 construction must not request realized FX quotes"
    )


def execution_evidence_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.7 construction must not request execution evidence"
    )


def realized_evidence_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.7 construction must not request realized evidence"
    )


def inputs(
    **overrides,
):
    values = {
        "market_data_service": MarketDataStub(),
        "decision_provider": decision_provider,
        "fx_conversion_resolver": fx_conversion_resolver,
        "estimated_exit_fee_resolver": (
            estimated_exit_fee_resolver
        ),
        "realized_quotes_resolver": realized_quotes_resolver,
        "execution_evidence_resolver": (
            execution_evidence_resolver
        ),
        "realized_evidence_resolver": (
            realized_evidence_resolver
        ),
        "trading_fee_rate": 0.001,
        "slippage_bps": 0.0,
        "strategy_id": "PHASE14_A7",
    }
    values.update(
        overrides
    )
    return Phase14ApplicationBindingInputs(
        **values
    )


def test_unambiguous_application_defaults_are_bound():
    context = build_phase14_application_context(
        inputs()
    )

    assert isinstance(
        context,
        Phase14PaperDependencyContext,
    )
    assert isinstance(
        context.market_session_service,
        MarketSessionService,
    )
    assert isinstance(
        context.clock,
        SystemClock,
    )
    assert context.asset_resolver is get_asset


def test_explicit_safe_overrides_are_preserved():
    class Session:
        def get_session(
            self,
            asset_id,
            at,
        ):
            return None

    class Clock:
        def now(
            self,
        ):
            return datetime(
                2026,
                9,
                19,
                tzinfo=UTC,
            )

    def asset_resolver(
        asset_id,
    ):
        return object()

    session = Session()
    clock = Clock()

    context = build_phase14_application_context(
        inputs(
            market_session_service=session,
            clock=clock,
            asset_resolver=asset_resolver,
        )
    )

    assert context.market_session_service is session
    assert context.clock is clock
    assert context.asset_resolver is asset_resolver


@pytest.mark.parametrize(
    "field_name",
    [
        "decision_provider",
        "fx_conversion_resolver",
        "estimated_exit_fee_resolver",
        "realized_quotes_resolver",
        "execution_evidence_resolver",
        "realized_evidence_resolver",
    ],
)
def test_ambiguous_bindings_are_required_and_fail_closed(
    field_name,
):
    value = inputs()

    broken = Phase14ApplicationBindingInputs(
        **{
            **value.__dict__,
            field_name: None,
        }
    )

    with pytest.raises(
        Phase14ApplicationBindingError,
        match=field_name,
    ):
        build_phase14_application_context(
            broken
        )


def test_market_data_is_explicit_because_a6_found_multiple_candidates():
    value = inputs(
        market_data_service=None
    )

    with pytest.raises(
        Phase14ApplicationBindingError,
        match="market_data_service",
    ):
        build_phase14_application_context(
            value
        )


def test_market_data_must_expose_run_cycle():
    value = inputs(
        market_data_service=object()
    )

    with pytest.raises(
        Phase14ApplicationBindingError,
        match="run_cycle",
    ):
        build_phase14_application_context(
            value
        )


def test_bound_context_builds_real_a5_dependency_composition():
    context = build_phase14_application_context(
        inputs()
    )

    kwargs = build_phase14_sqlite_bundle_kwargs(
        context
    )

    assert kwargs["market_data_service"] is context.market_data_service
    assert kwargs["market_session_service"] is context.market_session_service
    assert kwargs["decision_provider"] is decision_provider
    assert kwargs["clock"] is context.clock
    assert kwargs["broker"].execution_journal is None


def test_bound_context_constructs_real_temp_sqlite_bundle_via_a4(
    tmp_path,
    capsys,
):
    db = tmp_path / "phase14-a7.db"

    bootstrap_fresh_database(
        db,
        initial_cash_pln="1000",
        bootstrap_id="phase14-a7",
        created_at_utc=NOW_TEXT,
    )

    live = (
        tmp_path
        / "data"
        / "live"
        / "trading.db"
    )

    context = build_phase14_application_context(
        inputs()
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
        paper_dependency_context=context,
    )

    output = capsys.readouterr().out

    assert code == 0
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
