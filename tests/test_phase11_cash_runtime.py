from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType, SimpleNamespace

import pytest

import src.accounting.cash_runtime as cash_runtime_module
from src.accounting.cash_ledger import (
    Phase11CashLedger,
)
from src.accounting.cash_runtime import (
    Phase11CashAccountingRuntime,
    Phase11CashRuntimeError,
    reconcile_cash_ledger,
    wire_phase11_cash_runtime,
)
from src.accounting.realized_persistence import (
    PersistingAccountingRuntime,
    RealizedAccountingJournal,
)
from src.accounting.runtime_integration import (
    RuntimeAccountingAssetResult,
    RuntimeAccountingCycleResult,
)


UTC = timezone.utc
NOW = datetime(
    2026,
    9,
    18,
    15,
    0,
    tzinfo=UTC,
)


class FixedClock:
    def now(self):
        return NOW


def startup_metadata():
    return SimpleNamespace(
        global_config_hash="b" * 64,
    )


def realized_result(
    *,
    pln=Decimal("12.50"),
):
    accounting = SimpleNamespace(
        native_currency="USDT",
        net_realized_pnl_native=(
            Decimal("3")
        ),
        fx_rate=Decimal("4"),
        fx_path="USDT\u2192USD\u2192PLN",
        net_realized_pnl_pln=pln,
    )

    fx_booking = SimpleNamespace(
        fx_provider="NBP_TABLE_A",
        fx_table="x",
        fx_effective_date="2026-09-18",
        fx_path="USDT\u2192USD\u2192PLN",
    )

    return SimpleNamespace(
        accounting_record=accounting,
        fx_booking=fx_booking,
        limitations=(),
    )


def closed_position():
    return SimpleNamespace(
        asset_id="BTCUSDT",
        position_id="pos-1",
        entry_execution_id="exec-entry",
        exit_execution_id="exec-exit",
        closed_at=NOW,
    )


def exit_execution():
    return SimpleNamespace(
        asset_id="BTCUSDT",
        execution_id="exec-exit",
        config_hash="a" * 64,
    )


def append_realized(
    journal,
    *,
    pln=Decimal("12.50"),
):
    return journal.append_booking(
        asset_id="BTCUSDT",
        position=closed_position(),
        exit_execution=exit_execution(),
        realized_result=(
            realized_result(
                pln=pln
            )
        ),
        startup_metadata=(
            startup_metadata()
        ),
    )


def test_reconcile_cash_ledger_settles_crash_gap_once(
    tmp_path,
):
    realized = RealizedAccountingJournal(
        tmp_path
        / "phase10_realized_accounting.jsonl",
        clock=FixedClock(),
    )

    append_realized(
        realized,
        pln=Decimal("12.50"),
    )

    cash = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl",
        clock=FixedClock(),
    )

    cash.initialize(
        "1000"
    )

    first = reconcile_cash_ledger(
        cash_ledger=cash,
        realized_journal=realized,
    )

    second = reconcile_cash_ledger(
        cash_ledger=cash,
        realized_journal=realized,
    )

    assert len(first) == 1
    assert first[0].appended is True
    assert len(second) == 1
    assert second[0].appended is False

    assert (
        cash.current_cash_pln()
        == Decimal("1012.50")
    )

    assert len(
        cash.read_records()
    ) == 2


def test_reconcile_empty_realized_journal_only_verifies_cash(
    tmp_path,
):
    realized = RealizedAccountingJournal(
        tmp_path
        / "phase10_realized_accounting.jsonl",
        clock=FixedClock(),
    )

    cash = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl",
        clock=FixedClock(),
    )

    cash.initialize(
        "1000"
    )

    result = reconcile_cash_ledger(
        cash_ledger=cash,
        realized_journal=realized,
    )

    assert result == ()
    assert (
        cash.current_cash_pln()
        == Decimal("1000")
    )


class FakePhase10Runtime:
    def __init__(
        self,
        *,
        result,
        positions,
    ):
        self.result = result
        self.positions = positions
        self.calls = []

    def run_cycle(
        self,
        asset_ids,
    ):
        self.calls.append(
            tuple(
                asset_ids
            )
        )

        return self.result


def close_cycle_result():
    broker_result = SimpleNamespace(
        position=closed_position(),
        execution=exit_execution(),
    )

    execution_cycle = SimpleNamespace(
        results={
            "BTCUSDT": (
                SimpleNamespace(
                    broker_result=(
                        broker_result
                    )
                )
            ),
        }
    )

    accounting_results = (
        MappingProxyType(
            {
                "BTCUSDT": (
                    RuntimeAccountingAssetResult(
                        asset_id="BTCUSDT",
                        realized_result=(
                            realized_result()
                        ),
                    )
                ),
            }
        )
    )

    return RuntimeAccountingCycleResult(
        execution_cycle=(
            execution_cycle
        ),
        accounting_results=(
            accounting_results
        ),
        portfolio_snapshot=(
            SimpleNamespace(
                cash_pln=Decimal(
                    "1000"
                )
            )
        ),
        limitations=(),
    )


def test_close_cycle_persists_realized_then_cash_and_rebuilds_portfolio(
    tmp_path,
):
    realized = RealizedAccountingJournal(
        tmp_path
        / "phase10_realized_accounting.jsonl",
        clock=FixedClock(),
    )

    cash = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl",
        clock=FixedClock(),
    )

    cash.initialize(
        "1000"
    )

    base = FakePhase10Runtime(
        result=close_cycle_result(),
        positions={},
    )

    persisting = (
        PersistingAccountingRuntime(
            runtime=base,
            journal=realized,
            startup_metadata=(
                startup_metadata()
            ),
        )
    )

    calls = []

    def build_portfolio(
        *,
        cash_pln,
        mtm_records,
    ):
        calls.append(
            (
                cash_pln,
                tuple(
                    mtm_records
                ),
            )
        )

        return SimpleNamespace(
            cash_pln=cash_pln,
            equity_pln=cash_pln,
            position_count=(
                len(
                    tuple(
                        mtm_records
                    )
                )
            ),
        )

    runtime = (
        Phase11CashAccountingRuntime(
            persisting_runtime=(
                persisting
            ),
            cash_ledger=cash,
            realized_journal=realized,
            portfolio_snapshot_builder=(
                build_portfolio
            ),
        )
    )

    result = runtime.run_cycle(
        [
            "BTCUSDT",
        ]
    )

    assert (
        cash.current_cash_pln()
        == Decimal("1012.50")
    )

    assert len(
        realized.read_records()
    ) == 1

    assert len(
        cash.read_records()
    ) == 2

    assert (
        runtime
        .last_cash_settlements[
            "BTCUSDT"
        ]
        .appended
        is True
    )

    assert calls == [
        (
            Decimal("1012.50"),
            (),
        )
    ]

    assert (
        result
        .portfolio_snapshot
        .cash_pln
        == Decimal("1012.50")
    )

    assert (
        result
        .portfolio_snapshot
        .equity_pln
        == Decimal("1012.50")
    )


def test_runtime_requires_same_realized_journal_instance(
    tmp_path,
):
    cash = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl",
        clock=FixedClock(),
    )

    cash.initialize(
        "1000"
    )

    first = RealizedAccountingJournal(
        tmp_path / "first.jsonl",
        clock=FixedClock(),
    )

    second = RealizedAccountingJournal(
        tmp_path / "second.jsonl",
        clock=FixedClock(),
    )

    base = FakePhase10Runtime(
        result=close_cycle_result(),
        positions={},
    )

    persisting = (
        PersistingAccountingRuntime(
            runtime=base,
            journal=first,
            startup_metadata=(
                startup_metadata()
            ),
        )
    )

    with pytest.raises(
        Phase11CashRuntimeError,
        match="REALIZED_JOURNAL_INSTANCE_MISMATCH",
    ):
        Phase11CashAccountingRuntime(
            persisting_runtime=(
                persisting
            ),
            cash_ledger=cash,
            realized_journal=second,
            portfolio_snapshot_builder=(
                lambda **kwargs: None
            ),
        )


def test_wire_phase11_passes_authoritative_cash_resolver_and_reconciles(
    tmp_path,
    monkeypatch,
):
    realized = RealizedAccountingJournal(
        tmp_path
        / "phase10_realized_accounting.jsonl",
        clock=FixedClock(),
    )

    append_realized(
        realized,
        pln=Decimal("-5"),
    )

    cash = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl",
        clock=FixedClock(),
    )

    cash.initialize(
        "1000"
    )

    captured = {}

    fake_accounting_bridge = (
        SimpleNamespace(
            portfolio_snapshot=(
                lambda **kwargs: (
                    SimpleNamespace(
                        **kwargs
                    )
                )
            )
        )
    )

    fake_phase10_runtime = (
        FakePhase10Runtime(
            result=(
                RuntimeAccountingCycleResult(
                    execution_cycle=(
                        SimpleNamespace(
                            results={}
                        )
                    ),
                    accounting_results=(
                        MappingProxyType(
                            {}
                        )
                    ),
                    portfolio_snapshot=None,
                    limitations=(),
                )
            ),
            positions={},
        )
    )

    fake_phase10_bundle = (
        SimpleNamespace(
            wiring=SimpleNamespace(
                runtime=(
                    fake_phase10_runtime
                ),
                accounting_bridge=(
                    fake_accounting_bridge
                ),
            ),
            startup_metadata=(
                startup_metadata()
            ),
        )
    )

    def fake_wire(
        **kwargs,
    ):
        captured.update(
            kwargs
        )

        return fake_phase10_bundle

    monkeypatch.setattr(
        cash_runtime_module,
        "wire_phase10_production_runtime",
        fake_wire,
    )

    result = wire_phase11_cash_runtime(
        runtime=SimpleNamespace(),
        broker=SimpleNamespace(),
        runtime_flags=SimpleNamespace(),
        policy=SimpleNamespace(),
        cash_ledger=cash,
        realized_journal=realized,
        clock=FixedClock(),
    )

    assert (
        cash.current_cash_pln()
        == Decimal("995")
    )

    assert (
        len(
            result
            .startup_reconciliation
        )
        == 1
    )

    resolver = captured[
        "cash_pln_resolver"
    ]

    assert resolver() == Decimal("995")

    assert (
        result.cash_ledger
        is cash
    )

    assert (
        result.realized_journal
        is realized
    )


def test_reconciliation_tampered_realized_journal_fails_closed(
    tmp_path,
):
    realized = RealizedAccountingJournal(
        tmp_path
        / "phase10_realized_accounting.jsonl",
        clock=FixedClock(),
    )

    append_realized(
        realized
    )

    text = (
        realized.path
        .read_text(
            encoding="utf-8"
        )
    )

    realized.path.write_text(
        text.replace(
            '"net_realized_pnl_pln":"12.50"',
            '"net_realized_pnl_pln":"999"',
        ),
        encoding="utf-8",
    )

    cash = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl",
        clock=FixedClock(),
    )

    cash.initialize(
        "1000"
    )

    with pytest.raises(
        ValueError,
    ):
        reconcile_cash_ledger(
            cash_ledger=cash,
            realized_journal=realized,
        )

    assert (
        cash.current_cash_pln()
        == Decimal("1000")
    )
