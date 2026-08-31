from src.analysis.market_analyzer import MarketAnalyzer
from src.strategy.basic_strategy import BasicStrategy
from src.risk.risk_manager import RiskManager
from src.risk.risk_levels import RiskLevels


class StrategyEngine:
    def __init__(
        self,
        initial_balance=1000.0,
        buy_rsi=30.0,
        sell_rsi=70.0,
        min_difference=1.0,
        rsi_method="classic"
    ):
        self.analyzer = MarketAnalyzer(
            rsi_method=rsi_method
        )
        self.strategy = BasicStrategy()
        self.risk_manager = RiskManager()
        self.risk_levels = RiskLevels()
        self.initial_balance = initial_balance
        self.buy_rsi = buy_rsi
        self.sell_rsi = sell_rsi
        self.min_difference = min_difference
        self.rsi_method = rsi_method

    def run(self):
        analysis = self.analyzer.analyze()

        sma_values = analysis["sma"]
        ema_values = analysis["ema"]
        rsi_values = analysis["rsi"]

        if not sma_values or not ema_values or not rsi_values:
            return "HOLD"

        sma_value = sma_values[-1]
        ema_value = ema_values[-1]
        rsi_value = rsi_values[-1]

        previous_ema = None

        if len(ema_values) >= 2:
            previous_ema = ema_values[-2]

        return self.strategy.generate_signal(
            sma_value=sma_value,
            ema_value=ema_value,
            rsi_value=rsi_value,
            min_difference=self.min_difference,
            buy_rsi=self.buy_rsi,
            sell_rsi=self.sell_rsi,
            previous_ema=previous_ema
        )

    def generate_signals(self, analyzed_data):
        sma_values = analyzed_data["sma"]
        ema_values = analyzed_data["ema"]
        rsi_values = analyzed_data["rsi"]

        signals = []

        length = min(
            len(sma_values),
            len(ema_values),
            len(rsi_values)
        )

        for i in range(length):
            previous_ema = None

            if i > 0:
                previous_ema = ema_values[i - 1]

            signal = self.strategy.generate_signal(
                sma_value=sma_values[i],
                ema_value=ema_values[i],
                rsi_value=rsi_values[i],
                min_difference=self.min_difference,
                buy_rsi=self.buy_rsi,
                sell_rsi=self.sell_rsi,
                previous_ema=previous_ema
            )

            signals.append((signal, 0.0))

        return signals

    def generate_trade_setup(
        self,
        signal,
        entry_price,
        risk_percent,
        risk_reward_ratio,
        balance=None
    ):
        if signal not in ("BUY", "SELL"):
            return None

        stop_loss = self.risk_levels.calculate_stop_loss(
            entry_price=entry_price,
            risk_percent=risk_percent,
            side=signal
        )

        take_profit = self.risk_levels.calculate_take_profit(
            entry_price=entry_price,
            stop_loss=stop_loss,
            risk_reward_ratio=risk_reward_ratio,
            side=signal
        )

        if balance is None:
            balance = self.initial_balance

        position_size = self.risk_manager.calculate_position_size(
            balance=balance,
            risk_percent=risk_percent,
            entry_price=entry_price,
            stop_loss=stop_loss
        )

        return {
            "signal": signal,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "position_size": position_size,
            "risk_percent": risk_percent,
            "risk_reward_ratio": risk_reward_ratio
        }