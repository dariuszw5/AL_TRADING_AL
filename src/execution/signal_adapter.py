from __future__ import annotations

from src.agent.agent_config import (
    AgentConfig,
)
from src.agent.agent_engine import (
    AgentEngine,
)


class RealisticSignalAdapter:
    """
    Reuse the frozen analytical/signal path without
    using legacy execution.

    Only AgentEngine.analyze(candles) is called.

    AgentEngine.run(), run_cycle(), execute_trade()
    and TradingEngine are never called by this
    adapter.
    """

    VALID_SIGNALS = frozenset(
        {
            "BUY",
            "SELL",
            "HOLD",
        }
    )

    def __init__(
        self,
        *,
        config: AgentConfig | None = None,
        analysis_engine=None,
    ):
        if (
            config is not None
            and analysis_engine is not None
        ):
            raise ValueError(
                "Provide config or analysis_engine, "
                "not both"
            )

        if analysis_engine is None:
            config = (
                config
                or AgentConfig()
            )

            analysis_engine = (
                AgentEngine(
                    config=config
                )
            )

        self.analysis_engine = (
            analysis_engine
        )

    def signal_from_candles(
        self,
        candles,
    ) -> str:
        if not candles:
            return "HOLD"

        analysis = (
            self.analysis_engine
            .analyze(candles)
        )

        if not isinstance(
            analysis,
            dict,
        ):
            raise TypeError(
                "analysis must be a dict"
            )

        signal = analysis.get(
            "signal",
            "HOLD",
        )

        signal = str(
            signal
        ).upper()

        if (
            signal
            not in self.VALID_SIGNALS
        ):
            raise ValueError(
                "Unsupported strategy signal: "
                f"{signal}"
            )

        return signal
