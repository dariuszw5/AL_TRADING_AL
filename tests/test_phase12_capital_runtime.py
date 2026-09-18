from datetime import datetime, timezone
from types import MappingProxyType, SimpleNamespace

import pytest

from src.core.clock import FixedClock
from src.data.market_data import (
    DataQuality,
    ExecutionQuality,
    MarketSnapshot,
    ProviderStatus,
)
from src.execution.capital_admission import CashBackedCapitalAdmissionPolicy
from src.execution.capital_exposure import BtcUsdtLongExposureCalculator
from src.execution.capital_feature_flags import CapitalAdmissionFeatureFlags
from src.execution.capital_runtime import (
    Phase12CapitalAdmissionProvider,
    wire_phase12_capital_runtime,
)
from src.execution.capital_startup import (
    PHASE12_CAPITAL_ADMISSION_FLAG_NOT_ENABLED,
    Phase12CapitalAdmissionPolicy,
    Phase12StartupPolicyError,
)
from src.execution.models import (
    BrokerResult,
    Execution,
    ExecutionProfile,
    OrderIntent,
    OrderSide,
    OrderStatus,
    PaperMode,
    Position,
    PositionSide,
    PositionStatus,
)
from src.execution.runtime import (
    ExecutionDecision,
    RealisticPaperRuntime,
    RuntimeAssetStatus,
)
from src.execution.slippage import FixedBpsSlippage
from src.fx.converter import CurrencyConverter
from src.fx.freshness import FxFreshnessPolicy
from src.fx.models import FxQuote, FxSourceQuality
from src.market.market_session import (
    MarketSessionSnapshot,
    SessionQuality,
    SessionState,
)

NOW = datetime(2026, 9, 18, 14, 0, tzinfo=timezone.utc)


class MarketDataService:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def run_cycle(self, asset_ids):
        return SimpleNamespace(
            snapshots={asset_id: self.snapshot for asset_id in asset_ids},
            errors={},
            duration_seconds=0.01,
            timed_out=False,
        )


class SessionService:
    def get_session(self, asset_id, *, at):
        return MarketSessionSnapshot(
            asset_id=asset_id,
            session_id="CRYPTO_24_7",
            state=SessionState.OPEN,
            session_quality=SessionQuality.EXCHANGE_CALENDAR,
            observed_at=at,
            timezone_name="UTC",
            local_time=at,
            reason="TEST",
            calendar_version="TEST",
        )


class CountingBroker:
    execution_journal = None

    def __init__(self):
        self.calls = 0

    def submit_order(self, order, *, market_snapshot, market_session, position):
        self.calls += 1
        price = market_snapshot.ask if order.side is OrderSide.BUY else market_snapshot.bid
        execution = Execution(
            execution_id="exec-" + order.order_id,
            order_id=order.order_id,
            asset_id=order.asset_id,
            side=order.side,
            quantity=order.quantity,
            reference_price=price,
            execution_price=price,
            bid=market_snapshot.bid,
            ask=market_snapshot.ask,
            spread=market_snapshot.ask - market_snapshot.bid,
            slippage=0.0,
            fee=0.0,
            provider_timestamp=market_snapshot.provider_timestamp,
            execution_timestamp=NOW,
            data_quality=market_snapshot.data_quality,
            execution_quality=market_snapshot.execution_quality,
            session_quality=market_session.session_quality,
            paper_mode=order.paper_mode,
            short_label=None,
            trigger_reason=order.requested_exit_reason,
            pending_reason=None,
            execution_reason=(order.requested_exit_reason or "ENTRY"),
        )

        if order.intent is OrderIntent.ENTRY:
            new_position = Position(
                position_id="pos-" + order.order_id,
                asset_id=order.asset_id,
                side=PositionSide.LONG,
                quantity=order.quantity,
                entry_execution_id=execution.execution_id,
                entry_price=execution.execution_price,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                opened_at=NOW,
                short_mechanism=None,
                short_financing_model=None,
                execution_profile=ExecutionProfile.REALISTIC_V2,
                execution_quality_at_entry=market_snapshot.execution_quality,
                status=PositionStatus.OPEN,
            )
        else:
            new_position = Position(
                position_id=position.position_id,
                asset_id=position.asset_id,
                side=position.side,
                quantity=position.quantity,
                entry_execution_id=position.entry_execution_id,
                entry_price=position.entry_price,
                stop_loss=position.stop_loss,
                take_profit=position.take_profit,
                opened_at=position.opened_at,
                short_mechanism=position.short_mechanism,
                short_financing_model=position.short_financing_model,
                execution_profile=position.execution_profile,
                execution_quality_at_entry=position.execution_quality_at_entry,
                status=PositionStatus.CLOSED,
                closed_at=NOW,
                exit_execution_id=execution.execution_id,
                exit_price=execution.execution_price,
            )

        return BrokerResult(
            status=OrderStatus.FILLED,
            order=order,
            execution=execution,
            position=new_position,
        )


def snapshot():
    return MarketSnapshot(
        asset_id="BTCUSDT",
        bid=99.0,
        ask=100.0,
        last=99.5,
        provider_timestamp=NOW,
        received_at=NOW,
        data_quality=DataQuality.REALTIME,
        delayed=False,
        quote_age_seconds=0.0,
        provider_status=ProviderStatus.CONNECTED,
        execution_quality=ExecutionQuality.REAL_BOOK,
    )


def quote(base, target, rate):
    return FxQuote(
        base_currency=base,
        quote_currency=target,
        rate=rate,
        provider="TEST",
        provider_timestamp=NOW,
        observed_at=NOW,
        source_quality=FxSourceQuality.LIVE,
    )


def exposure_calculator():
    return BtcUsdtLongExposureCalculator(
        slippage_model=FixedBpsSlippage(0.0),
        fx_converter=CurrencyConverter(
            freshness_policy=FxFreshnessPolicy(
                weekday_max_age_seconds=900,
                weekend_max_age_seconds=900,
            ),
            clock=FixedClock(NOW),
        ),
    )


def gate_provider(*, cash):
    return Phase12CapitalAdmissionProvider(
        cash_pln_resolver=lambda: cash,
        fx_quotes_resolver=lambda: (
            quote("USDT", "USD", 1.0),
            quote("USD", "PLN", 4.0),
        ),
        exposure_calculator=exposure_calculator(),
        admission_policy=CashBackedCapitalAdmissionPolicy(),
        max_exposure_percent=100,
    )


def entry_decision(quantity):
    return ExecutionDecision(
        side=OrderSide.BUY,
        intent=OrderIntent.ENTRY,
        quantity=quantity,
        stop_loss=95.0,
        take_profit=110.0,
        signal_reference="TEST_ENTRY",
    )


def make_runtime(*, broker, decision, admission_provider=None):
    return RealisticPaperRuntime(
        market_data_service=MarketDataService(snapshot()),
        market_session_service=SessionService(),
        broker=broker,
        decision_provider=lambda **kwargs: decision,
        admission_provider=admission_provider,
        clock=FixedClock(NOW),
        paper_mode=PaperMode.REALISTIC_PAPER,
    )


def test_runtime_default_none_preserves_existing_execution_path():
    broker = CountingBroker()
    system = make_runtime(broker=broker, decision=entry_decision(1.0))
    asset = system.run_cycle(["BTCUSDT"]).results["BTCUSDT"]
    assert asset.status is RuntimeAssetStatus.FILLED
    assert broker.calls == 1
    assert asset.capital_admission is None


def test_oversized_long_is_blocked_before_broker():
    broker = CountingBroker()
    system = make_runtime(
        broker=broker,
        decision=entry_decision(3.0),
        admission_provider=gate_provider(cash="1000"),
    )
    asset = system.run_cycle(["BTCUSDT"]).results["BTCUSDT"]
    assert asset.status is RuntimeAssetStatus.CAPITAL_REJECTED
    assert broker.calls == 0
    assert asset.capital_admission.allowed is False
    assert asset.capital_admission.reason == "CAPITAL_LIMIT_EXCEEDED"
    assert asset.broker_result is None


def test_long_within_limit_reaches_broker():
    broker = CountingBroker()
    system = make_runtime(
        broker=broker,
        decision=entry_decision(2.0),
        admission_provider=gate_provider(cash="1000"),
    )
    asset = system.run_cycle(["BTCUSDT"]).results["BTCUSDT"]
    assert asset.status is RuntimeAssetStatus.FILLED
    assert broker.calls == 1
    assert asset.capital_admission.allowed is True


def test_zero_cash_blocks_new_long_before_broker():
    broker = CountingBroker()
    system = make_runtime(
        broker=broker,
        decision=entry_decision(0.1),
        admission_provider=gate_provider(cash="0"),
    )
    asset = system.run_cycle(["BTCUSDT"]).results["BTCUSDT"]
    assert asset.status is RuntimeAssetStatus.CAPITAL_REJECTED
    assert broker.calls == 0
    assert asset.capital_admission.reason == "SETTLED_CASH_NONPOSITIVE"


def test_exit_bypasses_capital_admission_provider():
    class MustNotRun:
        def __call__(self, **kwargs):
            raise AssertionError("capital admission must not run for EXIT")

    broker = CountingBroker()
    decision = ExecutionDecision(
        side=OrderSide.SELL,
        intent=OrderIntent.EXIT,
        quantity=1.0,
        exit_reason="TEST_EXIT",
    )
    system = make_runtime(
        broker=broker,
        decision=decision,
        admission_provider=MustNotRun(),
    )
    system.positions["BTCUSDT"] = Position(
        position_id="pos-existing",
        asset_id="BTCUSDT",
        side=PositionSide.LONG,
        quantity=1.0,
        entry_execution_id="exec-entry",
        entry_price=90.0,
        stop_loss=85.0,
        take_profit=100.0,
        opened_at=NOW,
        short_mechanism=None,
        short_financing_model=None,
        execution_profile=ExecutionProfile.REALISTIC_V2,
        execution_quality_at_entry=ExecutionQuality.REAL_BOOK,
        status=PositionStatus.OPEN,
    )
    asset = system.run_cycle(["BTCUSDT"]).results["BTCUSDT"]
    assert asset.status is RuntimeAssetStatus.FILLED
    assert broker.calls == 1
    assert asset.capital_admission is None


def test_admission_provider_exception_fails_closed_before_broker():
    class BrokenProvider:
        def __call__(self, **kwargs):
            raise RuntimeError("boom")

    broker = CountingBroker()
    system = make_runtime(
        broker=broker,
        decision=entry_decision(1.0),
        admission_provider=BrokenProvider(),
    )
    asset = system.run_cycle(["BTCUSDT"]).results["BTCUSDT"]
    assert asset.status is RuntimeAssetStatus.CAPITAL_REJECTED
    assert broker.calls == 0
    assert "CAPITAL_ADMISSION_PROVIDER_ERROR" in asset.error


def test_invalid_admission_provider_result_fails_closed():
    class InvalidProvider:
        def __call__(self, **kwargs):
            return object()

    broker = CountingBroker()
    system = make_runtime(
        broker=broker,
        decision=entry_decision(1.0),
        admission_provider=InvalidProvider(),
    )
    asset = system.run_cycle(["BTCUSDT"]).results["BTCUSDT"]
    assert asset.status is RuntimeAssetStatus.CAPITAL_REJECTED
    assert broker.calls == 0
    assert "CAPITAL_ADMISSION_INVALID_RESULT" in asset.error


def test_provider_fails_closed_when_fx_quotes_missing():
    provider = Phase12CapitalAdmissionProvider(
        cash_pln_resolver=lambda: "1000",
        fx_quotes_resolver=lambda: (),
        exposure_calculator=exposure_calculator(),
        admission_policy=CashBackedCapitalAdmissionPolicy(),
        max_exposure_percent=100,
    )
    result = provider(
        asset_id="BTCUSDT",
        snapshot=snapshot(),
        position=None,
        decision=entry_decision(1.0),
    )
    assert result.allowed is False
    assert result.reason == "FX_UNAVAILABLE"


def test_wire_phase12_requires_enabled_flag_before_phase11_wiring(monkeypatch):
    called = []

    def fake_wire(**kwargs):
        called.append(kwargs)
        raise AssertionError("Phase 11 wiring must not run")

    monkeypatch.setattr(
        "src.execution.capital_runtime.wire_phase11_cash_runtime",
        fake_wire,
    )

    with pytest.raises(
        Phase12StartupPolicyError,
        match=PHASE12_CAPITAL_ADMISSION_FLAG_NOT_ENABLED,
    ):
        wire_phase12_capital_runtime(
            runtime=SimpleNamespace(admission_provider=None),
            broker=object(),
            runtime_flags=object(),
            phase10_policy=object(),
            cash_ledger=object(),
            realized_journal=object(),
            capital_flags=CapitalAdmissionFeatureFlags(enabled=False),
            capital_policy=Phase12CapitalAdmissionPolicy(
                controlled_asset_id="BTCUSDT",
                max_exposure_percent=100,
            ),
        )

    assert called == []


def test_wire_phase12_installs_provider_and_preserves_phase11_runtime(monkeypatch):
    class FxResolver:
        def __init__(self):
            self.converter = exposure_calculator().fx_converter
            self.mtm_quotes = ()

    fx_resolver = FxResolver()
    phase10_metadata = SimpleNamespace(
        execution_config_hash="a",
        global_config_hash="b",
        asset_registry_hash="c",
        paper_mode="realistic_paper",
        feature_flags=MappingProxyType({}),
        runtime_policy=MappingProxyType({}),
        limitations=(),
    )
    fake_phase11_runtime = object()
    fake_phase11_bundle = SimpleNamespace(
        runtime=fake_phase11_runtime,
        phase10_bundle=SimpleNamespace(
            startup_metadata=phase10_metadata,
            wiring=SimpleNamespace(fx_resolver=fx_resolver),
        ),
    )
    monkeypatch.setattr(
        "src.execution.capital_runtime.wire_phase11_cash_runtime",
        lambda **kwargs: fake_phase11_bundle,
    )

    cash_ledger = SimpleNamespace(current_cash_pln=lambda: "1000")
    broker = SimpleNamespace(slippage_model=FixedBpsSlippage(0.0))
    base_runtime = SimpleNamespace(admission_provider=None)

    bundle = wire_phase12_capital_runtime(
        runtime=base_runtime,
        broker=broker,
        runtime_flags=object(),
        phase10_policy=object(),
        cash_ledger=cash_ledger,
        realized_journal=object(),
        capital_flags=CapitalAdmissionFeatureFlags(enabled=True),
        capital_policy=Phase12CapitalAdmissionPolicy(
            controlled_asset_id="BTCUSDT",
            max_exposure_percent=100,
        ),
    )

    assert bundle.runtime is fake_phase11_runtime
    assert base_runtime.admission_provider is bundle.admission_provider
    assert bundle.phase12_metadata.schema == "phase12-capital-admission-v1"
