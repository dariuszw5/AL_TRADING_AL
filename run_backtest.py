from src.backtest.backtest_runner import BacktestRunner
from src.backtest.backtest_report import BacktestReport


def main():
    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=1000,
        initial_balance=1000.0
    )

    print("Pobieranie danych z Binance...")

    runner.load_data()

    print(
        f"Pobrano {len(runner.candles)} świec."
    )

    print("Uruchamianie backtestu...")

    runner.run()

    report = BacktestReport(runner)

    print()
    report.print_report()


if __name__ == "__main__":
    main()