from types import SimpleNamespace

from src.execution.models import (
    OrderIntent,
    OrderSide,
)
from scripts.run_realistic_smoke_fill import (
    SmokeEntryDecision,
)


def test_smoke_existing_position_still_holds_by_default():
    decision = SmokeEntryDecision(
        quantity=0.0001,
    )

    result = decision(
        asset_id="BTCUSDT",
        snapshot=SimpleNamespace(
            bid=100.0,
            ask=101.0,
            last=100.5,
        ),
        position=SimpleNamespace(
            quantity=0.0001,
        ),
    )

    assert result is None


def test_smoke_close_uses_exact_position_quantity():
    decision = SmokeEntryDecision(
        quantity=0.0001,
        close_existing=True,
    )

    result = decision(
        asset_id="BTCUSDT",
        snapshot=SimpleNamespace(
            bid=100.0,
            ask=101.0,
            last=100.5,
        ),
        position=SimpleNamespace(
            quantity=0.0001,
        ),
    )

    assert result.intent is OrderIntent.EXIT
    assert result.side is OrderSide.SELL
    assert result.quantity == 0.0001
    assert result.exit_reason == "SMOKE_CLOSE"

    assert (
        result.signal_reference
        == "CONTROLLED_SMOKE_EXIT_NOT_STRATEGY_SIGNAL"
    )
