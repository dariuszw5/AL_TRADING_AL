from time import sleep

from src.agent.agent_config import AgentConfig
from src.agent.agent_loop import AgentLoop


STATE_FILE = "data/live_state/paper_live_BTCUSDT_1m.json"

config = AgentConfig(
    symbol="BTCUSDT",
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
    min_difference=1.0,
    trading_fee=0.0004,
    rsi_method="classic",
    max_position_candles=241,
)

loop = AgentLoop(
    config=config,
    state_file=STATE_FILE,
)

print()
print("=" * 100)
print("AL TRADING AGENT | PAPER-LIVE")
print("=" * 100)

print()
print("CONFIG")
print("-" * 100)
print(f"Symbol:                 {config.symbol}")
print(f"Interval:               {config.interval}")
print(f"BUY RSI:                {config.buy_rsi}")
print(f"SELL RSI:               {config.sell_rsi}")
print(f"MAX POSITION CANDLES:   {config.max_position_candles}")
print(f"MIN DIFFERENCE:         {config.min_difference}")
print(f"TRADING FEE:            {config.trading_fee}")
print(f"RSI METHOD:             {config.rsi_method}")
print(f"INITIAL BALANCE:        {config.initial_balance}")
print(f"STATE FILE:             {STATE_FILE}")

print()
print("MODE")
print("-" * 100)
print("PAPER-LIVE ONLY")
print("NO REAL ORDERS")
print("NO EXCHANGE ORDERS")
print("STATE PERSISTENCE ENABLED")

print()
print("=" * 100)
print("WAITING FOR NEXT CLOSED CANDLE...")
print("=" * 100)

while True:
    result = loop.run_live_once()

    status = result.get("status")
    signal = result.get("signal")
    timestamp = result.get("timestamp")
    position = result.get("position")

    print()
    print("=" * 100)
    print("PAPER-LIVE CYCLE")
    print("=" * 100)
    print(f"Status:                 {status}")
    print(f"Timestamp:              {timestamp}")
    print(f"Signal:                 {signal}")
    print(f"Position:               {position}")

    if status == "API_ERROR":
        print(f"API error:              {result.get('error')}")

    if status == "PROCESSED":
        print("State saved:            YES")

    print("-" * 100)
    print("Last processed:         "
          f"{loop.last_processed_timestamp}")
    print("Agent balance:           "
          f"{loop.agent.balance:.8f}")
    print("Peak balance:            "
          f"{loop.agent.peak_balance:.8f}")
    print("Max drawdown:            "
          f"{loop.agent.max_drawdown:.8f}")
    print("Position candles:        "
          f"{loop.agent.position_candles}")

    trades = loop.agent.trading_engine.trade_manager.trade_history

    print("Closed trades:           "
          f"{len(trades)}")

    if trades:
        print("Last trade:")
        print(trades[-1])

    print("=" * 100)

    sleep(5)
