import pytest
from src.agent.pln_broker import PlnLedger


def test_deposit_fills_shortfall_and_withdrawal_uses_same_ledger(tmp_path, monkeypatch):
    from app.backend import main
    monkeypatch.setattr(main, 'LIVE_STATE_DIR', tmp_path)
    with PlnLedger(tmp_path).transaction() as s:
        s['balance'] = 990
    wallet = main.deposit_user_portfolio(main.PortfolioAmount(amount=25))
    assert wallet['balance'] == 15
    assert wallet['topups'] == 10
    with PlnLedger(tmp_path).transaction() as s:
        assert s['balance'] == 1000
    assert main.withdraw_user_portfolio(main.PortfolioAmount(amount=5))['balance'] == 10
    with pytest.raises(main.HTTPException):
        main.withdraw_user_portfolio(main.PortfolioAmount(amount=11))
    assert main.user_portfolio_state()['balance'] == 10
