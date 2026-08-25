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