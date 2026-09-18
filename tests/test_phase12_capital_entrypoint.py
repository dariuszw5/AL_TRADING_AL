from pathlib import Path

import pytest

from scripts.run_phase12_capital_accounting_smoke import (
    PHASE12_STARTUP_METADATA_FILENAME,
    main,
)
from src.accounting.cash_ledger import (
    Phase11CashLedger,
)
from src.accounting.startup_metadata_store import (
    StartupMetadataJournal,
)
from src.execution.capital_startup_store import (
    Phase12StartupMetadataJournal,
)


POLICY_ARGS = [
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


def _enable_required_flags(
    monkeypatch,
):
    monkeypatch.setenv(
        "AL_TRADING_REALISTIC_V2_ENABLED",
        "1",
    )
    monkeypatch.setenv(
        "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED",
        "1",
    )
    monkeypatch.setenv(
        "AL_TRADING_FX_ENABLED",
        "1",
    )
    monkeypatch.setenv(
        "AL_TRADING_PLN_ACCOUNTING_ENABLED",
        "1",
    )
    monkeypatch.setenv(
        "AL_TRADING_CAPITAL_ADMISSION_ENABLED",
        "1",
    )


def test_construction_only_persists_both_startup_layers_and_cash(
    tmp_path,
    monkeypatch,
    capsys,
):
    _enable_required_flags(
        monkeypatch
    )

    result = main(
        [
            "--state-dir",
            str(
                tmp_path
            ),
            "--initial-cash-pln",
            "1000",
            *POLICY_ARGS,
        ]
    )

    assert result == 0

    output = (
        capsys
        .readouterr()
        .out
    )

    assert (
        "PAPER EXECUTION CYCLE: NOT RUN"
        in output
    )
    assert (
        "NETWORK ACCOUNTING PREFETCH: NOT RUN"
        in output
    )
    assert (
        "REAL EXCHANGE ORDERS SENT: 0"
        in output
    )
    assert (
        "PHASE 12 STARTUP METADATA PERSISTED: YES"
        in output
    )

    cash = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl"
    )

    assert (
        str(
            cash.current_cash_pln()
        )
        == "1000"
    )

    phase10 = StartupMetadataJournal(
        tmp_path
        / "phase10_startup_metadata.jsonl"
    )

    phase12 = Phase12StartupMetadataJournal(
        tmp_path
        / PHASE12_STARTUP_METADATA_FILENAME
    )

    assert len(
        phase10.read_records()
    ) == 1

    phase12_records = (
        phase12.read_records()
    )

    assert len(
        phase12_records
    ) == 1

    assert (
        phase12_records[0][
            "phase12_feature_flags"
        ][
            "AL_TRADING_CAPITAL_ADMISSION_ENABLED"
        ]
        is True
    )

    assert not (
        tmp_path
        / "state.json"
    ).exists()

    assert not (
        tmp_path
        / "execution_journal.jsonl"
    ).exists()

    assert not (
        tmp_path
        / "phase10_realized_accounting.jsonl"
    ).exists()


def test_run_cycle_requires_explicit_phase12_confirmation(
    tmp_path,
    monkeypatch,
):
    _enable_required_flags(
        monkeypatch
    )

    result = main(
        [
            "--state-dir",
            str(
                tmp_path
            ),
            "--initial-cash-pln",
            "1000",
            "--run-cycle",
            *POLICY_ARGS,
        ]
    )

    assert result == 4

    assert not any(
        tmp_path.iterdir()
    )


def test_disabled_capital_flag_fails_closed_before_state(
    tmp_path,
    monkeypatch,
):
    _enable_required_flags(
        monkeypatch
    )

    monkeypatch.setenv(
        "AL_TRADING_CAPITAL_ADMISSION_ENABLED",
        "0",
    )

    result = main(
        [
            "--state-dir",
            str(
                tmp_path
            ),
            "--initial-cash-pln",
            "1000",
            *POLICY_ARGS,
        ]
    )

    assert result == 12
    assert not any(
        tmp_path.iterdir()
    )


def test_first_start_requires_explicit_initial_cash(
    tmp_path,
    monkeypatch,
):
    _enable_required_flags(
        monkeypatch
    )

    result = main(
        [
            "--state-dir",
            str(
                tmp_path
            ),
            *POLICY_ARGS,
        ]
    )

    assert result == 20

    assert not (
        tmp_path
        / "phase12_startup_metadata.jsonl"
    ).exists()


def test_restart_can_omit_initial_cash_and_appends_both_metadata_layers(
    tmp_path,
    monkeypatch,
):
    _enable_required_flags(
        monkeypatch
    )

    first = main(
        [
            "--state-dir",
            str(
                tmp_path
            ),
            "--initial-cash-pln",
            "1000",
            *POLICY_ARGS,
        ]
    )

    second = main(
        [
            "--state-dir",
            str(
                tmp_path
            ),
            *POLICY_ARGS,
        ]
    )

    assert first == 0
    assert second == 0

    phase10 = StartupMetadataJournal(
        tmp_path
        / "phase10_startup_metadata.jsonl"
    )

    phase12 = Phase12StartupMetadataJournal(
        tmp_path
        / "phase12_startup_metadata.jsonl"
    )

    assert len(
        phase10.read_records()
    ) == 2
    assert len(
        phase12.read_records()
    ) == 2


def test_conflicting_restart_initial_cash_fails_closed(
    tmp_path,
    monkeypatch,
):
    _enable_required_flags(
        monkeypatch
    )

    first = main(
        [
            "--state-dir",
            str(
                tmp_path
            ),
            "--initial-cash-pln",
            "1000",
            *POLICY_ARGS,
        ]
    )

    assert first == 0

    second = main(
        [
            "--state-dir",
            str(
                tmp_path
            ),
            "--initial-cash-pln",
            "2000",
            *POLICY_ARGS,
        ]
    )

    assert second == 20

    cash = Phase11CashLedger(
        tmp_path
        / "phase11_cash_ledger.jsonl"
    )

    assert str(
        cash.current_cash_pln()
    ) == "1000"


def test_only_btcusdt_is_allowed(
    tmp_path,
    monkeypatch,
):
    _enable_required_flags(
        monkeypatch
    )

    result = main(
        [
            "--asset",
            "ETHUSDT",
            "--state-dir",
            str(
                tmp_path
            ),
            "--initial-cash-pln",
            "1000",
            *POLICY_ARGS,
        ]
    )

    assert result == 5
    assert not any(
        tmp_path.iterdir()
    )
