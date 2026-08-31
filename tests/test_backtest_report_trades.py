from src.backtest.backtest_report import BacktestReport


class FakeRunner:
    def get_summary(self):
        return {
            "symbol": "BTCUSDT",
            "interval": "1m",
            "candles": 10,
            "initial_balance": 1000.0,
            "final_balance": 1010.0,
            "trades": 1,
            "winning_trades": 1,
            "losing_trades": 0,
            "win_rate": 100.0,
            "total_profit": 10.0,
            "max_drawdown": 0.0
        }

    def get_trades(self):
        return [
            {
                "side": "BUY",
                "entry_price": 100.0,
                "exit_price": 110.0,
                "quantity": 1.0,
                "stop_loss": 95.0,
                "take_profit": 110.0,
                "entry_timestamp": 1000,
                "exit_timestamp": 1060,
                "profit": 10.0
            }
        ]


def test_backtest_report_returns_trade_history():
    report = BacktestReport(FakeRunner())

    trades = report.get_trades()

    assert len(trades) == 1
    assert trades[0]["side"] == "BUY"
    assert trades[0]["profit"] == 10.0


def test_backtest_report_formats_trade_history():
    report = BacktestReport(FakeRunner())

    text = report.format_trades()

    assert isinstance(text, str)
    assert "BUY" in text
    assert "100.00" in text
    assert "110.00" in text
    assert "10.00" in text
    assert "1000" in text
    assert "1060" in text
