from datetime import datetime, timezone
from decimal import Decimal

import pytest

from scripts.run_phase11_cash_accounting_smoke import (
    CASH_LEDGER_FILENAME,
    _parser,
    _prepare_cash_ledger,
)
from src.accounting.cash_ledger import (
    CashLedgerError,
)


UTC = timezone.utc


class FixedClock:
    def now(self):
        return datetime(
            2026,
            9,
            18,
            16,
            0,
            tzinfo=UTC,
        )


def test_parser_requires_explicit_state_dir():
    parser = _parser()

    with pytest.raises(
        SystemExit,
    ):
        parser.parse_args(
            [
                "--realized-market-max-age-seconds",
                "7200",
                "--realized-daily-reference-max-age-days",
                "7",
                "--fx-prefetch-timeout-seconds",
                "4",
                "--fx-prefetch-max-workers",
                "3",
                "--cycle-timeout-seconds",
                "20",
            ]
        )


def test_parser_initial_cash_is_optional_for_restart():
    parser = _parser()

    args = parser.parse_args(
        [
            "--state-dir",
            "state",
            "--realized-market-max-age-seconds",
            "7200",
            "--realized-daily-reference-max-age-days",
            "7",
            "--fx-prefetch-timeout-seconds",
            "4",
            "--fx-prefetch-max-workers",
            "3",
            "--cycle-timeout-seconds",
            "20",
        ]
    )

    assert args.initial_cash_pln is None


def test_first_start_requires_initial_cash(
    tmp_path,
):
    with pytest.raises(
        CashLedgerError,
        match="INITIAL_CASH_PLN_REQUIRED",
    ):
        _prepare_cash_ledger(
            state_dir=tmp_path,
            initial_cash_pln=None,
            clock=FixedClock(),
        )

    assert not (
        tmp_path
        / CASH_LEDGER_FILENAME
    ).exists()


def test_first_start_initializes_authoritative_cash(
    tmp_path,
):
    ledger, records = (
        _prepare_cash_ledger(
            state_dir=tmp_path,
            initial_cash_pln="1000.00",
            clock=FixedClock(),
        )
    )

    assert len(records) == 1
    assert (
        ledger.current_cash_pln()
        == Decimal("1000.00")
    )


def test_restart_can_omit_initial_cash(
    tmp_path,
):
    first, _ = (
        _prepare_cash_ledger(
            state_dir=tmp_path,
            initial_cash_pln="1000",
            clock=FixedClock(),
        )
    )

    assert (
        first.current_cash_pln()
        == Decimal("1000")
    )

    second, records = (
        _prepare_cash_ledger(
            state_dir=tmp_path,
            initial_cash_pln=None,
            clock=FixedClock(),
        )
    )

    assert len(records) == 1
    assert (
        second.current_cash_pln()
        == Decimal("1000")
    )


def test_restart_rejects_conflicting_initial_cash(
    tmp_path,
):
    _prepare_cash_ledger(
        state_dir=tmp_path,
        initial_cash_pln="1000",
        clock=FixedClock(),
    )

    with pytest.raises(
        CashLedgerError,
        match="CASH_LEDGER_INITIAL_CASH_CONFLICT",
    ):
        _prepare_cash_ledger(
            state_dir=tmp_path,
            initial_cash_pln="999",
            clock=FixedClock(),
        )


@pytest.mark.parametrize(
    "evidence_name",
    [
        "state.json",
        "execution_journal.jsonl",
        "phase10_startup_metadata.jsonl",
        "phase10_realized_accounting.jsonl",
    ],
)
def test_existing_runtime_state_without_cash_ledger_fails_closed(
    tmp_path,
    evidence_name,
):
    (
        tmp_path
        / evidence_name
    ).write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        CashLedgerError,
        match="CASH_LEDGER_REQUIRED_FOR_EXISTING_STATE",
    ):
        _prepare_cash_ledger(
            state_dir=tmp_path,
            initial_cash_pln="1000",
            clock=FixedClock(),
        )

    assert not (
        tmp_path
        / CASH_LEDGER_FILENAME
    ).exists()
