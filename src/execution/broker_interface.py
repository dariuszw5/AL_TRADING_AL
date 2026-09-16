from __future__ import annotations

from abc import ABC, abstractmethod

from .models import (
    BrokerResult,
    Order,
    Position,
)


class BrokerInterface(ABC):

    @abstractmethod
    def submit_order(
        self,
        order: Order,
        *,
        market_snapshot,
        market_session,
        position: Position | None = None,
    ) -> BrokerResult:
        raise NotImplementedError
