from src.agent.risk_guard import RiskGuard


def test_risk_guard_exists():
    guard = RiskGuard()

    assert guard is not None


def test_risk_guard_initial_loss_is_zero():
    guard = RiskGuard(max_daily_loss=100.0)

    assert guard.daily_loss == 0.0


def test_risk_guard_allows_trade_under_limit():
    guard = RiskGuard(max_daily_loss=100.0)

    assert guard.can_trade() is True


def test_risk_guard_blocks_trade_after_limit():
    guard = RiskGuard(max_daily_loss=100.0)

    guard.record_loss(100.0)

    assert guard.can_trade() is False


def test_risk_guard_blocks_trade_above_limit():
    guard = RiskGuard(max_daily_loss=100.0)

    guard.record_loss(150.0)

    assert guard.can_trade() is False


def test_risk_guard_records_multiple_losses():
    guard = RiskGuard(max_daily_loss=100.0)

    guard.record_loss(30.0)
    guard.record_loss(40.0)
    guard.record_loss(30.0)

    assert guard.daily_loss == 100.0
    assert guard.can_trade() is False


def test_risk_guard_profit_does_not_increase_loss():
    guard = RiskGuard(max_daily_loss=100.0)

    guard.record_profit(50.0)

    assert guard.daily_loss == 0.0
    assert guard.can_trade() is True