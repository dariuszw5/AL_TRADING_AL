from src.data.candle import Candle


class DataManager:
    def __init__(self):
        self.data = []

    def add_data(self, candle: Candle):
        if not isinstance(candle, Candle):
            raise TypeError("DataManager accepts only Candle objects")

        self.data.append(candle)

    def get_data(self):
        return self.data

    def get_latest(self):
        if not self.data:
            return None

        return self.data[-1]

    def get_all(self):
        return self.data