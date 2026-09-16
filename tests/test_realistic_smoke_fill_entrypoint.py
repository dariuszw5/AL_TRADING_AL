import scripts.run_realistic_smoke_fill as entry


def test_smoke_requires_base_feature_flag(
    monkeypatch,
    capsys,
):
    monkeypatch.delenv(
        "AL_TRADING_REALISTIC_V2_ENABLED",
        raising=False,
    )

    monkeypatch.delenv(
        "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED",
        raising=False,
    )

    code = entry.main(
        [
            "--confirm-paper-smoke",
        ]
    )

    output = capsys.readouterr().out

    assert code == 2
    assert "REALISTIC_V2 IS DISABLED" in output


def test_smoke_requires_execution_feature_flag(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv(
        "AL_TRADING_REALISTIC_V2_ENABLED",
        "1",
    )

    monkeypatch.delenv(
        "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED",
        raising=False,
    )

    code = entry.main(
        [
            "--confirm-paper-smoke",
        ]
    )

    output = capsys.readouterr().out

    assert code == 3
    assert "EXECUTION FEATURE FLAG IS DISABLED" in output


def test_smoke_requires_explicit_confirmation(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv(
        "AL_TRADING_REALISTIC_V2_ENABLED",
        "1",
    )

    monkeypatch.setenv(
        "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED",
        "1",
    )

    code = entry.main([])

    output = capsys.readouterr().out

    assert code == 4
    assert "EXPLICIT CONFIRMATION REQUIRED" in output


def test_smoke_rejects_non_btc_asset(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv(
        "AL_TRADING_REALISTIC_V2_ENABLED",
        "1",
    )

    monkeypatch.setenv(
        "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED",
        "1",
    )

    code = entry.main(
        [
            "--asset",
            "ETHUSDT",
            "--confirm-paper-smoke",
        ]
    )

    output = capsys.readouterr().out

    assert code == 5
    assert "BTCUSDT ONLY" in output
