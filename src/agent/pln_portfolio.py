"""PLN valuation and protected virtual trading balance."""
from dataclasses import dataclass


@dataclass
class PlnPortfolio:
    target: float = 1000.0
    available: float = 1000.0
    user_reserve: float = 0.0

    def settle(self, result_pln: float) -> float:
        """Apply a virtual result and transfer surplus/shortfall safely."""
        self.available += result_pln
        if self.available > self.target:
            surplus = self.available - self.target
            self.user_reserve += surplus
            self.available = self.target
            return surplus
        if self.available < self.target:
            needed = self.target - self.available
            transfer = min(needed, self.user_reserve)
            self.user_reserve -= transfer
            self.available += transfer
            return -transfer
        return 0.0

    @staticmethod
    def to_pln(value: float, quote: str, rates: dict[str, float]) -> float:
        if quote == 'PLN':
            return value
        rate = rates.get(f'{quote}PLN')
        if rate is None or rate <= 0:
            raise ValueError(f'Brak kursu {quote}/PLN')
        return value * rate
