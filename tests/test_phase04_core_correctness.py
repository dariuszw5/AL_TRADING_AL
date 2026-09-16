from copy import deepcopy
from pathlib import Path

import pytest

from src.agent.agent_config import AgentConfig
from src.agent.agent_loop import AgentLoop
from src.agent.multi_asset_runner import MultiAssetPaperLive
from src.agent import ai_manager as ai
from src.backtest.backtest_engine import BacktestEngine
from src.backtest.backtest_runner import BacktestRunner
from src.data.assets import SUPPORTED_ASSETS
from src.data.candle import Candle


# ---------------------------------------------------------------------------
# PHASE 04 CONTRACT
#
# Reproduction first:
# - RED  -> bug confirmed, fix allowed
# - GREEN -> behavior must not be changed
#
# These tests intentionally describe the REQUIRED correct behavior.
# ---------------------------------------------------------------------------


FROZEN_BTC_FILE = "data/backtest/BTCUSDT_1m_5000.json"


def _candles(
    count=600,
    step=0.0003,
    start=1_700_000_040_000,
):
    result = []
    price = 100.0

    for i in range(count):
        value = price * (1 + step)

        result.append(
            Candle(
                timestamp=start + i * ai.MINUTE,
                open=price,
                high=max(price, value) * 1.0001,
                low=min(price, value) * 0.9999,
                close=value,
                volume=10.0,
            )
        )

        price = value

    return result


def _now(bars):
    return bars[-1].timestamp + ai.MINUTE


# ===========================================================================
# 1. REPEATED BACKTEST STATE LEAKAGE
# ===========================================================================


def test_phase04_repeated_backtest_same_runner_is_deterministic():
    """
    Running the same BacktestRunner twice on the same frozen input must produce
    exactly the same observable result.

    A second run must behave like a fresh run, not continue AgentEngine state
    left by the first backtest.
    """

    assert Path(FROZEN_BTC_FILE).exists()

    runner = BacktestRunner(
        symbol="BTCUSDT",
        interval="1m",
        limit=5000,
        initial_balance=1000.0,
        buy_rsi=33.8,
        sell_rsi=68.5,
        min_difference=1.0,
        trading_fee=0.0004,
        rsi_method="classic",
        risk_percent=5.0,
        max_daily_loss_percent=10.0,
        risk_reward_ratio=2.0,
        data_source="file",
        data_file=FROZEN_BTC_FILE,
    )

    runner.run()

    first_summary = deepcopy(runner.get_summary())
    first_trades = deepcopy(runner.get_trades())

    runner.run()

    second_summary = deepcopy(runner.get_summary())
    second_trades = deepcopy(runner.get_trades())

    assert second_summary == first_summary
    assert second_trades == first_trades


# ===========================================================================
# 2. CROSS-ASSET STATE LEAKAGE
# ===========================================================================


def test_phase04_multi_asset_agents_do_not_share_mutable_state(tmp_path):
    """
    BTC and ETH must have independent agents, trade managers, risk guards,
    balances, positions and histories.
    """

    runner = MultiAssetPaperLive(
        state_directory=tmp_path,
        assets=SUPPORTED_ASSETS[:2],
    )

    btc = runner.loops["BTCUSDT"]
    eth = runner.loops["ETHUSDT"]

    assert btc is not eth
    assert btc.agent is not eth.agent

    assert (
        btc.agent.trading_engine.trade_manager
        is not eth.agent.trading_engine.trade_manager
    )

    assert btc.agent.risk_guard is not eth.agent.risk_guard
    assert btc.agent.data_manager is not eth.agent.data_manager

    btc.agent.balance = 777.0
    btc.agent.risk_guard.daily_loss = 12.5

    btc.agent.trading_engine.trade_manager.position = {
        "side": "BUY",
        "entry_price": 100.0,
        "quantity": 1.0,
    }

    btc.agent.trading_engine.trade_manager.trade_history.append(
        {
            "side": "BUY",
            "profit": 5.0,
        }
    )

    assert eth.agent.balance == eth.config.initial_balance
    assert eth.agent.risk_guard.daily_loss == 0.0
    assert eth.agent.trading_engine.trade_manager.position is None
    assert eth.agent.trading_engine.trade_manager.trade_history == []


# ===========================================================================
# 3. AI RANKING MUST BE SORTED AFTER LEARNING BONUS
# ===========================================================================


def test_phase04_ai_ranking_is_resorted_after_learning_bonus(
    tmp_path,
    monkeypatch,
):
    """
    The winning asset must be selected from FINAL score after learning_bonus,
    not from the pre-bonus ordering.
    """

    manager = ai.AIPaperManager(
        tmp_path / "ai.json",
        assets=[],
    )

    manager.state["strategy_learning"]["trend"] = {
        "trades": 3,
        "wins": 1,
        "total_return": 0.0,
    }

    manager.state["strategy_learning"]["breakout"] = {
        "trades": 3,
        "wins": 3,
        "total_return": 0.12,
    }

    def fake_rank(symbol, bars):
        if symbol == "BTCUSDT":
            return [
                {
                    "symbol": "BTCUSDT",
                    "strategy": "trend",
                    "score": 0.020,
                    "eligible": True,
                }
            ]

        if symbol == "ETHUSDT":
            return [
                {
                    "symbol": "ETHUSDT",
                    "strategy": "breakout",
                    "score": 0.015,
                    "eligible": True,
                }
            ]

        return []

    monkeypatch.setattr(ai, "rank_asset", fake_rank)

    bars = _candles()

    state = manager.step(
        {
            "BTCUSDT": bars,
            "ETHUSDT": bars,
        },
        _now(bars),
    )

    # Before bonus:
    # BTC trend     = 0.020
    # ETH breakout  = 0.015
    #
    # breakout online mean = 0.12 / 3 = 0.04
    # bonus = 0.25 * 0.04 = 0.01
    #
    # Final:
    # BTC = 0.020
    # ETH = 0.025  -> must become first.

    assert state["ranking"][0]["symbol"] == "ETHUSDT"
    assert state["ranking"][0]["strategy"] == "breakout"

    assert state["pending"]["symbol"] == "ETHUSDT"
    assert state["pending"]["strategy"] == "breakout"


# ===========================================================================
# 4. AI SIMULATION UNITS MUST NOT CHANGE PLN USER CASH
# ===========================================================================


def test_phase04_ai_simulation_surplus_does_not_credit_pln_portfolio(
    tmp_path,
    monkeypatch,
):
    """
    simulation_units are not PLN.

    A simulated AI gain must never be copied 1:1 into the user's PLN cash
    ledger.
    """

    monkeypatch.chdir(tmp_path)

    manager = ai.AIPaperManager(
        tmp_path / "ai.json",
        assets=[],
    )

    manager.state["balance"] = 1012.5
    manager.state["equity"] = 1012.5

    state = manager.step(
        {},
        _now(_candles()),
    )

    portfolio_path = Path(
        "data/live_state/user_portfolio.json"
    )

    if portfolio_path.exists():
        user = ai.LiveStateStore(portfolio_path).load()

        assert user.get("balance", 0.0) == 0.0
        assert user.get("profit_transferred", 0.0) == 0.0

    assert state["balance"] == pytest.approx(1012.5)
    assert state.get("profit_swept", 0.0) == pytest.approx(0.0)


# ===========================================================================
# 5. PROCESSED TIMESTAMP MUST ADVANCE ONLY AFTER SUCCESS
# ===========================================================================


def test_phase04_processed_timestamp_does_not_advance_on_failed_cycle(
    tmp_path,
    monkeypatch,
):
    """
    If agent.run_cycle fails, the closed candle must remain unprocessed.

    last_processed_timestamp may advance only after a successful cycle and
    successful persistence.
    """

    loop = AgentLoop(
        config=AgentConfig(
            symbol="BTCUSDT",
            interval="1m",
            limit=10,
        ),
        state_file=tmp_path / "state.json",
    )

    bars = [
        Candle(
            timestamp=1_700_000_000_000,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=10.0,
        ),
        Candle(
            timestamp=1_700_000_060_000,
            open=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
            volume=10.0,
        ),
        Candle(
            timestamp=1_700_000_120_000,
            open=101.0,
            high=103.0,
            low=100.0,
            close=102.0,
            volume=10.0,
        ),
    ]

    monkeypatch.setattr(
        loop.data_provider,
        "get_candles",
        lambda **kwargs: bars,
    )

    def fail_cycle(_history):
        raise RuntimeError("simulated processing failure")

    monkeypatch.setattr(
        loop.agent,
        "run_cycle",
        fail_cycle,
    )

    assert loop.last_processed_timestamp is None

    with pytest.raises(
        RuntimeError,
        match="simulated processing failure",
    ):
        loop.run_live_once()

    assert loop.last_processed_timestamp is None

    restored = AgentLoop(
        config=loop.config,
        state_file=tmp_path / "state.json",
    )

    assert restored.last_processed_timestamp is None


# ===========================================================================
# 6. BACKTEST MAX DRAWDOWN MUST INCLUDE MTM EQUITY
# ===========================================================================


def test_phase04_backtest_max_drawdown_includes_mark_to_market_equity():
    """
    Backtest max DD must see intratrade / per-candle MTM equity.

    A closed-trade-only curve must not report zero DD while the agent observed
    a 50-unit MTM drawdown.
    """

    class FakeTradeManager:
        position = None

    class FakeTradingEngine:
        def __init__(self):
            self.trade_manager = FakeTradeManager()

    class FakeMtmAgent:
        def __init__(self):
            self.trading_engine = FakeTradingEngine()

            self.balance = 1000.0
            self.equity_curve = [1000.0]
            self.peak_balance = 1000.0
            self.max_drawdown = 0.0

            self.mtm_values = [
                1000.0,
                950.0,
                975.0,
            ]

        def run_cycle(self, history):
            equity = self.mtm_values[len(history) - 1]

            self.equity_curve.append(equity)

            self.peak_balance = max(
                self.peak_balance,
                equity,
            )

            self.max_drawdown = max(
                self.max_drawdown,
                self.peak_balance - equity,
            )

            return {
                "signal": "HOLD",
                "position": None,
                "result": None,
            }

    agent = FakeMtmAgent()

    engine = BacktestEngine(
        agent=agent,
        initial_balance=1000.0,
        trading_fee=0.0,
    )

    candles = [
        {
            "timestamp": 1,
            "close": 100.0,
        },
        {
            "timestamp": 2,
            "close": 95.0,
        },
        {
            "timestamp": 3,
            "close": 97.5,
        },
    ]

    engine.run(candles)

    assert agent.max_drawdown == pytest.approx(50.0)

    # LEGACY_V1 realized drawdown must remain frozen.
    assert engine.get_max_drawdown() == pytest.approx(0.0)

    # Phase 04 requires a separate full mark-to-market risk metric.
    assert engine.get_mtm_max_drawdown() == pytest.approx(50.0)
