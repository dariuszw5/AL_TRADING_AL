import csv

from src.data.candle import Candle


class HistoricalData:
    def __init__(self):
        self.candles = []

    def load_csv(self, file_path):
        candles = []

        with open(
            file_path,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                candle = Candle(
                    timestamp=int(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"])
                )

                candles.append(candle)

        self.candles = candles

        return candles

    def save_csv(self, file_path, candles=None):
        if candles is None:
            candles = self.candles

        with open(
            file_path,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:
            writer = csv.writer(file)

            writer.writerow([
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume"
            ])

            for candle in candles:
                writer.writerow([
                    candle.timestamp,
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                    candle.volume
                ])

        self.candles = list(candles)

    def get_candles(self):
        return self.candles

    def count(self):
        return len(self.candles)