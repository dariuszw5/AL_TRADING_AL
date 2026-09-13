from pathlib import Path

from src.agent.agent_loop import AgentLoop
from src.agent.agent_config import AgentConfig


def main():
    state_file = Path(
        "data/live_state/test_restart_open_position.json"
    )

    if state_file.exists():
        state_file.unlink()

    config = AgentConfig()

    print("=" * 100)
    print("=== LIVE PROCESS RESTART WITH OPEN POSITION - PERSISTENCE AUDIT ===")
    print("=" * 100)

    # PROCESS 1
    loop1 = AgentLoop(
        config=config,
        state_file=str(state_file)
    )

    trade_manager = loop1.agent.trading_engine.trade_manager

    position = {
        "side": "BUY",
        "entry_price": 100000.0,
        "quantity": 0.01,
        "stop_loss": 95000.0,
        "take_profit": 110000.0,
        "entry_timestamp": 1788162840000,
    }

    trade_manager.position = position
    loop1.agent.position_candles = 137
    loop1.last_processed_timestamp = 1788162900000
    loop1.agent.balance = 987.50
    loop1.agent.peak_balance = 1005.0
    loop1.agent.max_drawdown = 17.5
    loop1.agent.market_price = 100500.0
    loop1.agent.equity_curve = [1000.0, 995.0, 987.5]

    loop1._save_state()

    assert state_file.exists()
    print("STATE FILE CREATED                     PASS")

    del loop1

    # PROCESS 2
    loop2 = AgentLoop(
        config=config,
        state_file=str(state_file)
    )

    recovered = loop2.agent.trading_engine.trade_manager.position

    if recovered == position:
        print("POSITION RECOVERED                    PASS")
    else:
        print("POSITION RECOVERED                    FAIL")

    if loop2.agent.position_candles == 137:
        print("POSITION CANDLES RECOVERED            PASS")
    else:
        print("POSITION CANDLES RECOVERED            FAIL")

    if loop2.last_processed_timestamp == 1788162900000:
        print("TIMESTAMP RECOVERED                   PASS")
    else:
        print("TIMESTAMP RECOVERED                   FAIL")

    if loop2.agent.balance == 987.50:
        print("BALANCE RECOVERED                     PASS")
    else:
        print("BALANCE RECOVERED                     FAIL")

    if loop2.agent.peak_balance == 1005.0:
        print("PEAK BALANCE RECOVERED                PASS")
    else:
        print("PEAK BALANCE RECOVERED                FAIL")

    if loop2.agent.max_drawdown == 17.5:
        print("MAX DRAWDOWN RECOVERED                PASS")
    else:
        print("MAX DRAWDOWN RECOVERED                FAIL")

    if loop2.agent.market_price == 100500.0:
        print("MARKET PRICE RECOVERED                PASS")
    else:
        print("MARKET PRICE RECOVERED                FAIL")

    if loop2.agent.equity_curve == [1000.0, 995.0, 987.5]:
        print("EQUITY CURVE RECOVERED                PASS")
    else:
        print("EQUITY CURVE RECOVERED                FAIL")

    # Ensure the state cannot cause a duplicate entry.
    if loop2.agent.trading_engine.trade_manager.position is not None:
        print("NO DUPLICATE ENTRY STATE              PASS")
    else:
        print("NO DUPLICATE ENTRY STATE              FAIL")

    # Simulate restart again and verify deterministic persistence.
    loop2._save_state()
    del loop2

    loop3 = AgentLoop(
        config=config,
        state_file=str(state_file)
    )

    if loop3.agent.trading_engine.trade_manager.position == position:
        print("SECOND RESTART POSITION               PASS")
    else:
        print("SECOND RESTART POSITION               FAIL")

    if loop3.agent.position_candles == 137:
        print("SECOND RESTART TIME STATE             PASS")
    else:
        print("SECOND RESTART TIME STATE             FAIL")

    if loop3.last_processed_timestamp == 1788162900000:
        print("SECOND RESTART TIMESTAMP              PASS")
    else:
        print("SECOND RESTART TIMESTAMP              FAIL")

    state_file.unlink()

    print("-" * 100)

    print("RESULT: RESTART PERSISTENCE AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()
