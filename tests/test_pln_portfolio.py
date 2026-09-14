import pytest
from src.agent.pln_portfolio import PlnPortfolio


def test_profit_is_swept_to_user_reserve():
    wallet = PlnPortfolio(user_reserve=0)
    assert wallet.settle(25) == 25
    assert wallet.available == 1000
    assert wallet.user_reserve == 25


def test_loss_is_topped_up_from_user_reserve():
    wallet = PlnPortfolio(user_reserve=100)
    assert wallet.settle(-40) == -40
    assert wallet.available == 1000
    assert wallet.user_reserve == 60


def test_fx_conversion_requires_current_rate():
    assert PlnPortfolio.to_pln(10, 'USD', {'USDPLN': 4.0}) == 40
    with pytest.raises(ValueError):
        PlnPortfolio.to_pln(10, 'EUR', {})
