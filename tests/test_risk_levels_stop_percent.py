from src.risk.risk_levels import RiskLevels


def test_stop_loss_accepts_custom_stop_loss_percent_for_buy():
    risk_levels = RiskLevels()

    result = risk_levels.calculate_stop_loss(
        entry_price=100.0,
        risk_percent=5.0,
        stop_loss_percent=1.5,
        side="BUY"
    )

    assert result == 98.5


def test_stop_loss_accepts_custom_stop_loss_percent_for_sell():
    risk_levels = RiskLevels()

    result = risk_levels.calculate_stop_loss(
        entry_price=100.0,
        risk_percent=5.0,
        stop_loss_percent=1.5,
        side="SELL"
    )

    assert result == 101.5


def test_stop_loss_defaults_to_risk_percent():
    risk_levels = RiskLevels()

    result = risk_levels.calculate_stop_loss(
        entry_price=100.0,
        risk_percent=5.0,
        side="BUY"
    )

    assert result == 95.0