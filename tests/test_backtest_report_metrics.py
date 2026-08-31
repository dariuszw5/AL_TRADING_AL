from src.backtest.backtest_report import BacktestReport


class FakeRunner:

    def get_summary(self):
        return {
            "symbol": "BTCUSDT",
            "interval": "1m",
            "candles": 1000,
            "initial_balance": 1000.0,
            "final_balance": 1015.0,
            "trades": 10,
            "winning_trades": 6,
            "losing_trades": 4,
            "win_rate": 60.0,
            "total_profit": 15.0,
            "max_drawdown": 8.0,
            "profit_factor": 1.5,
            "average_win": 5.0,
            "average_loss": 2.5,
            "largest_win": 10.0,
            "largest_loss": 5.0,
            "expectancy": 1.5
        }

    def get_trades(self):
        return []


def test_backtest_report_contains_advanced_metrics():
    report = BacktestReport(FakeRunner())

    text = report.format()

    assert "Profit Factor" in text
    assert "Average Win" in text
    assert "Average Loss" in text
    assert "Largest Win" in text
    assert "Largest Loss" in text
    assert "Expectancy" in text