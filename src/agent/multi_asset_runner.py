from pathlib import Path
import os

from src.agent.agent_config import AgentConfig
from src.agent.agent_loop import AgentLoop
from src.data.assets import SUPPORTED_ASSETS, AssetSpec


class MultiAssetPaperLive:
    """Run one isolated paper agent per configured asset."""

    def __init__(self, state_directory=None, assets=None):
        self.state_directory = Path(
            state_directory or os.getenv("AL_TRADING_DATA_DIR", "data/live_state")
        )
        self.state_directory.mkdir(parents=True, exist_ok=True)

        self.assets = tuple(assets or SUPPORTED_ASSETS)
        self.loops = {
            asset.symbol: AgentLoop(
                config=self._config_for(asset),
                state_file=self.state_directory
                / f"paper_live_{asset.symbol}_1m.json",
            )
            for asset in self.assets
        }

    @staticmethod
    def _config_for(asset: AssetSpec) -> AgentConfig:
        return AgentConfig(
            symbol=asset.symbol,
            interval="1m",
            limit=100,
            risk_percent=5.0,
            stop_loss_percent=5.0,
            max_daily_loss_percent=10.0,
            max_exposure_percent=100.0,
            risk_reward_ratio=2.0,
            initial_balance=1000.0,
            buy_rsi=33.8,
            sell_rsi=68.5,
            min_difference=asset.min_difference,
            trading_fee=0.0004,
            rsi_method="classic",
            max_position_candles=241,
        )

    def run_once(self):
        results = {}
        for asset in self.assets:
            results[asset.symbol] = self.loops[asset.symbol].run_live_once()
        return results
