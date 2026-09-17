from datetime import (
    datetime,
    timezone,
)
from types import SimpleNamespace

import pytest

import scripts.run_phase10_persisted_accounting_smoke as entry
from src.accounting.startup_metadata_store import (
    StartupMetadataJournal,
)


UTC = timezone.utc
NOW = datetime(
    2026,
    9,
    17,
    18,
    45,
    tzinfo=UTC,
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


class FixedClock:
    def now(self):
        return NOW


class FakeExecutionFlags:
    enabled = True
    execution_enabled = True


class FakeFlags:
    fx = SimpleNamespace(
        enabled=True
    )
    pln_accounting = SimpleNamespace(
        enabled=True
    )


class FakeBroker:
    pass


class FakeRuntime:
    def __init__(
        self,
    ):
        self.broker = FakeBroker()
        self.clock = FixedClock()


class FakeStore:
    def load_positions(self):
        return {}


class FakeJournal:
    def expected_open_assets(self):
        return ()

    def unresolved_client_order_ids(self):
        return ()


class FakeCycleRuntime:
    def __init__(
        self,
        *,
        metadata_path,
        calls,
    ):
        self.metadata_path = (
            metadata_path
        )
        self.calls = calls

    def run_cycle(
        self,
        asset_ids,
    ):
        records = (
            StartupMetadataJournal(
                self.metadata_path
            )
            .read_records()
        )

        assert len(
            records
        ) >= 1

        self.calls.append(
            (
                "cycle",
                tuple(
                    asset_ids
                ),
                records[-1][
                    "global_config_hash"
                ],
            )
        )

        asset_result = SimpleNamespace(
            status=SimpleNamespace(
                value="FILLED"
            ),
            broker_result=None,
        )

        accounting = SimpleNamespace(
            error=None,
            limitations=(),
            mtm_record=object(),
            realized_result=None,
        )

        return SimpleNamespace(
            execution_cycle=(
                SimpleNamespace(
                    results={
                        "BTCUSDT": (
                            asset_result
                        ),
                    }
                )
            ),
            accounting_results={
                "BTCUSDT": accounting,
            },
            limitations=(),
        )


def metadata(
    global_hash="c" * 64,
):
    return SimpleNamespace(
        schema="phase10-accounting-runtime-v1",
        execution_config_hash="a" * 64,
        base_global_config_hash="b" * 64,
        global_config_hash=global_hash,
        asset_registry_hash="d" * 64,
        paper_mode="realistic_paper",
        feature_flags={
            "AL_TRADING_REALISTIC_V2_ENABLED": True,
            "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED": True,
            "AL_TRADING_FX_ENABLED": True,
            "AL_TRADING_PLN_ACCOUNTING_ENABLED": True,
        },
        runtime_policy={
            "schema": "phase10-accounting-runtime-v1",
            "realized_market_max_age_seconds": 7200.0,
            "realized_daily_reference_max_age_days": 7,
            "fx_prefetch_timeout_seconds": 4.0,
            "fx_prefetch_max_workers": 3,
            "cycle_timeout_seconds": 20.0,
        },
        limitations=(),
    )


def install_enabled(
    monkeypatch,
):
    monkeypatch.setattr(
        entry.RealisticV2FeatureFlags,
        "from_env",
        lambda: FakeExecutionFlags(),
    )

    monkeypatch.setattr(
        entry,
        "resolve_phase09_runtime_flags",
        lambda **kwargs: FakeFlags(),
    )


def install_runtime(
    monkeypatch,
    *,
    state_dir,
    calls,
    metadata_value=None,
):
    if metadata_value is None:
        metadata_value = metadata()

    runtime = FakeRuntime()
    store = FakeStore()
    journal = FakeJournal()

    def builder(
        *,
        state_dir,
        quantity,
        close_existing,
    ):
        calls.append(
            (
                "build",
                str(
                    state_dir
                ),
                quantity,
                close_existing,
            )
        )

        return (
            runtime,
            store,
            journal,
        )

    monkeypatch.setattr(
        entry,
        "build_runtime",
        builder,
    )

    wrapped = (
        FakeCycleRuntime(
            metadata_path=(
                state_dir
                / entry
                .STARTUP_METADATA_FILENAME
            ),
            calls=calls,
        )
    )

    monkeypatch.setattr(
        entry,
        "wire_phase10_production_runtime",
        lambda **kwargs: (
            SimpleNamespace(
                startup_metadata=(
                    metadata_value
                ),
                wiring=SimpleNamespace(
                    runtime=wrapped
                ),
            )
        ),
    )

    return (
        runtime,
        store,
        journal,
        wrapped,
    )


def args_for(
    state_dir,
    *extra,
):
    return (
        [
            "--state-dir",
            str(
                state_dir
            ),
        ]
        + POLICY_ARGS
        + list(
            extra
        )
    )


def test_verify_only_persists_one_verified_record_without_cycle(
    tmp_path,
    monkeypatch,
    capsys,
):
    install_enabled(
        monkeypatch
    )

    calls = []

    install_runtime(
        monkeypatch,
        state_dir=tmp_path,
        calls=calls,
    )

    code = entry.main(
        args_for(
            tmp_path
        )
    )

    output = (
        capsys
        .readouterr()
        .out
    )

    assert code == 0

    path = (
        tmp_path
        / entry
        .STARTUP_METADATA_FILENAME
    )

    records = (
        StartupMetadataJournal(
            path
        )
        .read_records()
    )

    assert len(
        records
    ) == 1

    assert (
        records[0][
            "global_config_hash"
        ]
        == "c" * 64
    )

    assert not any(
        item[0] == "cycle"
        for item in calls
    )

    assert (
        "STARTUP METADATA PERSISTED: YES"
        in output
    )

    assert (
        "STARTUP METADATA INTEGRITY: VERIFIED"
        in output
    )

    assert (
        "PAPER EXECUTION CYCLE: NOT RUN"
        in output
    )


def test_cycle_observes_verified_metadata_before_execution(
    tmp_path,
    monkeypatch,
    capsys,
):
    install_enabled(
        monkeypatch
    )

    calls = []

    install_runtime(
        monkeypatch,
        state_dir=tmp_path,
        calls=calls,
    )

    code = entry.main(
        args_for(
            tmp_path,
            "--run-cycle",
            "--confirm-paper-accounting-smoke",
        )
    )

    output = (
        capsys
        .readouterr()
        .out
    )

    assert code == 0

    cycle_calls = [
        item
        for item in calls
        if item[0] == "cycle"
    ]

    assert cycle_calls == [
        (
            "cycle",
            (
                "BTCUSDT",
            ),
            "c" * 64,
        )
    ]

    assert (
        "STARTUP METADATA VERIFIED BEFORE PAPER CYCLE"
        in output
    )


def test_corrupt_existing_metadata_blocks_cycle_before_execution(
    tmp_path,
    monkeypatch,
    capsys,
):
    install_enabled(
        monkeypatch
    )

    calls = []

    install_runtime(
        monkeypatch,
        state_dir=tmp_path,
        calls=calls,
    )

    path = (
        tmp_path
        / entry
        .STARTUP_METADATA_FILENAME
    )

    path.write_text(
        '{"broken":\n',
        encoding="utf-8",
    )

    code = entry.main(
        args_for(
            tmp_path,
            "--run-cycle",
            "--confirm-paper-accounting-smoke",
        )
    )

    output = (
        capsys
        .readouterr()
        .out
    )

    assert code == 22

    assert not any(
        item[0] == "cycle"
        for item in calls
    )

    assert (
        "STARTUP METADATA PERSISTENCE FAILED"
        in output
    )

    assert (
        "PAPER EXECUTION CYCLE: NOT RUN"
        in output
    )


def test_confirmation_is_required_before_runtime_construction(
    tmp_path,
    monkeypatch,
    capsys,
):
    install_enabled(
        monkeypatch
    )

    monkeypatch.setattr(
        entry,
        "build_runtime",
        lambda **kwargs: (
            (_ for _ in ())
            .throw(
                AssertionError(
                    "builder must not run"
                )
            )
        ),
    )

    code = entry.main(
        args_for(
            tmp_path,
            "--run-cycle",
        )
    )

    output = (
        capsys
        .readouterr()
        .out
    )

    assert code == 4

    assert (
        "EXPLICIT PAPER ACCOUNTING SMOKE CONFIRMATION REQUIRED"
        in output
    )

    assert not (
        tmp_path
        / entry
        .STARTUP_METADATA_FILENAME
    ).exists()


def test_second_start_appends_and_preserves_first_record(
    tmp_path,
    monkeypatch,
):
    install_enabled(
        monkeypatch
    )

    calls = []

    install_runtime(
        monkeypatch,
        state_dir=tmp_path,
        calls=calls,
        metadata_value=metadata(
            "c" * 64
        ),
    )

    assert entry.main(
        args_for(
            tmp_path
        )
    ) == 0

    first_bytes = (
        tmp_path
        / entry
        .STARTUP_METADATA_FILENAME
    ).read_bytes()

    install_runtime(
        monkeypatch,
        state_dir=tmp_path,
        calls=calls,
        metadata_value=metadata(
            "e" * 64
        ),
    )

    assert entry.main(
        args_for(
            tmp_path
        )
    ) == 0

    path = (
        tmp_path
        / entry
        .STARTUP_METADATA_FILENAME
    )

    all_bytes = (
        path.read_bytes()
    )

    assert all_bytes.startswith(
        first_bytes
    )

    records = (
        StartupMetadataJournal(
            path
        )
        .read_records()
    )

    assert [
        item[
            "global_config_hash"
        ]
        for item in records
    ] == [
        "c" * 64,
        "e" * 64,
    ]


def test_metadata_path_is_scoped_inside_explicit_state_dir(
    tmp_path,
):
    path = entry._metadata_path(
        tmp_path
    )

    assert path == (
        tmp_path
        / "phase10_startup_metadata.jsonl"
    )

    assert path.parent == tmp_path


def test_policy_above_half_budget_blocks_before_metadata_write(
    tmp_path,
    monkeypatch,
    capsys,
):
    install_enabled(
        monkeypatch
    )

    args = args_for(
        tmp_path
    )

    index = args.index(
        "--fx-prefetch-timeout-seconds"
    )

    args[
        index + 1
    ] = "11"

    code = entry.main(
        args
    )

    output = (
        capsys
        .readouterr()
        .out
    )

    assert code == 10

    assert not (
        tmp_path
        / entry
        .STARTUP_METADATA_FILENAME
    ).exists()

    assert (
        "PHASE 10 POLICY BLOCKED"
        in output
    )


def test_state_dir_is_required():
    with pytest.raises(
        SystemExit,
    ):
        entry.main(
            POLICY_ARGS
        )
