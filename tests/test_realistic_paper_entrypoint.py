import scripts.run_realistic_paper as entry


class FakeResult:

    def __init__(
        self,
        *,
        status="READY",
        allowed=True,
        reason=None,
    ):
        self.status = type(
            "Status",
            (),
            {"value": status},
        )()

        self.allowed = allowed
        self.rejection_reason = reason
        self.error = None
        self.data_quality = "REALTIME"
        self.execution_quality = "REAL_BOOK"
        self.session_state = "OPEN"
        self.session_quality = (
            "EXCHANGE_CALENDAR"
        )
        self.provider_status = "CONNECTED"
        self.quote_age_seconds = 0.0
        self.labels = ()


class FakeCycle:

    def __init__(self):
        self.results = {
            "BTCUSDT": FakeResult(),
        }

        self.duration_seconds = 0.1
        self.timed_out = False
        self.market_data_errors = {}


class FakePreflight:

    def __init__(self):
        self.calls = []

    def run(self, asset_ids):
        self.calls.append(
            tuple(asset_ids)
        )
        return FakeCycle()


def test_entrypoint_flag_off_fails_before_builder(
    monkeypatch,
    capsys,
):
    monkeypatch.delenv(
        "AL_TRADING_REALISTIC_V2_ENABLED",
        raising=False,
    )

    def forbidden_builder(**kwargs):
        raise AssertionError(
            "builder must not run when flag is OFF"
        )

    monkeypatch.setattr(
        entry,
        "build_live_preflight",
        forbidden_builder,
    )

    code = entry.main(
        [
            "--asset",
            "BTCUSDT",
        ]
    )

    output = capsys.readouterr().out

    assert code == 2

    assert (
        "REALISTIC_V2 IS DISABLED"
        in output
    )


def test_entrypoint_execute_is_explicitly_blocked(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv(
        "AL_TRADING_REALISTIC_V2_ENABLED",
        "1",
    )

    def forbidden_builder(**kwargs):
        raise AssertionError(
            "builder must not run for blocked --execute"
        )

    monkeypatch.setattr(
        entry,
        "build_live_preflight",
        forbidden_builder,
    )

    code = entry.main(
        [
            "--asset",
            "BTCUSDT",
            "--execute",
        ]
    )

    output = capsys.readouterr().out

    assert code == 3

    assert (
        "PAPER EXECUTION BLOCKED"
        in output
    )


def test_entrypoint_enabled_runs_live_preflight(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv(
        "AL_TRADING_REALISTIC_V2_ENABLED",
        "1",
    )

    fake = FakePreflight()

    monkeypatch.setattr(
        entry,
        "build_live_preflight",
        lambda **kwargs: fake,
    )

    code = entry.main(
        [
            "--asset",
            "BTCUSDT",
        ]
    )

    output = capsys.readouterr().out

    assert code == 0
    assert fake.calls == [
        ("BTCUSDT",)
    ]

    assert (
        "PRE-FLIGHT ONLY"
        in output
    )

    assert (
        "BTCUSDT"
        in output
    )


def test_entrypoint_rejects_unknown_asset(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv(
        "AL_TRADING_REALISTIC_V2_ENABLED",
        "1",
    )

    code = entry.main(
        [
            "--asset",
            "NOT_REAL",
        ]
    )

    output = capsys.readouterr().out

    assert code == 4

    assert (
        "UNKNOWN ASSET"
        in output
    )
