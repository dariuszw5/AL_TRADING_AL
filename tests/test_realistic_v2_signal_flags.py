from datetime import datetime, timezone

import pytest

from src.agent.agent_config import AgentConfig
from src.core.clock import FixedClock
from src.data.market_data import (
    DataQuality,
    ExecutionQuality,
    MarketSnapshot,
    ProviderStatus,
)
from src.execution.feature_flags import (
    RealisticV2FeatureFlags,
)
from src.execution.models import (
    ExecutionProfile,
    Order,
    OrderIntent,
    OrderSide,
    OrderStatus,
    PaperMode,
)
from src.execution.paper_broker import PaperBroker
from src.execution.signal_adapter import (
    RealisticSignalAdapter,
)
from src.execution.slippage import FixedBpsSlippage
from src.market.market_session import (
    MarketSessionSnapshot,
    SessionQuality,
    SessionState,
)


NOW = datetime(
    2026,
    9,
    16,
    15,
    0,
    tzinfo=timezone.utc,
)


class FakeAnalysisEngine:

    def __init__(self, signal):
        self.signal = signal
        self.analyze_calls = []
        self.run_cycle_calls = []

    def analyze(self, candles):
        self.analyze_calls.append(
            tuple(candles)
        )

        return {
            "signal": self.signal,
            "sma": [100.0],
            "ema": [101.0],
            "rsi": [30.0],
        }

    def run_cycle(self, candles):
        self.run_cycle_calls.append(
            tuple(candles)
        )

        raise AssertionError(
            "signal adapter must never execute run_cycle"
        )


class FakeAsset:

    asset_id = "TEST"
    allow_long = True
    allow_short = False
    short_mechanism = "NONE"
    short_financing_model = None


def test_realistic_v2_feature_flag_defaults_off(
    monkeypatch,
):
    monkeypatch.delenv(
        "AL_TRADING_REALISTIC_V2_ENABLED",
        raising=False,
    )

    monkeypatch.delenv(
        "AL_TRADING_REALISTIC_V2_PAPER_MODE",
        raising=False,
    )

    flags = (
        RealisticV2FeatureFlags.from_env()
    )

    assert flags.enabled is False

    assert (
        flags.paper_mode
        is PaperMode.REALISTIC_PAPER
    )


@pytest.mark.parametrize(
    "value",
    [
        "1",
        "true",
        "TRUE",
        "yes",
        "on",
    ],
)
def test_realistic_v2_feature_flag_explicit_enable(
    monkeypatch,
    value,
):
    monkeypatch.setenv(
        "AL_TRADING_REALISTIC_V2_ENABLED",
        value,
    )

    flags = (
        RealisticV2FeatureFlags.from_env()
    )

    assert flags.enabled is True


def test_realistic_v2_feature_flag_research_mode(
    monkeypatch,
):
    monkeypatch.setenv(
        "AL_TRADING_REALISTIC_V2_PAPER_MODE",
        "research_paper",
    )

    flags = (
        RealisticV2FeatureFlags.from_env()
    )

    assert (
        flags.paper_mode
        is PaperMode.RESEARCH_PAPER
    )


def test_realistic_v2_feature_flag_invalid_boolean_fails_closed(
    monkeypatch,
):
    monkeypatch.setenv(
        "AL_TRADING_REALISTIC_V2_ENABLED",
        "maybe",
    )

    with pytest.raises(
        ValueError,
        match="AL_TRADING_REALISTIC_V2_ENABLED",
    ):
        RealisticV2FeatureFlags.from_env()


def test_realistic_v2_feature_flag_invalid_mode_fails_closed(
    monkeypatch,
):
    monkeypatch.setenv(
        "AL_TRADING_REALISTIC_V2_PAPER_MODE",
        "live_money",
    )

    with pytest.raises(
        ValueError,
        match="AL_TRADING_REALISTIC_V2_PAPER_MODE",
    ):
        RealisticV2FeatureFlags.from_env()


def test_signal_adapter_uses_analysis_only():
    engine = FakeAnalysisEngine(
        "BUY"
    )

    adapter = RealisticSignalAdapter(
        analysis_engine=engine
    )

    candles = [
        {"close": 100.0},
        {"close": 101.0},
    ]

    signal = adapter.signal_from_candles(
        candles
    )

    assert signal == "BUY"

    assert len(
        engine.analyze_calls
    ) == 1

    assert (
        engine.run_cycle_calls
        == []
    )


def test_signal_adapter_empty_history_is_hold():
    engine = FakeAnalysisEngine(
        "BUY"
    )

    adapter = RealisticSignalAdapter(
        analysis_engine=engine
    )

    assert (
        adapter.signal_from_candles([])
        == "HOLD"
    )

    assert engine.analyze_calls == []


@pytest.mark.parametrize(
    "signal",
    [
        "BUY",
        "SELL",
        "HOLD",
    ],
)
def test_signal_adapter_accepts_only_known_strategy_signals(
    signal,
):
    engine = FakeAnalysisEngine(
        signal
    )

    adapter = RealisticSignalAdapter(
        analysis_engine=engine
    )

    assert (
        adapter.signal_from_candles(
            [{"close": 100.0}]
        )
        == signal
    )


def test_signal_adapter_rejects_unknown_signal():
    engine = FakeAnalysisEngine(
        "MAGIC"
    )

    adapter = RealisticSignalAdapter(
        analysis_engine=engine
    )

    with pytest.raises(
        ValueError,
        match="Unsupported strategy signal",
    ):
        adapter.signal_from_candles(
            [{"close": 100.0}]
        )


def test_signal_adapter_default_engine_preserves_config():
    config = AgentConfig(
        buy_rsi=33.8,
        sell_rsi=68.5,
        min_difference=1.0,
        rsi_method="classic",
    )

    adapter = RealisticSignalAdapter(
        config=config
    )

    assert (
        adapter.analysis_engine.config
        is config
    )


def make_broker():
    return PaperBroker(
        clock=FixedClock(NOW),
        asset_resolver=(
            lambda asset_id: FakeAsset()
        ),
        slippage_model=(
            FixedBpsSlippage(5.0)
        ),
        trading_fee_rate=0.0004,
    )


def make_snapshot():
    return MarketSnapshot(
        asset_id="TEST",
        bid=100.0,
        ask=101.0,
        last=100.5,
        provider_timestamp=NOW,
        received_at=NOW,
        data_quality=(
            DataQuality.REALTIME
        ),
        delayed=False,
        quote_age_seconds=0.0,
        provider_status=(
            ProviderStatus.CONNECTED
        ),
        execution_quality=(
            ExecutionQuality.REAL_BOOK
        ),
    )


def make_session():
    return MarketSessionSnapshot(
        asset_id="TEST",
        session_id="TEST_SESSION",
        state=SessionState.OPEN,
        session_quality=(
            SessionQuality.EXCHANGE_CALENDAR
        ),
        observed_at=NOW,
        timezone_name="UTC",
        local_time=NOW,
        reason="TEST",
        calendar_version="test-v1",
    )


def make_order(
    *,
    client_id,
    paper_mode,
):
    return Order(
        order_id=(
            f"order-{client_id}"
        ),
        client_order_id=client_id,
        asset_id="TEST",
        side=OrderSide.BUY,
        quantity=1.0,
        intent=OrderIntent.ENTRY,
        created_at=NOW,
        execution_profile=(
            ExecutionProfile.REALISTIC_V2
        ),
        paper_mode=paper_mode,
        signal_reference="hash-test",
        stop_loss=95.0,
        take_profit=110.0,
    )


def test_config_hash_changes_with_paper_mode():
    broker = make_broker()

    realistic = broker.config_hash_for(
        PaperMode.REALISTIC_PAPER
    )

    research = broker.config_hash_for(
        PaperMode.RESEARCH_PAPER
    )

    assert realistic != research

    assert (
        broker.config_hash
        == realistic
    )


def test_execution_stores_exact_config_hash():
    broker = make_broker()

    order = make_order(
        client_id="hash-execution",
        paper_mode=(
            PaperMode.REALISTIC_PAPER
        ),
    )

    result = broker.submit_order(
        order,
        market_snapshot=make_snapshot(),
        market_session=make_session(),
    )

    assert (
        result.status
        is OrderStatus.FILLED
    )

    assert (
        result.execution.config_hash
        == broker.config_hash_for(
            order.paper_mode
        )
    )


def test_config_hash_is_deterministic():
    first = make_broker()
    second = make_broker()

    assert (
        first.config_hash_for(
            PaperMode.REALISTIC_PAPER
        )
        == second.config_hash_for(
            PaperMode.REALISTIC_PAPER
        )
    )
