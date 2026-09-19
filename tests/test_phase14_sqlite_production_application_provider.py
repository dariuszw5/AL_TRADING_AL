from pathlib import Path

import pytest

import scripts.run_phase14_sqlite_cutover as entry
from src.accounting.production_resolvers import (
    BrokerExitFeeEstimator,
    ProductionFxResolver,
)
from src.persistence.sqlite_application_binding import (
    Phase14ApplicationBindingInputs,
)
from src.persistence.sqlite_bootstrap import (
    bootstrap_fresh_database,
)
from src.persistence.sqlite_production_application_provider import (
    Phase14ProductionApplicationProviderError,
    Phase14ProductionBindingInputs,
    build_phase14_production_application_context,
    build_phase14_production_application_inputs,
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
            "A.9 construction must not run market cycle"
        )


def decision_provider(
    **kwargs,
):
    raise AssertionError(
        "A.9 construction must not request decision"
    )


def execution_evidence_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.9 construction must not request execution evidence"
    )


def realized_evidence_resolver(
    **kwargs,
):
    raise AssertionError(
        "A.9 construction must not request realized evidence"
    )


def uninitialized_production_fx_resolver():
    return object.__new__(
        ProductionFxResolver
    )


def uninitialized_exit_fee_estimator():
    return object.__new__(
        BrokerExitFeeEstimator
    )


def provider_inputs(
    **overrides,
):
    values = {
        "market_data_service": MarketDataStub(),
        "decision_provider": decision_provider,
        "production_fx_resolver": (
            uninitialized_production_fx_resolver()
        ),
        "exit_fee_estimator": (
            uninitialized_exit_fee_estimator()
        ),
        "execution_evidence_resolver": (
            execution_evidence_resolver
        ),
        "realized_evidence_resolver": (
            realized_evidence_resolver
        ),
        "trading_fee_rate": 0.001,
        "slippage_bps": 0.0,
        "strategy_id": "PHASE14_A9",
    }
    values.update(
        overrides
    )

    return Phase14ProductionBindingInputs(
        **values
    )


def test_provider_uses_real_production_resolver_types():
    inputs = build_phase14_production_application_inputs(
        provider_inputs()
    )

    assert isinstance(
        inputs,
        Phase14ApplicationBindingInputs,
    )

    source = provider_inputs()

    assert (
        type(source.production_fx_resolver)
        is ProductionFxResolver
    )
    assert (
        type(source.exit_fee_estimator)
        is BrokerExitFeeEstimator
    )


def test_provider_maps_existing_production_fx_methods_without_calling_them():
    source = provider_inputs()

    inputs = build_phase14_production_application_inputs(
        source
    )

    assert (
        inputs.fx_conversion_resolver.__self__
        is source.production_fx_resolver
    )
    assert (
        inputs.fx_conversion_resolver.__func__
        is ProductionFxResolver.conversion_for
    )

    assert (
        inputs.realized_quotes_resolver.__self__
        is source.production_fx_resolver
    )
    assert (
        inputs.realized_quotes_resolver.__func__
        is ProductionFxResolver.resolve_realized_quotes
    )


def test_provider_maps_existing_exit_fee_estimator_without_calling_it():
    source = provider_inputs()

    inputs = build_phase14_production_application_inputs(
        source
    )

    assert (
        inputs.estimated_exit_fee_resolver
        is source.exit_fee_estimator
    )

    assert callable(
        inputs.estimated_exit_fee_resolver
    )


def test_provider_keeps_market_decision_and_evidence_explicit():
    source = provider_inputs()

    inputs = build_phase14_production_application_inputs(
        source
    )

    assert (
        inputs.market_data_service
        is source.market_data_service
    )
    assert (
        inputs.decision_provider
        is source.decision_provider
    )
    assert (
        inputs.execution_evidence_resolver
        is source.execution_evidence_resolver
    )
    assert (
        inputs.realized_evidence_resolver
        is source.realized_evidence_resolver
    )


def test_wrong_fx_resolver_type_fails_closed():
    with pytest.raises(
        Phase14ProductionApplicationProviderError,
        match="ProductionFxResolver",
    ):
        build_phase14_production_application_inputs(
            provider_inputs(
                production_fx_resolver=object()
            )
        )


def test_wrong_exit_fee_estimator_type_fails_closed():
    with pytest.raises(
        Phase14ProductionApplicationProviderError,
        match="BrokerExitFeeEstimator",
    ):
        build_phase14_production_application_inputs(
            provider_inputs(
                exit_fee_estimator=object()
            )
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "market_data_service",
        "decision_provider",
        "execution_evidence_resolver",
        "realized_evidence_resolver",
    ],
)
def test_remaining_ambiguous_dependencies_stay_required(
    field_name,
):
    value = provider_inputs()

    broken = Phase14ProductionBindingInputs(
        **{
            **value.__dict__,
            field_name: None,
        }
    )

    with pytest.raises(
        Phase14ProductionApplicationProviderError,
        match=field_name,
    ):
        build_phase14_production_application_inputs(
            broken
        )


def test_provider_builds_a7_application_context():
    context = build_phase14_production_application_context(
        provider_inputs()
    )

    assert (
        context.market_data_service.__class__
        is MarketDataStub
    )
    assert (
        context.decision_provider
        is decision_provider
    )
    assert (
        context.fx_conversion_resolver.__func__
        is ProductionFxResolver.conversion_for
    )
    assert (
        context.realized_quotes_resolver.__func__
        is ProductionFxResolver.resolve_realized_quotes
    )


def test_production_provider_result_constructs_real_temp_sqlite_bundle(
    tmp_path,
    capsys,
):
    db = tmp_path / "phase14-a9.db"

    bootstrap_fresh_database(
        db,
        initial_cash_pln="1000",
        bootstrap_id="phase14-a9",
        created_at_utc=NOW_TEXT,
    )

    live = (
        tmp_path
        / "data"
        / "live"
        / "trading.db"
    )

    application_inputs = (
        build_phase14_production_application_inputs(
            provider_inputs()
        )
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
        application_binding_inputs=application_inputs,
    )

    output = capsys.readouterr().out

    assert code == 0
    assert "APPLICATION BINDING: PASS" in output
    assert "SQLITE CONSTRUCTED: YES" in output
    assert "SQLITE BUNDLE CLOSED: YES" in output
    assert "PAPER CYCLE: NOT RUN" in output

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
