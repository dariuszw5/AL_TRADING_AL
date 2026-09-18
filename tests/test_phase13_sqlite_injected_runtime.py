from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.persistence.sqlite_bootstrap import (
    bootstrap_fresh_database,
)
from src.persistence.sqlite_injected_runtime import (
    InjectedCycleWrite,
    SQLiteInjectedRuntime,
    SQLiteInjectedRuntimeError,
)
from src.persistence.sqlite_repository import (
    SQLiteLedgerRepository,
)


T0 = "2026-09-18T23:30:00.000000Z"
T1 = "2026-09-18T23:31:00.000000Z"


def order_payload(
    *,
    order_id,
    client_order_id,
    intent,
    side,
    timestamp,
):
    return {
        "order_id": order_id,
        "client_order_id": client_order_id,
        "asset_id": "BTCUSDT",
        "strategy_id": "PHASE13_A16_TEST",
        "intent": intent,
        "side": side,
        "quantity_native": "1",
        "signal_reference": "PHASE13_A16",
        "source_timestamp_utc": timestamp,
        "created_at_utc": timestamp,
        "execution_profile": "REALISTIC_V2",
        "paper_mode": "realistic_paper",
        "status": "FILLED",
        "config_hash": "config-a16",
        "order_fingerprint": "fingerprint-" + client_order_id,
        "raw_json": {"phase": "13A16"},
    }


def execution_payload(
    *,
    execution_id,
    order_id,
    side,
    price,
    timestamp,
):
    return {
        "execution_id": execution_id,
        "order_id": order_id,
        "asset_id": "BTCUSDT",
        "side": side,
        "quantity_native": "1",
        "reference_price_native": price,
        "execution_price_native": price,
        "bid_native": price,
        "ask_native": price,
        "spread_native": "0",
        "slippage_native": "0",
        "fee_native": "0",
        "fee_pln": "0",
        "provider_timestamp_utc": timestamp,
        "execution_timestamp_utc": timestamp,
        "data_quality": "REALTIME_BOOK",
        "execution_quality": "REAL_BOOK",
        "session_quality": "EXCHANGE_CALENDAR",
        "fx_path": "USDT->USD->PLN",
        "fx_rate": "4",
        "fx_provider": "TEST",
        "fx_timestamp_utc": timestamp,
        "fx_quality": "LIVE",
        "config_hash": "config-a16",
        "raw_json": {"phase": "13A16"},
    }


def open_position():
    return {
        "position_id": "position-a16",
        "asset_id": "BTCUSDT",
        "side": "LONG",
        "quantity_native": "1",
        "entry_execution_id": "execution-entry-a16",
        "exit_execution_id": None,
        "entry_price_native": "100",
        "exit_price_native": None,
        "stop_loss_native": "95",
        "take_profit_native": "110",
        "status": "OPEN",
        "opened_at_utc": T0,
        "closed_at_utc": None,
        "short_mechanism": None,
        "short_financing_model": None,
        "execution_profile": "REALISTIC_V2",
        "execution_quality_at_entry": "REAL_BOOK",
        "unrealized_pnl_native": "0",
        "unrealized_pnl_pln": "0",
        "raw_json": {
            "phase": "13A16",
            "state": "open",
        },
    }


def closed_position():
    result = dict(open_position())
    result.update(
        {
            "exit_execution_id": "execution-exit-a16",
            "exit_price_native": "106.25",
            "status": "CLOSED",
            "closed_at_utc": T1,
            "raw_json": {
                "phase": "13A16",
                "state": "closed",
            },
        }
    )
    return result


def trade_payload():
    return {
        "trade_id": "trade-a16",
        "asset_id": "BTCUSDT",
        "position_id": "position-a16",
        "entry_execution_id": "execution-entry-a16",
        "exit_execution_id": "execution-exit-a16",
        "quantity_native": "1",
        "realized_pnl_native": "6.25",
        "realized_pnl_pln": "25",
        "fees_pln": "0",
        "spread_cost_pln": "0",
        "slippage_pln": "0",
        "realized_fx_pair": "USDPLN",
        "realized_fx_path": "USDT->USD->PLN",
        "realized_fx_rate": "4",
        "realized_fx_provider": "TEST",
        "realized_fx_timestamp_utc": T1,
        "realized_fx_quality": "LIVE",
        "realized_transaction_id": "txn-realized-a16",
        "opened_at_utc": T0,
        "closed_at_utc": T1,
        "raw_json": {"phase": "13A16"},
    }


def transaction_payload():
    return {
        "transaction_id": "txn-realized-a16",
        "transaction_type": "REALIZED_PNL",
        "amount_pln": "25",
        "asset_id": "BTCUSDT",
        "reference_type": "TRADE",
        "reference_id": "trade-a16",
        "booked_at_utc": T1,
        "fx_pair": "USDPLN",
        "fx_path": "USDT->USD->PLN",
        "fx_rate": "4",
        "fx_provider": "TEST",
        "fx_timestamp_utc": T1,
        "fx_quality": "LIVE",
        "raw_json": {"phase": "13A16"},
    }


class FakeRuntime:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []
        self.memory = {"value": "initial"}

    def run_cycle(self, asset_ids):
        self.calls.append(tuple(asset_ids))
        self.memory = {"value": "changed"}

        if not self.results:
            raise RuntimeError("no fake runtime result")

        return self.results.pop(0)


def snapshot(runtime):
    return dict(runtime.memory)


def restore(runtime, value):
    runtime.memory = dict(value)


def entry_write():
    return InjectedCycleWrite(
        intent="ENTRY",
        processed_timestamp_utc=T0,
        updated_at_utc=T0,
        order=order_payload(
            order_id="order-entry-a16",
            client_order_id="client-entry-a16",
            intent="ENTRY",
            side="BUY",
            timestamp=T0,
        ),
        execution=execution_payload(
            execution_id="execution-entry-a16",
            order_id="order-entry-a16",
            side="BUY",
            price="100",
            timestamp=T0,
        ),
        position=open_position(),
    )


def exit_write():
    return InjectedCycleWrite(
        intent="EXIT",
        processed_timestamp_utc=T1,
        updated_at_utc=T1,
        reconciliation_event_id="reconcile-a16",
        order=order_payload(
            order_id="order-exit-a16",
            client_order_id="client-exit-a16",
            intent="EXIT",
            side="SELL",
            timestamp=T1,
        ),
        execution=execution_payload(
            execution_id="execution-exit-a16",
            order_id="order-exit-a16",
            side="SELL",
            price="106.25",
            timestamp=T1,
        ),
        position=closed_position(),
        trade=trade_payload(),
        portfolio_transaction=transaction_payload(),
    )


def bootstrap_temp(path, *, clear_halt=True):
    bootstrap_fresh_database(
        path,
        initial_cash_pln="1000",
        bootstrap_id="phase13-a16-test",
        created_at_utc=T0,
    )

    if clear_halt:
        repo = SQLiteLedgerRepository.open_writer(path)
        try:
            with repo.atomic_cycle():
                repo.clear_halt_explicitly(
                    reason="A16 temp activation",
                    updated_at_utc=T0,
                    event_id="a16-temp-clear",
                    event_timestamp_utc=T0,
                )
        finally:
            repo.close()


def mapper_from(write):
    def mapper(*, asset_id, runtime_result):
        assert asset_id == "BTCUSDT"
        assert runtime_result is not None
        return write

    return mapper


def test_live_database_path_is_refused(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    live = tmp_path / "data" / "live" / "trading.db"
    live.parent.mkdir(parents=True)
    live.write_bytes(b"not-used")

    runtime = FakeRuntime([object()])

    with pytest.raises(
        SQLiteInjectedRuntimeError,
        match="live",
    ):
        SQLiteInjectedRuntime(
            runtime=runtime,
            database_path=live,
            live_database_path=live,
            cycle_mapper=mapper_from(entry_write()),
            snapshot_provider=lambda: snapshot(runtime),
            restore_snapshot=lambda value: restore(runtime, value),
        )


def test_entry_cycle_is_persisted_after_runtime_result(tmp_path):
    path = tmp_path / "a16-entry.db"
    bootstrap_temp(path)

    result_object = object()
    runtime = FakeRuntime([result_object])

    injected = SQLiteInjectedRuntime(
        runtime=runtime,
        database_path=path,
        live_database_path=tmp_path / "forbidden-live.db",
        cycle_mapper=mapper_from(entry_write()),
        snapshot_provider=lambda: snapshot(runtime),
        restore_snapshot=lambda value: restore(runtime, value),
    )

    try:
        result = injected.run_cycle(["BTCUSDT"])

        assert result.runtime_result is result_object
        assert result.persisted is True
        assert result.blocked_by_halt is False
        assert runtime.calls == [("BTCUSDT",)]

        repo = injected.repository

        assert repo.count_rows("orders") == 1
        assert repo.count_rows("executions") == 1
        assert repo.count_rows("positions") == 1
        assert repo.read_last_processed_timestamp() == T0
    finally:
        injected.close()


def test_restart_then_halt_blocks_asset_without_open_position(tmp_path):
    path = tmp_path / "a16-halt-block.db"
    bootstrap_temp(path, clear_halt=False)

    runtime = FakeRuntime([object()])

    injected = SQLiteInjectedRuntime(
        runtime=runtime,
        database_path=path,
        live_database_path=tmp_path / "forbidden-live.db",
        cycle_mapper=mapper_from(entry_write()),
        snapshot_provider=lambda: snapshot(runtime),
        restore_snapshot=lambda value: restore(runtime, value),
    )

    try:
        result = injected.run_cycle(["BTCUSDT"])

        assert result.runtime_result is None
        assert result.persisted is False
        assert result.blocked_by_halt is True
        assert runtime.calls == []
        assert injected.repository.count_rows("orders") == 0
    finally:
        injected.close()


def test_halt_allows_existing_open_position_exit(tmp_path):
    path = tmp_path / "a16-halt-exit.db"
    bootstrap_temp(path)

    entry_runtime = FakeRuntime([object()])
    entry_mode = SQLiteInjectedRuntime(
        runtime=entry_runtime,
        database_path=path,
        live_database_path=tmp_path / "forbidden-live.db",
        cycle_mapper=mapper_from(entry_write()),
        snapshot_provider=lambda: snapshot(entry_runtime),
        restore_snapshot=lambda value: restore(
            entry_runtime,
            value,
        ),
    )

    entry_mode.run_cycle(["BTCUSDT"])

    with entry_mode.repository.atomic_cycle():
        entry_mode.repository.set_halt(
            reason="A16_TEST_HALT",
            updated_at_utc=T1,
            event_id="a16-test-halt",
            event_timestamp_utc=T1,
        )

    entry_mode.close()

    exit_runtime = FakeRuntime([object()])
    exit_mode = SQLiteInjectedRuntime(
        runtime=exit_runtime,
        database_path=path,
        live_database_path=tmp_path / "forbidden-live.db",
        cycle_mapper=mapper_from(exit_write()),
        snapshot_provider=lambda: snapshot(exit_runtime),
        restore_snapshot=lambda value: restore(
            exit_runtime,
            value,
        ),
    )

    try:
        result = exit_mode.run_cycle(["BTCUSDT"])

        assert result.persisted is True
        assert result.blocked_by_halt is False
        assert exit_runtime.calls == [("BTCUSDT",)]

        repo = exit_mode.repository

        row = repo.connection.execute(
            "SELECT * FROM positions WHERE position_id = ?",
            ("position-a16",),
        ).fetchone()

        assert row["status"] == "CLOSED"
        assert Decimal(
            repo.read_system_state()["cash_balance_pln"]
        ) == Decimal("1025")
        assert repo.count_rows("trades") == 1
        assert repo.read_last_processed_timestamp() == T1

        state = repo.read_system_state()
        assert state["halted"] == 1
        assert state["halt_reason"] == "A16_TEST_HALT"
    finally:
        exit_mode.close()


def test_persistence_failure_restores_runtime_memory(tmp_path):
    path = tmp_path / "a16-restore.db"
    bootstrap_temp(path)

    runtime = FakeRuntime([object()])

    broken = entry_write()
    broken_order = dict(broken.order)
    broken_order["order_id"] = ""
    broken = InjectedCycleWrite(
        intent=broken.intent,
        processed_timestamp_utc=broken.processed_timestamp_utc,
        updated_at_utc=broken.updated_at_utc,
        order=broken_order,
        execution=broken.execution,
        position=broken.position,
    )

    injected = SQLiteInjectedRuntime(
        runtime=runtime,
        database_path=path,
        live_database_path=tmp_path / "forbidden-live.db",
        cycle_mapper=mapper_from(broken),
        snapshot_provider=lambda: snapshot(runtime),
        restore_snapshot=lambda value: restore(runtime, value),
    )

    assert runtime.memory == {"value": "initial"}

    try:
        with pytest.raises(Exception):
            injected.run_cycle(["BTCUSDT"])

        assert runtime.memory == {"value": "initial"}
        assert injected.repository.count_rows("orders") == 0
        assert injected.repository.count_rows("executions") == 0
        assert injected.repository.count_rows("positions") == 0
    finally:
        injected.close()


def test_a16_is_single_asset_only(tmp_path):
    path = tmp_path / "a16-single-only.db"
    bootstrap_temp(path)

    runtime = FakeRuntime([object()])

    injected = SQLiteInjectedRuntime(
        runtime=runtime,
        database_path=path,
        live_database_path=tmp_path / "forbidden-live.db",
        cycle_mapper=mapper_from(entry_write()),
        snapshot_provider=lambda: snapshot(runtime),
        restore_snapshot=lambda value: restore(runtime, value),
    )

    try:
        with pytest.raises(
            SQLiteInjectedRuntimeError,
            match="exactly one asset",
        ):
            injected.run_cycle(
                ["BTCUSDT", "ETHUSDT"]
            )

        assert runtime.calls == []
    finally:
        injected.close()
