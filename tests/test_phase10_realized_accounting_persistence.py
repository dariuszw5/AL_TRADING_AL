from datetime import (
    date,
    datetime,
    timezone,
)
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.accounting.realized_persistence import (
    PersistingAccountingRuntime,
    RealizedAccountingJournal,
    RealizedAccountingStoreError,
)


UTC = timezone.utc

NOW = datetime(
    2026,
    9,
    18,
    12,
    0,
    tzinfo=UTC,
)


class FixedClock:
    def now(self):
        return NOW


def startup_metadata():
    return SimpleNamespace(
        global_config_hash=("b" * 64),
    )


def position(*, exit_execution_id="exec-exit"):
    return SimpleNamespace(
        asset_id="BTCUSDT",
        position_id="pos-1",
        entry_execution_id="exec-entry",
        exit_execution_id=exit_execution_id,
        closed_at=NOW,
    )


def exit_execution(
    *,
    execution_id="exec-exit",
    config_hash="a" * 64,
):
    return SimpleNamespace(
        asset_id="BTCUSDT",
        execution_id=execution_id,
        config_hash=config_hash,
    )


def realized_result(
    *,
    native=Decimal("-0.01"),
    pln=Decimal("-0.038"),
):
    accounting = SimpleNamespace(
        native_currency="USDT",
        net_realized_pnl_native=native,
        fx_rate=Decimal("3.8"),
        fx_path="USDT\u2192USD\u2192PLN",
        net_realized_pnl_pln=pln,
    )

    fx_booking = SimpleNamespace(
        fx_provider="NBP_TABLE_A",
        fx_table="180/A/NBP/2026",
        fx_effective_date=date(
            2026,
            9,
            18,
        ),
        fx_path="USDT\u2192USD\u2192PLN",
    )

    return SimpleNamespace(
        accounting_record=accounting,
        fx_booking=fx_booking,
        limitations=(
            "KNOWN_LIMITATION: FX_CONVERSION_COST_NOT_MODELLED",
        ),
    )


def append(
    journal,
    *,
    position_value=None,
    exit_value=None,
    realized_value=None,
):
    return journal.append_booking(
        asset_id="BTCUSDT",
        position=position_value or position(),
        exit_execution=exit_value or exit_execution(),
        realized_result=realized_value or realized_result(),
        startup_metadata=startup_metadata(),
    )


def test_append_round_trip_contains_identity_pnl_fx_and_hashes(
    tmp_path,
):
    path = (
        tmp_path
        / "phase10_realized_accounting.jsonl"
    )

    journal = RealizedAccountingJournal(
        path,
        clock=FixedClock(),
    )

    result = append(journal)

    assert result.appended is True

    records = journal.read_records()

    assert len(records) == 1

    record = records[0]

    assert record["asset_id"] == "BTCUSDT"
    assert record["position_id"] == "pos-1"
    assert record["entry_execution_id"] == "exec-entry"
    assert record["exit_execution_id"] == "exec-exit"
    assert record["net_realized_pnl_native"] == "-0.01"
    assert record["fx_rate"] == "3.8"
    assert record["fx_path"] == "USDT\u2192USD\u2192PLN"
    assert record["net_realized_pnl_pln"] == "-0.038"
    assert record["execution_config_hash"] == "a" * 64
    assert record["global_config_hash"] == "b" * 64
    assert (
        record["fx_evidence"]["fx_provider"]
        == "NBP_TABLE_A"
    )
    assert len(record["record_hash"]) == 64
    assert len(record["booking_key"]) == 64


def test_second_identical_booking_is_idempotent_without_append(
    tmp_path,
):
    path = (
        tmp_path
        / "phase10_realized_accounting.jsonl"
    )

    journal = RealizedAccountingJournal(
        path,
        clock=FixedClock(),
    )

    first = append(journal)
    first_bytes = path.read_bytes()
    second = append(journal)

    assert first.appended is True
    assert second.appended is False
    assert (
        second.record["record_hash"]
        == first.record["record_hash"]
    )
    assert path.read_bytes() == first_bytes
    assert len(journal.read_records()) == 1


def test_same_identity_with_different_pnl_fails_idempotency(
    tmp_path,
):
    path = (
        tmp_path
        / "phase10_realized_accounting.jsonl"
    )

    journal = RealizedAccountingJournal(
        path,
        clock=FixedClock(),
    )

    append(journal)
    first_bytes = path.read_bytes()

    with pytest.raises(
        RealizedAccountingStoreError,
        match="REALIZED_ACCOUNTING_IDEMPOTENCY_CONFLICT",
    ):
        append(
            journal,
            realized_value=realized_result(
                pln=Decimal("-0.039")
            ),
        )

    assert path.read_bytes() == first_bytes


def test_tampered_record_fails_closed(tmp_path):
    path = (
        tmp_path
        / "phase10_realized_accounting.jsonl"
    )

    journal = RealizedAccountingJournal(
        path,
        clock=FixedClock(),
    )

    append(journal)

    text = path.read_text(
        encoding="utf-8"
    )

    path.write_text(
        text.replace(
            '"net_realized_pnl_pln":"-0.038"',
            '"net_realized_pnl_pln":"999"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        RealizedAccountingStoreError,
        match="REALIZED_ACCOUNTING_RECORD_HASH_MISMATCH",
    ):
        journal.read_records()


def test_duplicate_booking_key_in_file_fails_closed(
    tmp_path,
):
    path = (
        tmp_path
        / "phase10_realized_accounting.jsonl"
    )

    journal = RealizedAccountingJournal(
        path,
        clock=FixedClock(),
    )

    append(journal)

    line = path.read_text(
        encoding="utf-8"
    )

    path.write_text(
        line + line,
        encoding="utf-8",
    )

    with pytest.raises(
        RealizedAccountingStoreError,
        match="REALIZED_ACCOUNTING_DUPLICATE_BOOKING_KEY",
    ):
        journal.read_records()


def test_exit_execution_mismatch_fails_before_file_creation(
    tmp_path,
):
    path = (
        tmp_path
        / "phase10_realized_accounting.jsonl"
    )

    journal = RealizedAccountingJournal(
        path,
        clock=FixedClock(),
    )

    with pytest.raises(
        RealizedAccountingStoreError,
        match="REALIZED_ACCOUNTING_EXIT_EXECUTION_MISMATCH",
    ):
        append(
            journal,
            position_value=position(
                exit_execution_id="expected"
            ),
            exit_value=exit_execution(
                execution_id="actual"
            ),
        )

    assert not path.exists()


def cycle_result(*, realized=True):
    realized_value = (
        realized_result()
        if realized
        else None
    )

    return SimpleNamespace(
        execution_cycle=SimpleNamespace(
            results={
                "BTCUSDT": SimpleNamespace(
                    broker_result=SimpleNamespace(
                        position=position(),
                        execution=exit_execution(),
                    )
                ),
            }
        ),
        accounting_results={
            "BTCUSDT": SimpleNamespace(
                realized_result=realized_value
            ),
        },
    )


class FakeRuntime:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def run_cycle(self, asset_ids):
        self.calls.append(
            tuple(asset_ids)
        )
        return self.result


def test_runtime_wrapper_persists_successful_realized_result(
    tmp_path,
):
    path = (
        tmp_path
        / "phase10_realized_accounting.jsonl"
    )

    base = FakeRuntime(
        cycle_result(
            realized=True
        )
    )

    wrapper = PersistingAccountingRuntime(
        runtime=base,
        journal=RealizedAccountingJournal(
            path,
            clock=FixedClock(),
        ),
        startup_metadata=startup_metadata(),
    )

    result = wrapper.run_cycle(
        ["BTCUSDT"]
    )

    assert result is base.result
    assert base.calls == [
        ("BTCUSDT",)
    ]

    persisted = (
        wrapper.last_persistence["BTCUSDT"]
    )

    assert persisted.appended is True
    assert len(
        RealizedAccountingJournal(
            path
        ).read_records()
    ) == 1


def test_runtime_wrapper_does_not_create_file_without_realized_result(
    tmp_path,
):
    path = (
        tmp_path
        / "phase10_realized_accounting.jsonl"
    )

    base = FakeRuntime(
        cycle_result(
            realized=False
        )
    )

    wrapper = PersistingAccountingRuntime(
        runtime=base,
        journal=RealizedAccountingJournal(
            path,
            clock=FixedClock(),
        ),
        startup_metadata=startup_metadata(),
    )

    wrapper.run_cycle(
        ["BTCUSDT"]
    )

    assert dict(
        wrapper.last_persistence
    ) == {}

    assert not path.exists()
