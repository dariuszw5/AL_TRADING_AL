from src.risk.risk_manager import RiskManager


def test_risk_manager_exists():
    manager = RiskManager()

    assert manager is not None


def test_calculate_position_size():
    manager = RiskManager()

    result = manager.calculate_position_size(
        balance=1000.0,
        risk_percent=1.0,
        entry_price=100.0,
        stop_loss=95.0
    )

    assert result == 2.0


def test_calculate_position_size_with_higher_risk():
    manager = RiskManager()

    result = manager.calculate_position_size(
        balance=1000.0,
        risk_percent=2.0,
        entry_price=100.0,
        stop_loss=95.0
    )

    assert result == 4.0


def test_calculate_position_size_sell():
    manager = RiskManager()

    result = manager.calculate_position_size(
        balance=1000.0,
        risk_percent=1.0,
        entry_price=100.0,
        stop_loss=105.0
    )

    assert result == 2.0


def test_calculate_position_size_zero_distance():
    manager = RiskManager()

    result = manager.calculate_position_size(
        balance=1000.0,
        risk_percent=1.0,
        entry_price=100.0,
        stop_loss=100.0
    )

    assert result == 0.0


def test_calculate_position_size_negative_distance():
    manager = RiskManager()

    result = manager.calculate_position_size(
        balance=1000.0,
        risk_percent=1.0,
        entry_price=100.0,
        stop_loss=100.0
    )

    assert result == 0.0


def test_calculate_position_size_zero_balance():
    manager = RiskManager()

    result = manager.calculate_position_size(
        balance=0.0,
        risk_percent=1.0,
        entry_price=100.0,
        stop_loss=95.0
    )

    assert result == 0.0
