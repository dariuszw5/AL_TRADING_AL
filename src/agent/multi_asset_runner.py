from pathlib import Path

from src.agent.agent_config import AgentConfig
from src.agent.agent_loop import AgentLoop
from src.data.assets import (
    AssetConfig,
    SUPPORTED_ASSETS,
)


class MultiAssetPaperLive:
    """Run one isolated paper agent per asset config."""

    def __init__(
        self,
        state_directory=None,
        assets=None,
    ):
        self.state_directory = Path(
            state_directory or "data/live_state"
        )

        self.state_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.assets = tuple(
            assets or SUPPORTED_ASSETS
        )

        self.loops = {
            asset.asset_id: AgentLoop(
                config=self._config_for(
                    asset
                ),
                state_file=(
                    self.state_directory
                    / (
                        "paper_live_"
                        f"{asset.state_key}_"
                        f"{asset.interval}.json"
                    )
                ),
            )
            for asset in self.assets
        }

    @staticmethod
    def _config_for(
        asset: AssetConfig,
    ) -> AgentConfig:
        strategy = asset.strategy
        risk = asset.risk
        execution = asset.execution

        return AgentConfig(
            symbol=asset.asset_id,
            interval=asset.interval,
            limit=100,
            risk_percent=risk.risk_percent,
            stop_loss_percent=(
                risk.stop_loss_percent
            ),
            max_daily_loss_percent=(
                risk.max_daily_loss_percent
            ),
            max_exposure_percent=(
                risk.max_exposure_percent
            ),
            risk_reward_ratio=(
                risk.risk_reward_ratio
            ),
            initial_balance=(
                risk.initial_balance
            ),
            buy_rsi=strategy.buy_rsi,
            sell_rsi=strategy.sell_rsi,
            min_difference=(
                strategy.min_difference
            ),
            trading_fee=(
                execution.trading_fee
            ),
            rsi_method=(
                strategy.rsi_method
            ),
            max_position_candles=(
                execution.max_position_candles
            ),
        )

    def run_once(self):
        results = {}

        for asset in self.assets:
            loop = self.loops[
                asset.asset_id
            ]

            results[
                asset.asset_id
            ] = loop.run_live_once()

        return results
