from dataclasses import dataclass


@dataclass
class AgentConfig:
    symbol: str = "BTCUSDT"
    interval: str = "1m"
    limit: int = 100

    risk_percent: float = 5.0
    stop_loss_percent: float = 5.0
    max_daily_loss_percent: float = 10.0
    max_exposure_percent: float = 100.0

    risk_reward_ratio: float = 2.0

    initial_balance: float = 1000.0

    buy_rsi: float = 33.8
    sell_rsi: float = 68.5
    min_difference: float = 1.0

    trading_fee: float = 0.0
    rsi_method: str = "classic"

    max_position_candles: int = 241
