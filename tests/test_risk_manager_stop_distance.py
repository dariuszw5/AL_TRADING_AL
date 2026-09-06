from src.risk.risk_manager import RiskManager


def test_position_size_scales_with_stop_distance():
    manager = RiskManager()

    wide_stop = manager.calculate_position_size(
        balance=1000.0,
        risk_percent=5.0,
        entry_price=100.0,
        stop_loss=95.0
    )

    tight_stop = manager.calculate_position_size(
        balance=1000.0,
        risk_percent=5.0,
        entry_price=100.0,
        stop_loss=99.0
    )

    assert wide_stop == 10.0
    assert tight_stop == 50.0


def test_position_size_keeps_risk_amount_constant():
    manager = RiskManager()

    entry_price = 100.0

    for stop_loss in (95.0, 98.0, 99.0):
        position_size = manager.calculate_position_size(
            balance=1000.0,
            risk_percent=5.0,
            entry_price=entry_price,
            stop_loss=stop_loss
        )

        risk = (
            abs(entry_price - stop_loss)
            * position_size
        )

        assert risk == 50.0
