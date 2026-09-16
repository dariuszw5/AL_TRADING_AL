from __future__ import annotations

from abc import ABC, abstractmethod

from .models import OrderSide


class SlippageModel(ABC):

    @abstractmethod
    def apply(
        self,
        reference_price: float,
        side: OrderSide,
    ) -> float:
        raise NotImplementedError

    @abstractmethod
    def config(self) -> dict:
        raise NotImplementedError


class FixedBpsSlippage(
    SlippageModel
):

    def __init__(
        self,
        bps: float = 0.0,
    ):
        bps = float(bps)

        if bps < 0:
            raise ValueError(
                "slippage bps cannot be negative"
            )

        self.bps = bps

    def apply(
        self,
        reference_price: float,
        side: OrderSide,
    ) -> float:
        reference_price = float(
            reference_price
        )

        if reference_price <= 0:
            raise ValueError(
                "reference_price must be positive"
            )

        factor = (
            self.bps
            / 10000.0
        )

        if side is OrderSide.BUY:
            return (
                reference_price
                * (1.0 + factor)
            )

        if side is OrderSide.SELL:
            return (
                reference_price
                * (1.0 - factor)
            )

        raise ValueError(
            f"Unsupported side: {side}"
        )

    def config(self):
        return {
            "model": "FixedBpsSlippage",
            "bps": self.bps,
        }
