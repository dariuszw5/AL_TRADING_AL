from src.risk.risk_levels import RiskLevels


def test_stop_loss():
    risk_levels = RiskLevels()

    stop_loss = risk_levels.calculate_stop_loss(
        entry_price=100.0,
        risk_percent=5.0
    )

    assert stop_loss == 95.0


def test_take_profit():
    risk_levels = RiskLevels()

    take_profit = risk_levels.calculate_take_profit(
        entry_price=100.0,
        stop_loss=95.0,
        risk_reward_ratio=2.0
    )

    assert take_profit == 110.0