from datetime import timezone

import pytest

import scripts.run_realistic_paper as entry
from src.execution.feature_flags import RealisticV2FeatureFlags
from src.execution.models import PaperMode
from src.runtime_feature_flags import resolve_phase09_runtime_flags


class FakeResult:
    def __init__(self):
        self.status = type("Status", (), {"value": "READY"})()
        self.allowed = True
        self.rejection_reason = None
        self.error = None
        self.data_quality = "REALTIME"
        self.execution_quality = "REAL_BOOK"
        self.session_state = "OPEN"
        self.session_quality = "EXCHANGE_CALENDAR"
        self.provider_status = "CONNECTED"
        self.quote_age_seconds = 0.0
        self.labels = ()


class FakeCycle:
    def __init__(self):
        self.results = {"BTCUSDT": FakeResult()}
        self.duration_seconds = 0.1
        self.timed_out = False
        self.market_data_errors = {}


class FakePreflight:
    def __init__(self):
        self.calls = []

    def run(self, asset_ids):
        self.calls.append(tuple(asset_ids))
        return FakeCycle()


def test_runtime_flags_default_fail_closed():
    resolved = resolve_phase09_runtime_flags(env={})

    assert resolved.execution.enabled is False
    assert resolved.execution.execution_enabled is False
    assert resolved.execution.paper_mode is PaperMode.REALISTIC_PAPER
    assert resolved.fx.enabled is False
    assert resolved.pln_accounting.enabled is False


def test_runtime_flags_resolve_all_phase09_env_flags():
    resolved = resolve_phase09_runtime_flags(
        env={
            "AL_TRADING_REALISTIC_V2_ENABLED": "1",
            "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED": "1",
            "AL_TRADING_REALISTIC_V2_PAPER_MODE": "research_paper",
            "AL_TRADING_FX_ENABLED": "1",
            "AL_TRADING_PLN_ACCOUNTING_ENABLED": "1",
        }
    )

    assert resolved.execution.enabled is True
    assert resolved.execution.execution_enabled is True
    assert resolved.execution.paper_mode is PaperMode.RESEARCH_PAPER
    assert resolved.fx.enabled is True
    assert resolved.pln_accounting.enabled is True


def test_runtime_flags_reuse_pre_resolved_execution_flags():
    execution = RealisticV2FeatureFlags(
        enabled=True,
        execution_enabled=False,
        paper_mode=PaperMode.RESEARCH_PAPER,
    )

    resolved = resolve_phase09_runtime_flags(
        env={
            "AL_TRADING_FX_ENABLED": "1",
            "AL_TRADING_PLN_ACCOUNTING_ENABLED": "0",
        },
        execution_flags=execution,
    )

    assert resolved.execution is execution
    assert resolved.fx.enabled is True
    assert resolved.pln_accounting.enabled is False


def test_runtime_flags_fingerprint_snapshot_matches_a11_contract():
    resolved = resolve_phase09_runtime_flags(
        env={
            "AL_TRADING_REALISTIC_V2_ENABLED": "1",
            "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED": "1",
            "AL_TRADING_FX_ENABLED": "1",
            "AL_TRADING_PLN_ACCOUNTING_ENABLED": "0",
        }
    )

    assert dict(resolved.fingerprint_flags()) == {
        "AL_TRADING_REALISTIC_V2_ENABLED": True,
        "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED": True,
        "AL_TRADING_FX_ENABLED": True,
        "AL_TRADING_PLN_ACCOUNTING_ENABLED": False,
    }


@pytest.mark.parametrize(
    "name,value",
    [
        ("AL_TRADING_FX_ENABLED", "maybe"),
        ("AL_TRADING_PLN_ACCOUNTING_ENABLED", "maybe"),
    ],
)
def test_runtime_flags_invalid_phase09_boolean_fails_closed(name, value):
    with pytest.raises(ValueError, match=name):
        resolve_phase09_runtime_flags(env={name: value})


def test_realistic_preflight_reports_resolved_phase09_flags(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("AL_TRADING_REALISTIC_V2_ENABLED", "1")
    monkeypatch.setenv("AL_TRADING_FX_ENABLED", "1")
    monkeypatch.setenv("AL_TRADING_PLN_ACCOUNTING_ENABLED", "1")

    fake = FakePreflight()
    monkeypatch.setattr(
        entry,
        "build_live_preflight",
        lambda **kwargs: fake,
    )

    code = entry.main(["--asset", "BTCUSDT"])
    output = capsys.readouterr().out

    assert code == 0
    assert fake.calls == [("BTCUSDT",)]
    assert "FX enabled: True" in output
    assert "PLN accounting enabled: True" in output
    assert "Phase 09 feature flags:" in output


def test_realistic_preflight_keeps_execution_gate_semantics(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("AL_TRADING_REALISTIC_V2_ENABLED", "1")
    monkeypatch.delenv(
        "AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED",
        raising=False,
    )
    monkeypatch.delenv("AL_TRADING_FX_ENABLED", raising=False)
    monkeypatch.delenv(
        "AL_TRADING_PLN_ACCOUNTING_ENABLED",
        raising=False,
    )

    fake = FakePreflight()
    monkeypatch.setattr(
        entry,
        "build_live_preflight",
        lambda **kwargs: fake,
    )

    code = entry.main(["--asset", "BTCUSDT"])
    output = capsys.readouterr().out

    assert code == 0
    assert fake.calls == [("BTCUSDT",)]
    assert "FX enabled: False" in output
    assert "PLN accounting enabled: False" in output