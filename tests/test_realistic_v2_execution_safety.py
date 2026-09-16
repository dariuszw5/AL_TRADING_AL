from dataclasses import replace
from datetime import datetime, timezone

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


class FakeAsset:
    def __init__(
        self,
        asset_id="TEST",
        *,
        allow_long=True,
        allow_short=False,
        short_mechanism="NONE",
        short_financing_model=None,
    ):
        self.asset_id = asset_id
        self.allow_long = allow_long
        self.allow_short = allow_short
        self.short_mechanism = short_mechanism
        self.short_financing_model = (
            short_financing_model
        )


def make_asset_resolver(
    *,
    allow_long=True,
):
    def resolver(asset_id):
        return FakeAsset(
            asset_id=asset_id,
            allow_long=allow_long,
        )

    return resolver


def make_broker(
    *,
    allow_long=True,
):
    return PaperBroker(
        clock=FixedClock(NOW),
        asset_resolver=make_asset_resolver(
            allow_long=allow_long,
        ),
        slippage_model=FixedBpsSlippage(
            0.0
        ),
        trading_fee_rate=0.0,
    )


def snapshot(
    asset_id="TEST",
    *,
    bid=100.0,
    ask=101.0,
    provider_status=ProviderStatus.CONNECTED,
):
    return MarketSnapshot(
        asset_id=asset_id,
        bid=bid,
        ask=ask,
        last=(bid + ask) / 2.0,
        provider_timestamp=NOW,
        received_at=NOW,
        data_quality=DataQuality.REALTIME,
        delayed=False,
        quote_age_seconds=0.0,
        provider_status=provider_status,
        execution_quality=(
            ExecutionQuality.REAL_BOOK
        ),
    )


def session(
    asset_id="TEST",
    *,
    state=SessionState.OPEN,
    quality=SessionQuality.EXCHANGE_CALENDAR,
):
    return MarketSessionSnapshot(
        asset_id=asset_id,
        session_id="TEST_SESSION",
        state=state,
        session_quality=quality,
        observed_at=NOW,
        timezone_name="UTC",
        local_time=NOW,
        reason="TEST",
        calendar_version="test-v1",
    )


def order(
    *,
    client_id,
    asset_id="TEST",
    side=OrderSide.BUY,
    intent=OrderIntent.ENTRY,
    quantity=2.0,
    stop_loss=95.0,
    take_profit=110.0,
    exit_reason=None,
    paper_mode=PaperMode.REALISTIC_PAPER,
):
    return Order(
        order_id=f"order-{client_id}",
        client_order_id=client_id,
        asset_id=asset_id,
        side=side,
        quantity=quantity,
        intent=intent,
        created_at=NOW,
        execution_profile=(
            ExecutionProfile.REALISTIC_V2
        ),
        paper_mode=paper_mode,
        signal_reference="safety-test",
        requested_exit_reason=exit_reason,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )


def open_long(
    broker,
    *,
    asset_id="TEST",
):
    result = broker.submit_order(
        order(
            client_id=f"{asset_id}-entry",
            asset_id=asset_id,
        ),
        market_snapshot=snapshot(
            asset_id
        ),
        market_session=session(
            asset_id
        ),
    )

    assert result.status is OrderStatus.FILLED
    assert (
        result.position.side
        is PositionSide.LONG
    )

    return result.position


def test_long_entry_rejected_when_allow_long_false():
    broker = make_broker(
        allow_long=False
    )

    result = broker.submit_order(
        order(
            client_id="long-disabled"
        ),
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert (
        result.status
        is OrderStatus.REJECTED
    )

    assert (
        result.rejection_reason
        is RejectionReason.LONG_NOT_SUPPORTED
    )


def test_snapshot_asset_mismatch_is_rejected():
    broker = make_broker()

    result = broker.submit_order(
        order(
            client_id="snapshot-mismatch"
        ),
        market_snapshot=snapshot(
            "OTHER"
        ),
        market_session=session(
            "TEST"
        ),
    )

    assert (
        result.status
        is OrderStatus.REJECTED
    )

    assert (
        result.rejection_reason
        is RejectionReason.INVALID_ORDER
    )


def test_session_asset_mismatch_is_rejected():
    broker = make_broker()

    result = broker.submit_order(
        order(
            client_id="session-mismatch"
        ),
        market_snapshot=snapshot(
            "TEST"
        ),
        market_session=session(
            "OTHER"
        ),
    )

    assert (
        result.status
        is OrderStatus.REJECTED
    )

    assert (
        result.rejection_reason
        is RejectionReason.INVALID_ORDER
    )


def test_exit_position_asset_mismatch_is_rejected():
    broker = make_broker()

    position = open_long(
        broker
    )

    wrong_position = replace(
        position,
        asset_id="OTHER",
    )

    result = broker.submit_order(
        order(
            client_id="position-mismatch",
            side=OrderSide.SELL,
            intent=OrderIntent.EXIT,
            exit_reason="TIME_EXIT",
        ),
        market_snapshot=snapshot(),
        market_session=session(),
        position=wrong_position,
    )

    assert (
        result.status
        is OrderStatus.REJECTED
    )

    assert (
        result.rejection_reason
        is RejectionReason.INVALID_ORDER
    )


def test_long_exit_requires_sell_side():
    broker = make_broker()

    position = open_long(
        broker
    )

    result = broker.submit_order(
        order(
            client_id="wrong-exit-side",
            side=OrderSide.BUY,
            intent=OrderIntent.EXIT,
            exit_reason="TIME_EXIT",
        ),
        market_snapshot=snapshot(),
        market_session=session(),
        position=position,
    )

    assert (
        result.status
        is OrderStatus.REJECTED
    )

    assert (
        result.rejection_reason
        is RejectionReason.INVALID_ORDER
    )


def test_exit_quantity_must_match_position_quantity():
    broker = make_broker()

    position = open_long(
        broker
    )

    result = broker.submit_order(
        order(
            client_id="wrong-exit-qty",
            side=OrderSide.SELL,
            intent=OrderIntent.EXIT,
            quantity=1.0,
            exit_reason="TIME_EXIT",
        ),
        market_snapshot=snapshot(),
        market_session=session(),
        position=position,
    )

    assert (
        result.status
        is OrderStatus.REJECTED
    )

    assert (
        result.rejection_reason
        is RejectionReason.INVALID_ORDER
    )


def test_entry_with_existing_position_is_rejected():
    broker = make_broker()

    position = open_long(
        broker
    )

    result = broker.submit_order(
        order(
            client_id="second-entry"
        ),
        market_snapshot=snapshot(),
        market_session=session(),
        position=position,
    )

    assert (
        result.status
        is OrderStatus.REJECTED
    )

    assert (
        result.rejection_reason
        is RejectionReason.INVALID_ORDER
    )


def test_conflicting_client_order_id_is_rejected():
    broker = make_broker()

    first_order = order(
        client_id="same-client-id",
        quantity=2.0,
    )

    first = broker.submit_order(
        first_order,
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert (
        first.status
        is OrderStatus.FILLED
    )

    conflicting_order = order(
        client_id="same-client-id",
        quantity=3.0,
    )

    second = broker.submit_order(
        conflicting_order,
        market_snapshot=snapshot(),
        market_session=session(),
    )

    assert (
        second.status
        is OrderStatus.REJECTED
    )

    assert (
        second.rejection_reason
        is RejectionReason.IDEMPOTENCY_CONFLICT
    )

    assert second.order == conflicting_order


def test_disconnected_provider_is_rejected():
    broker = make_broker()

    result = broker.submit_order(
        order(
            client_id="provider-down"
        ),
        market_snapshot=snapshot(
            provider_status=(
                ProviderStatus.DISCONNECTED
            )
        ),
        market_session=session(),
    )

    assert (
        result.status
        is OrderStatus.REJECTED
    )

    assert (
        result.rejection_reason
        is RejectionReason.PROVIDER_UNAVAILABLE
    )


def test_degraded_provider_is_explicitly_labelled():
    broker = make_broker()

    result = broker.submit_order(
        order(
            client_id="provider-degraded"
        ),
        market_snapshot=snapshot(
            provider_status=(
                ProviderStatus.DEGRADED
            )
        ),
        market_session=session(),
    )

    assert (
        result.status
        is OrderStatus.FILLED
    )

    assert (
        "PROVIDER_DEGRADED"
        in result.labels
    )


def test_unknown_session_quality_is_rejected():
    broker = make_broker()

    result = broker.submit_order(
        order(
            client_id="unknown-session"
        ),
        market_snapshot=snapshot(),
        market_session=session(
            quality=SessionQuality.UNKNOWN
        ),
    )

    assert (
        result.status
        is OrderStatus.REJECTED
    )

    assert (
        result.rejection_reason
        is RejectionReason.SESSION_UNAVAILABLE
    )


def test_pending_time_exit_reopens_as_stop_gap():
    broker = make_broker()

    position = open_long(
        broker
    )

    pending = broker.submit_order(
        order(
            client_id="pending-time-exit",
            side=OrderSide.SELL,
            intent=OrderIntent.EXIT,
            exit_reason="TIME_EXIT",
        ),
        market_snapshot=snapshot(),
        market_session=session(
            state=SessionState.CLOSED
        ),
        position=position,
    )

    assert (
        pending.status
        is OrderStatus.EXIT_PENDING
    )

    assert (
        pending.position.status
        is PositionStatus.EXIT_PENDING
    )

    reopened = broker.submit_order(
        order(
            client_id="reopen-time-exit",
            side=OrderSide.SELL,
            intent=OrderIntent.EXIT,
            exit_reason="TIME_EXIT",
        ),
        market_snapshot=snapshot(
            bid=90.0,
            ask=91.0,
        ),
        market_session=session(),
        position=pending.position,
    )

    assert (
        reopened.status
        is OrderStatus.FILLED
    )

    assert (
        reopened.execution.execution_reason
        == "STOP_GAP"
    )

    assert (
        reopened.execution.reference_price
        == 90.0
    )
