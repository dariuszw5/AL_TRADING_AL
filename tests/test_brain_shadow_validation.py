from math import sin
from types import SimpleNamespace

import src.agent.ai_manager as ai_manager


def _bars(n=600):
    start = 1_800_000_000_000
    candles = []
    for index in range(n):
        close = 100.0 + index * 0.02 + 1.5 * sin(index / 6)
        candles.append(SimpleNamespace(
            timestamp=start + index * ai_manager.MINUTE,
            open=close,
            high=close * 1.002,
            low=close * 0.998,
            close=close,
            volume=50.0,
        ))
    return candles


def test_shadow_validation_continues_when_live_model_rejects_signals(monkeypatch):
    monkeypatch.setattr(
        ai_manager,
        "signal_side",
        lambda strategy, candles, index: (
            "LONG" if strategy == "trend" else None
        ),
    )
    monkeypatch.setattr(
        ai_manager.NearestReturnModel,
        "predict",
        lambda self, features: (-0.01, 0.001),
    )

    rows = ai_manager.rank_asset("TESTUSDT", _bars())
    trend = next(
        row for row in rows
        if row["strategy"] == "trend" and row["side"] == "LONG"
    )
    assert trend["live_signal"] is True
    assert trend["eligible"] is False
    assert trend["validation_trades"] == 0
    assert trend["shadow_validation_trades"] >= 4
    assert trend["shadow_validation_mean"] is not None
    assert isinstance(trend["shadow_validation_wins"], int)
    assert "shadow_validation_profit_factor" in trend

    other = next(
        row for row in rows
        if row["strategy"] == "breakout" and row["side"] == "LONG"
    )
    assert other["shadow_validation_trades"] == 0
    assert other["shadow_validation_mean"] is None
