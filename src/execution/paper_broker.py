from __future__ import annotations

import hashlib
import json
from dataclasses import replace

from src.core.clock import SystemClock
from src.data.assets import get_asset
from src.data.market_data import (
    ExecutionQuality,
)

from .broker_interface import BrokerInterface
from .execution_policy import (
    ExecutionPolicy,
)
from .models import (
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
    RejectionReason,
)
from .slippage import FixedBpsSlippage


class PaperBroker(
    BrokerInterface
):

    def __init__(
        self,
        *,
        clock=None,
        asset_resolver=None,
        slippage_model=None,
        trading_fee_rate=0.0,
        simulated_spread_bps=None,
        derived_spread_bps=None,
        derived_spread_validated=False,
    ):
        trading_fee_rate = float(
            trading_fee_rate
        )

        if trading_fee_rate < 0:
            raise ValueError(
                "trading_fee_rate cannot be negative"
            )

        for name, value in (
            (
                "simulated_spread_bps",
                simulated_spread_bps,
            ),
            (
                "derived_spread_bps",
                derived_spread_bps,
            ),
        ):
            if (
                value is not None
                and float(value) < 0
            ):
                raise ValueError(
                    f"{name} cannot be negative"
                )

        self.clock = (
            clock
            or SystemClock()
        )

        self.asset_resolver = (
            asset_resolver
            or get_asset
        )

        self.slippage_model = (
            slippage_model
            or FixedBpsSlippage(0.0)
        )

        self.trading_fee_rate = (
            trading_fee_rate
        )

        self.simulated_spread_bps = (
            None
            if simulated_spread_bps
            is None
            else float(
                simulated_spread_bps
            )
        )

        self.derived_spread_bps = (
            None
            if derived_spread_bps
            is None
            else float(
                derived_spread_bps
            )
        )

        self.derived_spread_validated = bool(
            derived_spread_validated
        )

        self.policy = ExecutionPolicy(
            derived_spread_validated=(
                self.derived_spread_validated
            )
        )

        self._results_by_client_order_id = {}

    @property
    def config_hash(self):
        payload = {
            "execution_profile": (
                ExecutionProfile.REALISTIC_V2.value
            ),
            "trading_fee_rate": (
                self.trading_fee_rate
            ),
            "slippage": (
                self.slippage_model.config()
            ),
            "simulated_spread_bps": (
                self.simulated_spread_bps
            ),
            "derived_spread_bps": (
                self.derived_spread_bps
            ),
            "derived_spread_validated": (
                self.derived_spread_validated
            ),
        }

        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hashlib.sha256(
            encoded
        ).hexdigest()

    @staticmethod
    def _value(value):
        return getattr(
            value,
            "value",
            value,
        )

    @staticmethod
    def _short_mechanism(asset):
        value = getattr(
            asset,
            "short_mechanism",
            None,
        )

        value = getattr(
            value,
            "value",
            value,
        )

        if value is None:
            return None

        return str(
            value
        ).upper()

    @staticmethod
    def _short_financing(asset):
        value = getattr(
            asset,
            "short_financing_model",
            None,
        )

        return getattr(
            value,
            "value",
            value,
        )

    def _remember(
        self,
        result,
    ):
        self._results_by_client_order_id[
            result.order.client_order_id
        ] = result

        return result

    def _reject(
        self,
        order,
        reason,
        *,
        labels=(),
    ):
        return self._remember(
            BrokerResult(
                status=OrderStatus.REJECTED,
                order=order,
                rejection_reason=reason,
                labels=tuple(labels),
            )
        )

    def _pending(
        self,
        order,
        position,
        reason,
        *,
        labels=(),
    ):
        now = self.clock.now()

        pending = replace(
            position,
            status=PositionStatus.EXIT_PENDING,
            pending_exit_reason=(
                order.requested_exit_reason
                or str(
                    self._value(reason)
                )
            ),
            pending_since=(
                position.pending_since
                or now
            ),
        )

        return self._remember(
            BrokerResult(
                status=OrderStatus.EXIT_PENDING,
                order=order,
                position=pending,
                rejection_reason=reason,
                labels=tuple(labels),
            )
        )

    def _quote(
        self,
        market_snapshot,
    ):
        quality = (
            market_snapshot.execution_quality
        )

        if (
            quality
            is ExecutionQuality.REAL_BOOK
        ):
            bid = market_snapshot.bid
            ask = market_snapshot.ask

        elif (
            quality
            is ExecutionQuality.SIMULATED_SPREAD
        ):
            bid, ask = self._modelled_quote(
                market_snapshot.last,
                self.simulated_spread_bps,
            )

        elif (
            quality
            is ExecutionQuality.DERIVED_SPREAD
        ):
            bid, ask = self._modelled_quote(
                market_snapshot.last,
                self.derived_spread_bps,
            )

        else:
            return None

        if (
            bid is None
            or ask is None
            or bid <= 0
            or ask <= 0
            or bid > ask
        ):
            return None

        return (
            float(bid),
            float(ask),
        )

    @staticmethod
    def _modelled_quote(
        last,
        spread_bps,
    ):
        if (
            last is None
            or spread_bps is None
        ):
            return (
                None,
                None,
            )

        last = float(last)

        if last <= 0:
            return (
                None,
                None,
            )

        half_spread = (
            last
            * float(spread_bps)
            / 10000.0
            / 2.0
        )

        return (
            last - half_spread,
            last + half_spread,
        )

    def _check_short(
        self,
        order,
        asset,
    ):
        if (
            order.intent
            is not OrderIntent.ENTRY
            or order.side
            is not OrderSide.SELL
        ):
            return (
                None,
                (),
            )

        allow_short = bool(
            getattr(
                asset,
                "allow_short",
                False,
            )
        )

        mechanism = self._short_mechanism(
            asset
        )

        if (
            not allow_short
            or mechanism in {
                None,
                "",
                "NONE",
            }
        ):
            return (
                RejectionReason.SHORT_NOT_SUPPORTED,
                (),
            )

        if mechanism == "SYNTHETIC":
            if (
                order.paper_mode
                is PaperMode.REALISTIC_PAPER
            ):
                return (
                    RejectionReason.SHORT_NOT_SUPPORTED,
                    (),
                )

            return (
                None,
                (
                    "SYNTHETIC_SHORT",
                    "FINANCING_NOT_MODELLED",
                ),
            )

        return (
            None,
            (),
        )

    def submit_order(
        self,
        order,
        *,
        market_snapshot,
        market_session,
        position=None,
    ):
        existing = (
            self._results_by_client_order_id.get(
                order.client_order_id
            )
        )

        if existing is not None:
            if existing.order == order:
                return existing

            return BrokerResult(
                status=OrderStatus.REJECTED,
                order=order,
                rejection_reason=(
                    RejectionReason.IDEMPOTENCY_CONFLICT
                ),
                labels=(
                    "IDEMPOTENCY_CONFLICT",
                ),
            )

        if (
            order.execution_profile
            is not ExecutionProfile.REALISTIC_V2
        ):
            return self._reject(
                order,
                RejectionReason.PROFILE_NOT_ALLOWED,
            )

        if (
            market_snapshot.asset_id
            != order.asset_id
            or market_session.asset_id
            != order.asset_id
            or (
                position is not None
                and position.asset_id
                != order.asset_id
            )
        ):
            return self._reject(
                order,
                RejectionReason.INVALID_ORDER,
            )

        asset = self.asset_resolver(
            order.asset_id
        )

        if (
            order.intent
            is OrderIntent.ENTRY
            and position is not None
        ):
            return self._reject(
                order,
                RejectionReason.INVALID_ORDER,
            )

        if (
            order.intent
            is OrderIntent.ENTRY
            and order.side
            is OrderSide.BUY
            and not bool(
                getattr(
                    asset,
                    "allow_long",
                    False,
                )
            )
        ):
            return self._reject(
                order,
                RejectionReason.LONG_NOT_SUPPORTED,
            )

        if (
            order.intent
            is OrderIntent.EXIT
            and position is None
        ):
            return self._reject(
                order,
                RejectionReason.INVALID_ORDER,
            )

        if (
            order.intent
            is OrderIntent.EXIT
            and position is not None
        ):
            expected_side = (
                OrderSide.SELL
                if position.side
                is PositionSide.LONG
                else OrderSide.BUY
            )

            if order.side is not expected_side:
                return self._reject(
                    order,
                    RejectionReason.INVALID_ORDER,
                )

            if (
                order.quantity
                != position.quantity
            ):
                return self._reject(
                    order,
                    RejectionReason.INVALID_ORDER,
                )

            if (
                position.status
                is PositionStatus.CLOSED
            ):
                return self._reject(
                    order,
                    RejectionReason.INVALID_ORDER,
                )

        short_error, short_labels = (
            self._check_short(
                order,
                asset,
            )
        )

        if short_error is not None:
            return self._reject(
                order,
                short_error,
            )

        decision = self.policy.evaluate(
            order=order,
            market_snapshot=market_snapshot,
            market_session=market_session,
        )

        if not decision.allowed:
            if (
                order.intent
                is OrderIntent.EXIT
                and position is not None
            ):
                return self._pending(
                    order,
                    position,
                    decision.rejection_reason,
                    labels=decision.labels,
                )

            return self._reject(
                order,
                decision.rejection_reason,
                labels=decision.labels,
            )

        labels = tuple(
            dict.fromkeys(
                (
                    *decision.labels,
                    *short_labels,
                )
            )
        )

        quote = self._quote(
            market_snapshot
        )

        if quote is None:
            if (
                order.intent
                is OrderIntent.EXIT
                and position is not None
            ):
                return self._pending(
                    order,
                    position,
                    RejectionReason.QUOTE_UNAVAILABLE,
                    labels=labels,
                )

            return self._reject(
                order,
                RejectionReason.QUOTE_UNAVAILABLE,
                labels=labels,
            )

        bid, ask = quote

        reference_price = (
            ask
            if order.side
            is OrderSide.BUY
            else bid
        )

        execution_price = (
            self.slippage_model.apply(
                reference_price,
                order.side,
            )
        )

        execution_reason = (
            order.requested_exit_reason
            or "ENTRY"
        )

        if (
            order.intent
            is OrderIntent.EXIT
            and position is not None
            and position.stop_loss
            is not None
            and (
                order.requested_exit_reason
                == "STOP_LOSS"
                or position.status
                is PositionStatus.EXIT_PENDING
            )
        ):
            if (
                position.side
                is PositionSide.LONG
                and bid
                < position.stop_loss
            ):
                execution_reason = "STOP_GAP"

            elif (
                position.side
                is PositionSide.SHORT
                and ask
                > position.stop_loss
            ):
                execution_reason = "STOP_GAP"

        execution_timestamp = (
            self.clock.now()
        )

        slippage = abs(
            execution_price
            - reference_price
        )

        fee = abs(
            execution_price
            * order.quantity
            * self.trading_fee_rate
        )

        short_label = (
            "SYNTHETIC_SHORT"
            if "SYNTHETIC_SHORT"
            in labels
            else None
        )

        execution = Execution(
            execution_id=(
                f"exec-{order.order_id}"
            ),
            order_id=order.order_id,
            asset_id=order.asset_id,
            side=order.side,
            quantity=order.quantity,
            reference_price=reference_price,
            execution_price=execution_price,
            bid=bid,
            ask=ask,
            spread=ask - bid,
            slippage=slippage,
            fee=fee,
            provider_timestamp=(
                market_snapshot.provider_timestamp
            ),
            execution_timestamp=(
                execution_timestamp
            ),
            data_quality=(
                market_snapshot.data_quality
            ),
            execution_quality=(
                market_snapshot.execution_quality
            ),
            session_quality=(
                market_session.session_quality
            ),
            paper_mode=order.paper_mode,
            short_label=short_label,
            trigger_reason=(
                order.requested_exit_reason
            ),
            pending_reason=None,
            execution_reason=(
                execution_reason
            ),
            labels=labels,
        )

        if (
            order.intent
            is OrderIntent.ENTRY
        ):
            if (
                order.side
                is OrderSide.BUY
            ):
                position_side = (
                    PositionSide.LONG
                )
                mechanism = None
                financing = None

            else:
                position_side = (
                    PositionSide.SHORT
                )
                mechanism = (
                    self._short_mechanism(
                        asset
                    )
                )
                financing = (
                    self._short_financing(
                        asset
                    )
                )

                if (
                    mechanism == "SYNTHETIC"
                    and financing is None
                ):
                    financing = (
                        "FINANCING_NOT_MODELLED"
                    )

            new_position = Position(
                position_id=(
                    f"pos-{order.order_id}"
                ),
                asset_id=order.asset_id,
                side=position_side,
                quantity=order.quantity,
                entry_execution_id=(
                    execution.execution_id
                ),
                entry_price=execution_price,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                opened_at=(
                    execution_timestamp
                ),
                short_mechanism=mechanism,
                short_financing_model=(
                    financing
                ),
                execution_profile=(
                    ExecutionProfile.REALISTIC_V2
                ),
                execution_quality_at_entry=(
                    market_snapshot.execution_quality
                ),
                status=PositionStatus.OPEN,
            )

        else:
            new_position = replace(
                position,
                status=PositionStatus.CLOSED,
                closed_at=(
                    execution_timestamp
                ),
                exit_execution_id=(
                    execution.execution_id
                ),
                exit_price=execution_price,
                pending_exit_reason=None,
                pending_since=None,
            )

        return self._remember(
            BrokerResult(
                status=OrderStatus.FILLED,
                order=order,
                execution=execution,
                position=new_position,
                labels=labels,
            )
        )
