from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from src.core.clock import FixedClock
from src.data.market_data import (
    DataQuality,
    ExecutionQuality,
    MarketSnapshot,
    ProviderStatus,
)
from src.execution.models import (
    ExecutionProfile,
    Order,
    OrderIntent,
    OrderSide,
    OrderStatus,
    PaperMode,
    Position,
    PositionSide,
    PositionStatus,
    RejectionReason,
)
from src.execution.paper_broker import PaperBroker
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


@dataclass(frozen=True)
class FakeAsset:
    asset_id: str
    allow_long: bool = True
    allow_short: bool = True
    short_mechanism: str = "MARGIN"
    short_financing_model: str | None = None


def asset_resolver(
    *,
    allow_short=True,
    short_mechanism="MARGIN",
    financing=None,
):
    asset = FakeAsset(
        asset_id="TEST",
        allow_short=allow_short,
        short_mechanism=short_mechanism,
        short_financing_model=financing,
    )

    def resolve(asset_id):
        assert asset_id == "TEST"
        return asset

    return resolve


def snapshot(
    *,
    bid=100.0,
    ask=101.0,
    last=100.5,
    quality=ExecutionQuality.REAL_BOOK,
    data_quality=DataQuality.REALTIME,
    delayed=False,
):
    return MarketSnapshot(
        asset_id="TEST",
        bid=bid,
        ask=ask,
        last=last,
        provider_timestamp=NOW,
        received_at=NOW,
        data_quality=data_quality,
        delayed=delayed,
        quote_age_seconds=0.0,
        provider_status=ProviderStatus.CONNECTED,
        execution_quality=quality,
    )


def session(
    state=SessionState.OPEN,
):
    return MarketSessionSnapshot(
        asset_id="TEST",
        session_id="TEST_SESSION",
        state=state,
        session_quality=SessionQuality.EXCHANGE_CALENDAR,
        observed_at=NOW,
        timezone_name="UTC",
        local_time=NOW,
        reason="TEST",
        calendar_version="test-v1",
    )


def order(
    *,
    side,
    intent=OrderIntent.ENTRY,
    client_order_id="client-1",
    profile=ExecutionProfile.REALISTIC_V2,
    mode=PaperMode.REALISTIC_PAPER,
    exit_reason=None,
    stop_loss=None,
    take_profit=None,
):
    return Order(
        order_id=f"order-{client_order_id}",
        client_order_id=client_order_id,
        asset_id="TEST",
        side=side,
        quantity=2.0,
        intent=intent,
        created_at=NOW,
        execution_profile=profile,
        paper_mode=mode,
        requested_exit_reason=exit_reason,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )


def broker(
    *,
    allow_short=True,
    short_mechanism="MARGIN",
    slippage_bps=0.0,
    simulated_spread_bps=None,
    derived_spread_bps=None,
    derived_spread_validated=False,
):
    return PaperBroker(
        clock=FixedClock(NOW),
        asset_resolver=asset_resolver(
            allow_short=allow_short,
            short_mechanism=short_mechanism,
        ),
        slippage_model=FixedBpsSlippage(
            slippage_bps
        ),
        trading_fee_rate=0.0,
        simulated_spread_bps=(
            simulated_spread_bps
        ),
        derived_spread_bps=(
            derived_spread_bps
        ),
        derived_spread_validated=(
            derived_spread_validated
        ),
    )


def long_position(
    *,
    status=PositionStatus.OPEN,
    stop_loss=95.0,
):
    return Position(
        position_id="pos-long",
        asset_id="TEST",
        side=PositionSide.LONG,
        quantity=2.0,
        entry_execution_id="exec-entry",
        entry_price=101.0,
        stop_loss=stop_loss,
        take_profit=110.0,
        opened_at=NOW,
        short_mechanism=None,
        short_financing_model=None,
        execution_profile=(
            ExecutionProfile.REALISTIC_V2
        ),
        execution_quality_at_entry=(
            ExecutionQuality.REAL_BOOK
        ),
        status=status,
        pending_exit_reason=(
            "TIME_EXIT"
            if status
            is PositionStatus.EXIT_PENDING
            else None
        ),
        pending_since=(
            NOW
            if status
            is PositionStatus.EXIT_PENDING
            else None
        ),
    )


def short_position(
    *,
    stop_loss=105.0,
):
    return Position(
        position_id="pos-short",
        asset_id="TEST",
        side=PositionSide.SHORT,
        quantity=2.0,
        entry_execution_id="exec-entry",
        entry_price=100.0,
        stop_loss=stop_loss,
        take_profit=90.0,
        opened_at=NOW,
        short_mechanism="MARGIN",
        short_financing_model=None,
        execution_profile=(
            ExecutionProfile.REALISTIC_V2
        ),
        execution_quality_at_entry=(
            ExecutionQuality.REAL_BOOK
        ),
        status=PositionStatus.OPEN,
    )


def test_buy_entry_uses_ask():
    result = broker().submit_order(
        order(
            side=OrderSide.BUY
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert result.status is OrderStatus.FILLED
    assert result.execution.reference_price == 101.0
    assert result.execution.execution_price == 101.0
    assert result.position.side is PositionSide.LONG


def test_buy_entry_applies_adverse_slippage():
    result = broker(
        slippage_bps=10.0
    ).submit_order(
        order(
            side=OrderSide.BUY
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert result.execution.reference_price == 101.0

    assert result.execution.execution_price == pytest.approx(
        101.0 * 1.001
    )


def test_short_entry_uses_bid():
    result = broker().submit_order(
        order(
            side=OrderSide.SELL
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert result.status is OrderStatus.FILLED
    assert result.execution.reference_price == 100.0
    assert result.position.side is PositionSide.SHORT


def test_long_exit_uses_bid():
    result = broker().submit_order(
        order(
            side=OrderSide.SELL,
            intent=OrderIntent.EXIT,
            exit_reason="TIME_EXIT",
        ),
        market_snapshot=snapshot(),
        market_session=session(),
        position=long_position(),
    )

    assert result.execution.reference_price == 100.0
    assert result.position.status is PositionStatus.CLOSED


def test_short_exit_uses_ask():
    result = broker().submit_order(
        order(
            side=OrderSide.BUY,
            intent=OrderIntent.EXIT,
            exit_reason="TIME_EXIT",
        ),
        market_snapshot=snapshot(),
        market_session=session(),
        position=short_position(),
    )

    assert result.execution.reference_price == 101.0
    assert result.position.status is PositionStatus.CLOSED


def test_unsupported_short_is_rejected():
    result = broker(
        allow_short=False,
        short_mechanism="NONE",
    ).submit_order(
        order(
            side=OrderSide.SELL
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert result.status is OrderStatus.REJECTED

    assert (
        result.rejection_reason
        is RejectionReason.SHORT_NOT_SUPPORTED
    )


def test_synthetic_short_rejected_in_realistic_paper():
    result = broker(
        short_mechanism="SYNTHETIC",
    ).submit_order(
        order(
            side=OrderSide.SELL,
            mode=PaperMode.REALISTIC_PAPER,
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert result.status is OrderStatus.REJECTED

    assert (
        result.rejection_reason
        is RejectionReason.SHORT_NOT_SUPPORTED
    )


def test_synthetic_short_research_has_labels():
    result = broker(
        short_mechanism="SYNTHETIC",
    ).submit_order(
        order(
            side=OrderSide.SELL,
            mode=PaperMode.RESEARCH_PAPER,
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert result.status is OrderStatus.FILLED

    assert "SYNTHETIC_SHORT" in result.labels
    assert "FINANCING_NOT_MODELLED" in result.labels


def test_stale_entry_rejected():
    result = broker().submit_order(
        order(
            side=OrderSide.BUY
        ),
        market_snapshot=snapshot(
            data_quality=DataQuality.STALE,
            delayed=True,
        ),
        market_session=session(),
    )

    assert result.status is OrderStatus.REJECTED

    assert (
        result.rejection_reason
        is RejectionReason.STALE_DATA
    )


def test_delayed_entry_rejected_in_realistic_paper():
    result = broker().submit_order(
        order(
            side=OrderSide.BUY,
            mode=PaperMode.REALISTIC_PAPER,
        ),
        market_snapshot=snapshot(
            data_quality=DataQuality.DELAYED,
            delayed=True,
        ),
        market_session=session(),
    )

    assert result.status is OrderStatus.REJECTED

    assert (
        result.rejection_reason
        is RejectionReason.DELAYED_DATA
    )


def test_delayed_entry_research_is_labelled():
    result = broker().submit_order(
        order(
            side=OrderSide.BUY,
            mode=PaperMode.RESEARCH_PAPER,
        ),
        market_snapshot=snapshot(
            data_quality=DataQuality.DELAYED,
            delayed=True,
        ),
        market_session=session(),
    )

    assert result.status is OrderStatus.FILLED
    assert "DELAYED_DATA" in result.labels


def test_execution_records_real_book_quality():
    result = broker().submit_order(
        order(
            side=OrderSide.BUY
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert (
        result.execution.execution_quality
        is ExecutionQuality.REAL_BOOK
    )


def test_simulated_spread_rejected_in_realistic_paper():
    result = broker(
        simulated_spread_bps=20.0
    ).submit_order(
        order(
            side=OrderSide.BUY,
            mode=PaperMode.REALISTIC_PAPER,
        ),
        market_snapshot=snapshot(
            bid=None,
            ask=None,
            last=100.0,
            quality=ExecutionQuality.SIMULATED_SPREAD,
        ),
        market_session=session(),
    )

    assert result.status is OrderStatus.REJECTED

    assert (
        result.rejection_reason
        is RejectionReason.SIMULATED_SPREAD_NOT_ALLOWED
    )


def test_simulated_spread_research_is_labelled():
    result = broker(
        simulated_spread_bps=20.0
    ).submit_order(
        order(
            side=OrderSide.BUY,
            mode=PaperMode.RESEARCH_PAPER,
        ),
        market_snapshot=snapshot(
            bid=None,
            ask=None,
            last=100.0,
            quality=ExecutionQuality.SIMULATED_SPREAD,
        ),
        market_session=session(),
    )

    assert result.status is OrderStatus.FILLED

    assert (
        result.execution.execution_quality
        is ExecutionQuality.SIMULATED_SPREAD
    )

    assert "SIMULATED_SPREAD" in result.labels

    assert result.execution.reference_price == pytest.approx(
        100.1
    )


def test_untradeable_is_rejected():
    result = broker().submit_order(
        order(
            side=OrderSide.BUY
        ),
        market_snapshot=snapshot(
            bid=None,
            ask=None,
            last=100.0,
            quality=ExecutionQuality.UNTRADEABLE,
        ),
        market_session=session(),
    )

    assert result.status is OrderStatus.REJECTED

    assert (
        result.rejection_reason
        is RejectionReason.UNTRADEABLE
    )


def test_market_closed_rejects_new_entry():
    result = broker().submit_order(
        order(
            side=OrderSide.BUY
        ),
        market_snapshot=snapshot(),
        market_session=session(
            SessionState.CLOSED
        ),
    )

    assert result.status is OrderStatus.REJECTED

    assert (
        result.rejection_reason
        is RejectionReason.MARKET_CLOSED
    )


def test_time_exit_while_closed_becomes_pending():
    result = broker().submit_order(
        order(
            side=OrderSide.SELL,
            intent=OrderIntent.EXIT,
            exit_reason="TIME_EXIT",
        ),
        market_snapshot=snapshot(),
        market_session=session(
            SessionState.CLOSED
        ),
        position=long_position(),
    )

    assert result.status is OrderStatus.EXIT_PENDING

    assert (
        result.position.status
        is PositionStatus.EXIT_PENDING
    )

    assert (
        result.position.pending_exit_reason
        == "TIME_EXIT"
    )


def test_pending_exit_executes_after_reopen():
    result = broker().submit_order(
        order(
            side=OrderSide.SELL,
            intent=OrderIntent.EXIT,
            exit_reason="TIME_EXIT",
        ),
        market_snapshot=snapshot(),
        market_session=session(
            SessionState.OPEN
        ),
        position=long_position(
            status=PositionStatus.EXIT_PENDING
        ),
    )

    assert result.status is OrderStatus.FILLED
    assert result.position.status is PositionStatus.CLOSED
    assert result.execution.reference_price == 100.0


def test_long_stop_gap_fills_at_executable_bid():
    result = broker().submit_order(
        order(
            side=OrderSide.SELL,
            intent=OrderIntent.EXIT,
            exit_reason="STOP_LOSS",
        ),
        market_snapshot=snapshot(
            bid=92.0,
            ask=93.0,
            last=92.5,
        ),
        market_session=session(),
        position=long_position(
            stop_loss=95.0
        ),
    )

    assert result.status is OrderStatus.FILLED
    assert result.execution.reference_price == 92.0
    assert result.execution.execution_reason == "STOP_GAP"


def test_short_stop_gap_fills_at_executable_ask():
    result = broker().submit_order(
        order(
            side=OrderSide.BUY,
            intent=OrderIntent.EXIT,
            exit_reason="STOP_LOSS",
        ),
        market_snapshot=snapshot(
            bid=108.0,
            ask=109.0,
            last=108.5,
        ),
        market_session=session(),
        position=short_position(
            stop_loss=105.0
        ),
    )

    assert result.status is OrderStatus.FILLED
    assert result.execution.reference_price == 109.0
    assert result.execution.execution_reason == "STOP_GAP"


def test_client_order_id_is_idempotent():
    paper_broker = broker()

    first = paper_broker.submit_order(
        order(
            side=OrderSide.BUY,
            client_order_id="same",
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    second = paper_broker.submit_order(
        order(
            side=OrderSide.BUY,
            client_order_id="same",
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert second is first


def test_legacy_profile_not_allowed_in_paper_broker():
    result = broker().submit_order(
        order(
            side=OrderSide.BUY,
            profile=ExecutionProfile.LEGACY_V1,
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert result.status is OrderStatus.REJECTED

    assert (
        result.rejection_reason
        is RejectionReason.PROFILE_NOT_ALLOWED
    )


def test_config_hash_changes_with_slippage():
    a = broker(
        slippage_bps=0.0
    )

    b = broker(
        slippage_bps=10.0
    )

    assert a.config_hash != b.config_hash
    assert len(a.config_hash) == 64
    assert len(b.config_hash) == 64
