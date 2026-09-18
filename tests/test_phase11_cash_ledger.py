from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.accounting.cash_ledger import (
    ENTRY_FEE_SETTLED_AT_REALIZATION,
    CashLedgerError,
    Phase11CashLedger,
)
from src.accounting.realized_persistence import (
    RealizedAccountingJournal,
)


UTC = timezone.utc

T0 = datetime(
    2026,
    9,
    18,
    14,
    0,
    tzinfo=UTC,
)


class FixedClock:
    def __init__(self, value=T0):
        self.value = value

    def now(self):
        return self.value


def startup_metadata():
    return SimpleNamespace(
        global_config_hash="b" * 64,
    )


def realized_result(
    *,
    pln=Decimal("-0.038"),
):
    accounting = SimpleNamespace(
        native_currency="USDT",
        net_realized_pnl_native=(
            Decimal("-0.01")
        ),
        fx_rate=Decimal("3.8"),
        fx_path="USDT\u2192USD\u2192PLN",
        net_realized_pnl_pln=pln,
    )

    fx_booking = SimpleNamespace(
        fx_provider="NBP_TABLE_A",
        fx_table="180/A/NBP/2026",
        fx_effective_date="2026-09-18",
        fx_path="USDT\u2192USD\u2192PLN",
    )

    return SimpleNamespace(
        accounting_record=accounting,
        fx_booking=fx_booking,
        limitations=(
            "KNOWN_LIMITATION: "
            "FX_CONVERSION_COST_NOT_MODELLED",
        ),
    )


def append_realized(
    journal,
    *,
    position_id="pos-1",
    entry_execution_id="exec-entry-1",
    exit_execution_id="exec-exit-1",
    pln=Decimal("-0.038"),
):
    position = SimpleNamespace(
        asset_id="BTCUSDT",
        position_id=position_id,
        entry_execution_id=(
            entry_execution_id
        ),
        exit_execution_id=(
            exit_execution_id
        ),
        closed_at=T0,
    )

    exit_execution = SimpleNamespace(
        asset_id="BTCUSDT",
        execution_id=exit_execution_id,
        config_hash="a" * 64,
    )

    return journal.append_booking(
        asset_id="BTCUSDT",
        position=position,
        exit_execution=exit_execution,
        realized_result=realized_result(
            pln=pln
        ),
        startup_metadata=(
            startup_metadata()
        ),
    )


def test_first_start_requires_explicit_initial_cash(
    tmp_path,
):
    ledger = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl",
        clock=FixedClock(),
    )

    with pytest.raises(
        CashLedgerError,
        match="INITIAL_CASH_PLN_REQUIRED",
    ):
        ledger.initialize()

    assert not ledger.path.exists()


def test_initialize_and_read_authoritative_cash(
    tmp_path,
):
    ledger = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl",
        clock=FixedClock(),
    )

    record = ledger.initialize(
        "1000.00"
    )

    assert (
        record["record_type"]
        == "INITIAL"
    )
    assert (
        record["cash_after_pln"]
        == "1000.00"
    )
    assert (
        ENTRY_FEE_SETTLED_AT_REALIZATION
        in record["limitations"]
    )
    assert (
        ledger.current_cash_pln()
        == Decimal("1000.00")
    )


def test_negative_initial_cash_is_allowed_accounting_state(
    tmp_path,
):
    ledger = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl",
        clock=FixedClock(),
    )

    ledger.initialize(
        "-10.25"
    )

    assert (
        ledger.current_cash_pln()
        == Decimal("-10.25")
    )


def test_restart_accepts_same_initial_and_rejects_conflict(
    tmp_path,
):
    path = (
        tmp_path
        / "phase11_cash_ledger.jsonl"
    )

    first = Phase11CashLedger(
        path,
        clock=FixedClock(),
    )

    first.initialize(
        "1000"
    )

    second = Phase11CashLedger(
        path,
        clock=FixedClock(),
    )

    second.initialize(
        "1000.00"
    )

    assert (
        second.current_cash_pln()
        == Decimal("1000")
    )

    third = Phase11CashLedger(
        path,
        clock=FixedClock(),
    )

    with pytest.raises(
        CashLedgerError,
        match="CASH_LEDGER_INITIAL_CASH_CONFLICT",
    ):
        third.initialize(
            "999"
        )


def test_missing_file_after_initialization_fails_closed(
    tmp_path,
):
    ledger = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl",
        clock=FixedClock(),
    )

    ledger.initialize(
        "1000"
    )

    ledger.path.unlink()

    with pytest.raises(
        CashLedgerError,
        match="CASH_LEDGER_MISSING_AFTER_INITIALIZATION",
    ):
        ledger.current_cash_pln()


def test_tampered_cash_record_fails_closed(
    tmp_path,
):
    path = (
        tmp_path
        / "phase11_cash_ledger.jsonl"
    )

    ledger = Phase11CashLedger(
        path,
        clock=FixedClock(),
    )

    ledger.initialize(
        "1000"
    )

    text = path.read_text(
        encoding="utf-8"
    )

    path.write_text(
        text.replace(
            '"cash_after_pln":"1000"',
            '"cash_after_pln":"999"',
        ),
        encoding="utf-8",
    )

    restarted = Phase11CashLedger(
        path,
        clock=FixedClock(),
    )

    with pytest.raises(
        CashLedgerError,
        match="CASH_LEDGER_RECORD_HASH_MISMATCH",
    ):
        restarted.initialize()


def test_settle_exact_persisted_realized_pln_once(
    tmp_path,
):
    realized = RealizedAccountingJournal(
        tmp_path
        / "phase10_realized_accounting.jsonl",
        clock=FixedClock(),
    )

    persisted = append_realized(
        realized,
        pln=Decimal("-0.038"),
    )

    cash = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl",
        clock=FixedClock(),
    )

    cash.initialize(
        "1000"
    )

    result = (
        cash
        .settle_from_realized_journal(
            realized_journal=realized,
            booking_key=(
                persisted.record[
                    "booking_key"
                ]
            ),
        )
    )

    assert result.appended is True
    assert (
        result.record[
            "cash_delta_pln"
        ]
        == "-0.038"
    )
    assert (
        result.record[
            "cash_before_pln"
        ]
        == "1000"
    )
    assert (
        result.record[
            "cash_after_pln"
        ]
        == "999.962"
    )
    assert (
        result.record[
            "source_realized_record_hash"
        ]
        == persisted.record[
            "record_hash"
        ]
    )
    assert (
        cash.current_cash_pln()
        == Decimal("999.962")
    )


def test_identical_realized_booking_is_restart_safe_idempotent(
    tmp_path,
):
    realized = RealizedAccountingJournal(
        tmp_path
        / "phase10_realized_accounting.jsonl",
        clock=FixedClock(),
    )

    persisted = append_realized(
        realized
    )

    cash_path = (
        tmp_path
        / "phase11_cash_ledger.jsonl"
    )

    first = Phase11CashLedger(
        cash_path,
        clock=FixedClock(),
    )

    first.initialize(
        "1000"
    )

    first_result = (
        first
        .settle_from_realized_journal(
            realized_journal=realized,
            booking_key=(
                persisted.record[
                    "booking_key"
                ]
            ),
        )
    )

    bytes_after_first = (
        cash_path.read_bytes()
    )

    restarted = Phase11CashLedger(
        cash_path,
        clock=FixedClock(),
    )

    restarted.initialize(
        "1000"
    )

    second_result = (
        restarted
        .settle_from_realized_journal(
            realized_journal=realized,
            booking_key=(
                persisted.record[
                    "booking_key"
                ]
            ),
        )
    )

    assert first_result.appended is True
    assert second_result.appended is False
    assert (
        cash_path.read_bytes()
        == bytes_after_first
    )
    assert (
        restarted.current_cash_pln()
        == Decimal("999.962")
    )


def test_same_exit_execution_cannot_settle_two_bookings(
    tmp_path,
):
    realized = RealizedAccountingJournal(
        tmp_path
        / "phase10_realized_accounting.jsonl",
        clock=FixedClock(),
    )

    first = append_realized(
        realized,
        position_id="pos-1",
        entry_execution_id="exec-entry-1",
        exit_execution_id="exec-exit-shared",
        pln=Decimal("1.25"),
    )

    second = append_realized(
        realized,
        position_id="pos-2",
        entry_execution_id="exec-entry-2",
        exit_execution_id="exec-exit-shared",
        pln=Decimal("2.50"),
    )

    cash = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl",
        clock=FixedClock(),
    )

    cash.initialize(
        "1000"
    )

    cash.settle_from_realized_journal(
        realized_journal=realized,
        booking_key=first.record[
            "booking_key"
        ],
    )

    with pytest.raises(
        CashLedgerError,
        match="CASH_LEDGER_EXIT_EXECUTION_CONFLICT",
    ):
        cash.settle_from_realized_journal(
            realized_journal=realized,
            booking_key=second.record[
                "booking_key"
            ],
        )


def test_open_semantics_do_not_mutate_cash_without_realized_booking(
    tmp_path,
):
    ledger = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl",
        clock=FixedClock(),
    )

    ledger.initialize(
        "1000"
    )

    before = ledger.path.read_bytes()

    assert (
        ledger.current_cash_pln()
        == Decimal("1000")
    )

    after = ledger.path.read_bytes()

    assert after == before
    assert len(
        ledger.read_records()
    ) == 1
