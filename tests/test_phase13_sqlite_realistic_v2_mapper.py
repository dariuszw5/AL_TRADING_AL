from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.persistence.sqlite_bootstrap import (
    bootstrap_fresh_database,
)
from src.persistence.sqlite_injected_runtime import (
    SQLiteInjectedRuntime,
)
from src.persistence.sqlite_realistic_v2_mapper import (
    RealisticV2SQLiteMapper,
    RealisticV2SQLiteMapperError,
)
from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)


UTC = timezone.utc
T0 = datetime(2026, 9, 18, 23, 45, tzinfo=UTC)
T1 = datetime(2026, 9, 18, 23, 46, tzinfo=UTC)


def enum(value):
    return SimpleNamespace(value=value)


def order(*, intent, side, created_at):
    suffix = intent.lower()

    return SimpleNamespace(
        order_id=f"order-{suffix}-a17",
        client_order_id=f"client-{suffix}-a17",
        asset_id="BTCUSDT",
        side=enum(side),
        quantity=1.0,
        intent=enum(intent),
        created_at=created_at,
        execution_profile=enum("REALISTIC_V2"),
        paper_mode=enum("realistic_paper"),
        signal_reference="A17_SIGNAL",
        stop_loss=95.0,
        take_profit=110.0,
    )


def execution(*, intent, side, price, timestamp):
    suffix = intent.lower()

    return SimpleNamespace(
        execution_id=f"execution-{suffix}-a17",
        order_id=f"order-{suffix}-a17",
        asset_id="BTCUSDT",
        side=enum(side),
        quantity=1.0,
        reference_price=price,
        execution_price=price,
        bid=price,
        ask=price,
        spread=0.0,
        slippage=0.0,
        fee=0.1,
        provider_timestamp=timestamp,
        execution_timestamp=timestamp,
        data_quality=enum("REALTIME"),
        execution_quality=enum("REAL_BOOK"),
        session_quality=enum("EXCHANGE_CALENDAR"),
        paper_mode=enum("realistic_paper"),
        config_hash="a" * 64,
    )


def open_position():
    return SimpleNamespace(
        position_id="position-a17",
        asset_id="BTCUSDT",
        side=enum("LONG"),
        quantity=1.0,
        entry_execution_id="execution-entry-a17",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        opened_at=T0,
        short_mechanism=None,
        short_financing_model=None,
        execution_profile=enum("REALISTIC_V2"),
        execution_quality_at_entry=enum("REAL_BOOK"),
        status=enum("OPEN"),
        closed_at=None,
        exit_execution_id=None,
        exit_price=None,
        pending_exit_reason=None,
        pending_since=None,
    )


def closed_position():
    return SimpleNamespace(
        position_id="position-a17",
        asset_id="BTCUSDT",
        side=enum("LONG"),
        quantity=1.0,
        entry_execution_id="execution-entry-a17",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        opened_at=T0,
        short_mechanism=None,
        short_financing_model=None,
        execution_profile=enum("REALISTIC_V2"),
        execution_quality_at_entry=enum("REAL_BOOK"),
        status=enum("CLOSED"),
        closed_at=T1,
        exit_execution_id="execution-exit-a17",
        exit_price=106.25,
        pending_exit_reason=None,
        pending_since=None,
    )


def realized_result():
    accounting = SimpleNamespace(
        native_currency="USDT",
        net_realized_pnl_native=Decimal("6.25"),
        fx_rate=Decimal("4"),
        fx_path="USDT->USD->PLN",
        net_realized_pnl_pln=Decimal("25"),
    )

    booking = SimpleNamespace(
        fx_provider="TEST",
        fx_table="A17",
        fx_effective_date="2026-09-18",
        fx_path="USDT->USD->PLN",
    )

    return SimpleNamespace(
        accounting_record=accounting,
        fx_booking=booking,
        limitations=(),
    )


def broker_result(*, intent):
    is_entry = intent == "ENTRY"

    return SimpleNamespace(
        status=enum("FILLED"),
        order=order(
            intent=intent,
            side="BUY" if is_entry else "SELL",
            created_at=T0 if is_entry else T1,
        ),
        execution=execution(
            intent=intent,
            side="BUY" if is_entry else "SELL",
            price=100.0 if is_entry else 106.25,
            timestamp=T0 if is_entry else T1,
        ),
        position=(
            open_position()
            if is_entry
            else closed_position()
        ),
    )


def cycle_result(*, intent, status="FILLED"):
    asset_result = SimpleNamespace(
        status=enum(status),
        broker_result=(
            broker_result(intent=intent)
            if status == "FILLED"
            else None
        ),
    )

    accounting_result = SimpleNamespace(
        error=None,
        limitations=(),
        mtm_record=None,
        realized_result=(
            realized_result()
            if intent == "EXIT" and status == "FILLED"
            else None
        ),
    )

    return SimpleNamespace(
        execution_cycle=SimpleNamespace(
            results={
                "BTCUSDT": asset_result,
            }
        ),
        accounting_results={
            "BTCUSDT": accounting_result,
        },
        limitations=(),
    )


def execution_evidence(*, execution, intent, realized_result):
    timestamp = execution.execution_timestamp

    return {
        "fee_pln": (
            "0.4"
            if intent == "ENTRY"
            else "0.44"
        ),
        "fx_path": "USDT->USD->PLN",
        "fx_rate": "4",
        "fx_provider": "TEST",
        "fx_timestamp_utc": timestamp,
        "fx_quality": "LIVE",
    }


def realized_evidence(*, asset_id, position, execution, realized_result):
    return {
        "fees_pln": "0.84",
        "spread_cost_pln": "0.1",
        "slippage_pln": "0.2",
        "fx_pair": "USDPLN",
        "fx_provider": "TEST",
        "fx_timestamp_utc": execution.execution_timestamp,
        "fx_quality": "LIVE",
    }


def mapper():
    return RealisticV2SQLiteMapper(
        order_fingerprint_resolver=(
            lambda order: (
                "fingerprint-"
                + order.client_order_id
            )
        ),
        execution_evidence_resolver=execution_evidence,
        realized_evidence_resolver=realized_evidence,
        strategy_id="PHASE13_A17",
    )


def bootstrap_temp(path):
    bootstrap_fresh_database(
        path,
        initial_cash_pln="1000",
        bootstrap_id="phase13-a17",
        created_at_utc="2026-09-18T23:44:00Z",
    )

    repo = SQLiteLedgerRepository.open_writer(path)

    try:
        with repo.atomic_cycle():
            repo.clear_halt_explicitly(
                reason="A17 temp activation",
                updated_at_utc="2026-09-18T23:44:00Z",
                event_id="a17-temp-clear",
                event_timestamp_utc="2026-09-18T23:44:00Z",
            )
    finally:
        repo.close()


def test_entry_result_maps_to_sqlite_payloads():
    write = mapper()(
        asset_id="BTCUSDT",
        runtime_result=cycle_result(
            intent="ENTRY"
        ),
    )

    assert write.intent == "ENTRY"
    assert write.order["client_order_id"] == "client-entry-a17"
    assert write.order["order_fingerprint"] == (
        "fingerprint-client-entry-a17"
    )
    assert write.execution["config_hash"] == "a" * 64
    assert write.execution["fee_pln"] == "0.4"
    assert write.position["status"] == "OPEN"
    assert write.position["unrealized_pnl_native"] == "0"
    assert write.position["unrealized_pnl_pln"] == "0"


def test_exit_result_maps_realized_evidence_without_fabrication():
    write = mapper()(
        asset_id="BTCUSDT",
        runtime_result=cycle_result(
            intent="EXIT"
        ),
    )

    assert write.intent == "EXIT"
    assert write.position["status"] == "CLOSED"
    assert write.trade["realized_pnl_native"] == "6.25"
    assert write.trade["realized_pnl_pln"] == "25"
    assert write.trade["fees_pln"] == "0.84"
    assert write.trade["spread_cost_pln"] == "0.1"
    assert write.trade["slippage_pln"] == "0.2"
    assert write.portfolio_transaction["amount_pln"] == "25"
    assert (
        write.trade["realized_transaction_id"]
        == write.portfolio_transaction["transaction_id"]
    )
    assert write.trade["trade_id"] == (
        write.portfolio_transaction["reference_id"]
    )


def test_non_filled_result_maps_to_noop():
    write = mapper()(
        asset_id="BTCUSDT",
        runtime_result=cycle_result(
            intent="ENTRY",
            status="NO_SIGNAL",
        ),
    )

    assert write.intent == "NOOP"
    assert write.order is None
    assert write.execution is None
    assert write.position is None


def test_missing_execution_evidence_fails_closed():
    bad = RealisticV2SQLiteMapper(
        order_fingerprint_resolver=(
            lambda order: "fingerprint"
        ),
        execution_evidence_resolver=(
            lambda **kwargs: {}
        ),
        realized_evidence_resolver=realized_evidence,
    )

    with pytest.raises(
        RealisticV2SQLiteMapperError,
        match="fee_pln",
    ):
        bad(
            asset_id="BTCUSDT",
            runtime_result=cycle_result(
                intent="ENTRY"
            ),
        )


def test_missing_realized_evidence_fails_closed():
    bad = RealisticV2SQLiteMapper(
        order_fingerprint_resolver=(
            lambda order: "fingerprint"
        ),
        execution_evidence_resolver=execution_evidence,
        realized_evidence_resolver=(
            lambda **kwargs: {}
        ),
    )

    with pytest.raises(
        RealisticV2SQLiteMapperError,
        match="fees_pln",
    ):
        bad(
            asset_id="BTCUSDT",
            runtime_result=cycle_result(
                intent="EXIT"
            ),
        )


class FakeRuntime:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []
        self.memory = {}

    def run_cycle(self, asset_ids):
        self.calls.append(tuple(asset_ids))
        result = self.results.pop(0)
        self.memory["last"] = result
        return result


def test_injected_composition_entry_restart_halt_exit(tmp_path):
    path = tmp_path / "a17-composition.db"
    bootstrap_temp(path)

    entry_runtime = FakeRuntime(
        [
            cycle_result(
                intent="ENTRY"
            ),
        ]
    )

    entry_mode = SQLiteInjectedRuntime(
        runtime=entry_runtime,
        database_path=path,
        live_database_path=tmp_path / "forbidden-live.db",
        cycle_mapper=mapper(),
        snapshot_provider=lambda: dict(entry_runtime.memory),
        restore_snapshot=lambda value: (
            entry_runtime.memory.clear(),
            entry_runtime.memory.update(value),
        ),
    )

    entry_result = entry_mode.run_cycle(
        ["BTCUSDT"]
    )

    assert entry_result.persisted is True
    assert entry_mode.repository.count_rows("orders") == 1
    entry_mode.close()

    repo = SQLiteLedgerRepository.open_writer(path)
    try:
        with repo.atomic_cycle():
            repo.set_halt(
                reason="A17_TEST_HALT",
                updated_at_utc="2026-09-18T23:46:00Z",
                event_id="a17-halt",
                event_timestamp_utc="2026-09-18T23:46:00Z",
            )
    finally:
        repo.close()

    exit_runtime = FakeRuntime(
        [
            cycle_result(
                intent="EXIT"
            ),
        ]
    )

    exit_mode = SQLiteInjectedRuntime(
        runtime=exit_runtime,
        database_path=path,
        live_database_path=tmp_path / "forbidden-live.db",
        cycle_mapper=mapper(),
        snapshot_provider=lambda: dict(exit_runtime.memory),
        restore_snapshot=lambda value: (
            exit_runtime.memory.clear(),
            exit_runtime.memory.update(value),
        ),
    )

    try:
        exit_result = exit_mode.run_cycle(
            ["BTCUSDT"]
        )

        assert exit_result.persisted is True

        repo = exit_mode.repository
        state = repo.read_system_state()

        assert state["halted"] == 1
        assert state["halt_reason"] == "A17_TEST_HALT"
        assert Decimal(
            state["cash_balance_pln"]
        ) == Decimal("1025")
        assert repo.count_rows("orders") == 2
        assert repo.count_rows("executions") == 2
        assert repo.count_rows("trades") == 1

        position = repo.connection.execute(
            "SELECT * FROM positions WHERE position_id = ?",
            ("position-a17",),
        ).fetchone()

        assert position["status"] == "CLOSED"
    finally:
        exit_mode.close()


def test_noop_injected_result_reports_not_persisted(tmp_path):
    path = tmp_path / "a17-noop.db"
    bootstrap_temp(path)

    runtime = FakeRuntime(
        [
            cycle_result(
                intent="ENTRY",
                status="NO_SIGNAL",
            ),
        ]
    )

    mode = SQLiteInjectedRuntime(
        runtime=runtime,
        database_path=path,
        live_database_path=tmp_path / "forbidden-live.db",
        cycle_mapper=mapper(),
        snapshot_provider=lambda: dict(runtime.memory),
        restore_snapshot=lambda value: (
            runtime.memory.clear(),
            runtime.memory.update(value),
        ),
    )

    try:
        result = mode.run_cycle(
            ["BTCUSDT"]
        )

        assert result.persisted is False
        assert result.blocked_by_halt is False
        assert mode.repository.count_rows("orders") == 0
        assert mode.repository.count_rows("executions") == 0
    finally:
        mode.close()
