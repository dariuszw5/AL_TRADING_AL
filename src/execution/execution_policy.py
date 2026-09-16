from __future__ import annotations

from dataclasses import dataclass

from src.data.market_data import ExecutionQuality

from .models import (
    OrderIntent,
    PaperMode,
    RejectionReason,
)


def enum_value(value):
    return getattr(
        value,
        "value",
        value,
    )


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    rejection_reason: (
        RejectionReason | None
    ) = None
    labels: tuple[str, ...] = ()


class ExecutionPolicy:

    OPEN_SESSION_STATES = {
        "OPEN",
        "PRE_MARKET",
        "REGULAR",
        "AFTER_HOURS",
    }

    def __init__(
        self,
        *,
        derived_spread_validated=False,
    ):
        self.derived_spread_validated = bool(
            derived_spread_validated
        )

    def evaluate(
        self,
        *,
        order,
        market_snapshot,
        market_session,
    ):
        labels = []

        provider_status = str(
            enum_value(
                market_snapshot.provider_status
            )
        ).upper()

        if provider_status in {
            "DISCONNECTED",
            "RATE_LIMITED",
            "ERROR",
        }:
            return PolicyDecision(
                False,
                RejectionReason.PROVIDER_UNAVAILABLE,
            )

        if provider_status == "DEGRADED":
            labels.append(
                "PROVIDER_DEGRADED"
            )

        session_quality = str(
            enum_value(
                market_session.session_quality
            )
        ).upper()

        if session_quality == "UNKNOWN":
            return PolicyDecision(
                False,
                RejectionReason.SESSION_UNAVAILABLE,
            )

        session_state = enum_value(
            market_session.state
        )

        if (
            session_state
            not in self.OPEN_SESSION_STATES
        ):
            return PolicyDecision(
                False,
                RejectionReason.MARKET_CLOSED,
            )

        data_quality = str(
            enum_value(
                market_snapshot.data_quality
            )
        ).upper()

        if data_quality == "STALE":
            return PolicyDecision(
                False,
                RejectionReason.STALE_DATA,
            )

        delayed = (
            market_snapshot.delayed is True
            or data_quality == "DELAYED"
        )

        if delayed:
            if (
                order.paper_mode
                is PaperMode.REALISTIC_PAPER
            ):
                return PolicyDecision(
                    False,
                    RejectionReason.DELAYED_DATA,
                )

            labels.append(
                "DELAYED_DATA"
            )

        quality = (
            market_snapshot.execution_quality
        )

        if (
            quality
            is ExecutionQuality.UNTRADEABLE
        ):
            return PolicyDecision(
                False,
                RejectionReason.UNTRADEABLE,
            )

        if (
            quality
            is ExecutionQuality.SIMULATED_SPREAD
        ):
            if (
                order.paper_mode
                is PaperMode.REALISTIC_PAPER
            ):
                return PolicyDecision(
                    False,
                    RejectionReason.SIMULATED_SPREAD_NOT_ALLOWED,
                )

            labels.append(
                "SIMULATED_SPREAD"
            )

        if (
            quality
            is ExecutionQuality.DERIVED_SPREAD
        ):
            if (
                order.paper_mode
                is PaperMode.REALISTIC_PAPER
                and not self.derived_spread_validated
            ):
                return PolicyDecision(
                    False,
                    RejectionReason.DERIVED_SPREAD_NOT_VALIDATED,
                )

            labels.append(
                "DERIVED_SPREAD"
            )

        return PolicyDecision(
            True,
            labels=tuple(labels),
        )

    def evaluate_exit(
        self,
        *,
        order,
        market_snapshot,
        market_session,
    ):
        decision = self.evaluate(
            order=order,
            market_snapshot=market_snapshot,
            market_session=market_session,
        )

        if decision.allowed:
            return decision

        # For an exit we fail safely into
        # EXIT_PENDING instead of inventing
        # an executable price.
        return decision
