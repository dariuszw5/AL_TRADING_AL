from types import SimpleNamespace

import scripts.run_phase10_accounting_smoke as entry


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


class FakeExecutionFlags:
    def __init__(
        self,
        *,
        enabled=True,
        execution_enabled=True,
    ):
        self.enabled = enabled
        self.execution_enabled = (
            execution_enabled
        )


class FakeFlags:
    def __init__(
        self,
        *,
        fx=True,
        pln=True,
    ):
        self.fx = SimpleNamespace(
            enabled=fx
        )
        self.pln_accounting = (
            SimpleNamespace(
                enabled=pln
            )
        )


class FakeBroker:
    pass


class FakeRuntime:
    def __init__(self):
        self.broker = FakeBroker()


class FakeStore:
    def load_positions(self):
        return {}


class FakeJournal:
    def expected_open_assets(self):
        return ()

    def unresolved_client_order_ids(self):
        return ()


class FakeFxResolver:
    def __init__(self):
        self.provider_errors = {}
        self.contract_errors = {}
        self.last_prefetch_duration_seconds = (
            0.01
        )
        self.last_prefetch_timed_out = False


class FakeWrappedRuntime:
    def __init__(
        self,
        *,
        calls,
    ):
        self.calls = calls

    def run_cycle(
        self,
        asset_ids,
    ):
        self.calls.append(
            tuple(
                asset_ids
            )
        )

        asset_result = SimpleNamespace(
            status=SimpleNamespace(
                value="OPENED"
            ),
            broker_result=None,
        )

        accounting = SimpleNamespace(
            error=None,
            limitations=(),
            mtm_record=object(),
            realized_result=None,
        )

        execution_cycle = (
            SimpleNamespace(
                results={
                    "BTCUSDT": (
                        asset_result
                    ),
                }
            )
        )

        return SimpleNamespace(
            execution_cycle=(
                execution_cycle
            ),
            accounting_results={
                "BTCUSDT": accounting,
            },
            limitations=(),
        )


def fake_metadata():
    return SimpleNamespace(
        schema="phase10-accounting-runtime-v1",
        execution_config_hash="a" * 64,
        base_global_config_hash="b" * 64,
        global_config_hash="c" * 64,
        asset_registry_hash="d" * 64,
        paper_mode="realistic_paper",
        feature_flags={
            "AL_TRADING_REALISTIC_V2_ENABLED": True,
            "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED": True,
            "AL_TRADING_FX_ENABLED": True,
            "AL_TRADING_PLN_ACCOUNTING_ENABLED": True,
        },
        runtime_policy={
            "fx_prefetch_timeout_seconds": 4.0,
        },
        limitations=(),
    )


def install_enabled(
    monkeypatch,
    *,
    fx=True,
    pln=True,
):
    monkeypatch.setattr(
        entry.RealisticV2FeatureFlags,
        "from_env",
        lambda: FakeExecutionFlags(),
    )

    monkeypatch.setattr(
        entry,
        "resolve_phase09_runtime_flags",
        lambda **kwargs: FakeFlags(
            fx=fx,
            pln=pln,
        ),
    )


def install_builder_and_wiring(
    monkeypatch,
    *,
    run_calls=None,
):
    if run_calls is None:
        run_calls = []

    built = []

    def builder(
        *,
        state_dir,
        quantity,
        close_existing,
    ):
        built.append(
            (
                state_dir,
                quantity,
                close_existing,
            )
        )

        return (
            FakeRuntime(),
            FakeStore(),
            FakeJournal(),
        )

    monkeypatch.setattr(
        entry,
        "build_runtime",
        builder,
    )

    wiring_calls = []

    def wire(
        *,
        runtime,
        broker,
        runtime_flags,
        policy,
    ):
        wiring_calls.append(
            (
                runtime,
                broker,
                runtime_flags,
                policy,
            )
        )

        return SimpleNamespace(
            startup_metadata=(
                fake_metadata()
            ),
            wiring=SimpleNamespace(
                runtime=(
                    FakeWrappedRuntime(
                        calls=run_calls
                    )
                ),
                fx_resolver=(
                    FakeFxResolver()
                ),
            ),
        )

    monkeypatch.setattr(
        entry,
        "wire_phase10_production_runtime",
        wire,
    )

    return (
        built,
        wiring_calls,
        run_calls,
    )


def test_flag_off_fails_before_runtime_builder(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        entry.RealisticV2FeatureFlags,
        "from_env",
        lambda: FakeExecutionFlags(
            enabled=False
        ),
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
        POLICY_ARGS
    )

    output = (
        capsys
        .readouterr()
        .out
    )

    assert code == 2
    assert (
        "REALISTIC_V2 IS DISABLED"
        in output
    )


def test_fx_flag_off_fails_before_runtime_builder(
    monkeypatch,
    capsys,
):
    install_enabled(
        monkeypatch,
        fx=False,
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
        POLICY_ARGS
    )

    output = (
        capsys
        .readouterr()
        .out
    )

    assert code == 7
    assert (
        "FX FEATURE FLAG IS DISABLED"
        in output
    )


def test_pln_flag_off_fails_before_runtime_builder(
    monkeypatch,
    capsys,
):
    install_enabled(
        monkeypatch,
        pln=False,
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
        POLICY_ARGS
    )

    output = (
        capsys
        .readouterr()
        .out
    )

    assert code == 8
    assert (
        "PLN ACCOUNTING FEATURE FLAG IS DISABLED"
        in output
    )


def test_verify_only_builds_accounting_runtime_but_runs_no_cycle(
    monkeypatch,
    capsys,
):
    install_enabled(
        monkeypatch
    )

    (
        built,
        wiring_calls,
        run_calls,
    ) = install_builder_and_wiring(
        monkeypatch
    )

    code = entry.main(
        POLICY_ARGS
    )

    output = (
        capsys
        .readouterr()
        .out
    )

    assert code == 0

    assert len(
        built
    ) == 1

    assert len(
        wiring_calls
    ) == 1

    assert run_calls == []

    assert (
        "PHASE 10 ACCOUNTING RUNTIME "
        "CONSTRUCTION VERIFIED"
        in output
    )

    assert (
        "PAPER EXECUTION CYCLE: NOT RUN"
        in output
    )

    assert (
        "STARTUP METADATA PERSISTED: NO"
        in output
    )


def test_run_cycle_requires_explicit_confirmation_before_builder(
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
        POLICY_ARGS
        + [
            "--run-cycle",
        ]
    )

    output = (
        capsys
        .readouterr()
        .out
    )

    assert code == 4

    assert (
        "EXPLICIT PAPER ACCOUNTING "
        "SMOKE CONFIRMATION REQUIRED"
        in output
    )


def test_confirmed_cycle_runs_wrapped_runtime_once(
    monkeypatch,
    capsys,
):
    install_enabled(
        monkeypatch
    )

    (
        built,
        wiring_calls,
        run_calls,
    ) = install_builder_and_wiring(
        monkeypatch
    )

    code = entry.main(
        POLICY_ARGS
        + [
            "--run-cycle",
            "--confirm-paper-accounting-smoke",
        ]
    )

    output = (
        capsys
        .readouterr()
        .out
    )

    assert code == 0

    assert run_calls == [
        (
            "BTCUSDT",
        )
    ]

    assert (
        "REAL EXCHANGE ORDERS SENT: 0"
        in output
    )

    assert (
        "Accounting error: None"
        in output
    )


def test_policy_above_half_cycle_budget_is_blocked_before_builder(
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

    args = list(
        POLICY_ARGS
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

    assert (
        "PHASE 10 POLICY BLOCKED"
        in output
    )


def test_non_btc_asset_is_rejected_before_builder(
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
        POLICY_ARGS
        + [
            "--asset",
            "AAPL",
        ]
    )

    output = (
        capsys
        .readouterr()
        .out
    )

    assert code == 5
    assert (
        "BTCUSDT ONLY"
        in output
    )
