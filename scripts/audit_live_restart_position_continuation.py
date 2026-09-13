from pathlib import Path

from src.agent.agent_loop import AgentLoop
from src.agent.agent_config import AgentConfig


STATE_FILE = Path(
    "data/live_state/test_restart_position_continuation.json"
)


def check(label, condition):
    print(
        f"{label:<36}"
        + ("PASS" if condition else "FAIL")
    )
    return condition


def main():
    print("=" * 100)
    print("=== LIVE RESTART -> POSITION -> CONTINUATION AUDIT ===")
    print("=" * 100)

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.unlink(missing_ok=True)

    config = AgentConfig()

    # ============================================================
    # PROCESS 1 - create and persist open position
    # ============================================================

    loop1 = AgentLoop(
        config=config,
        state_file=str(STATE_FILE)
    )

    manager1 = loop1.agent.trading_engine.trade_manager

    position = manager1.open_position(
        side="BUY",
        entry_price=100000.0,
        quantity=0.01,
        stop_loss=99000.0,
        take_profit=101000.0,
        entry_timestamp=100
    )

    loop1.last_processed_timestamp = 200
    loop1.agent.position_candles = 137
    loop1.agent.balance = 1000.0
    loop1.agent.peak_balance = 1005.0
    loop1.agent.max_drawdown = 5.0
    loop1.agent.market_price = 100500.0
    loop1.agent.equity_curve = [1000.0, 1005.0]

    loop1._save_state()

    check(
        "OPEN POSITION CREATED",
        position is not None
    )

    check(
        "STATE FILE CREATED",
        STATE_FILE.exists()
    )

    # ============================================================
    # PROCESS 2 - restart
    # ============================================================

    del loop1

    loop2 = AgentLoop(
        config=config,
        state_file=str(STATE_FILE)
    )

    restored = (
        loop2.agent.trading_engine.trade_manager.position
    )

    position_recovered = check(
        "POSITION RECOVERED",
        restored is not None
    )

    position_identical = check(
        "POSITION IDENTICAL",
        restored is not None
        and restored["side"] == "BUY"
        and restored["entry_price"] == 100000.0
        and restored["quantity"] == 0.01
        and restored["stop_loss"] == 99000.0
        and restored["take_profit"] == 101000.0
        and restored["entry_timestamp"] == 100
    )

    timestamp_recovered = check(
        "TIMESTAMP RECOVERED",
        loop2.last_processed_timestamp == 200
    )

    candles_recovered = check(
        "POSITION CANDLES RECOVERED",
        loop2.agent.position_candles == 137
    )

    # ============================================================
    # NEXT CANDLE - take profit
    # ============================================================

    result = loop2.agent.trading_engine.check_candle(
        high=101000.0,
        low=100200.0,
        close=100900.0,
        timestamp=201
    )

    candle_processed = check(
        "NEXT CANDLE PROCESSED",
        result is not None
    )

    position_closed = check(
        "POSITION CLOSED",
        loop2.agent.trading_engine.trade_manager.position is None
    )

    take_profit = check(
        "EXIT REASON TAKE_PROFIT",
        result is not None
        and result.get("exit_reason") == "TAKE_PROFIT"
    )

    exit_timestamp = check(
        "EXIT TIMESTAMP RECORDED",
        result is not None
        and result.get("exit_timestamp") == 201
    )

    history_updated = check(
        "TRADE HISTORY UPDATED",
        len(
            loop2.agent.trading_engine.trade_manager.trade_history
        ) == 1
    )

    # Save the flat state before the second restart.
    loop2._save_state()

    # Capture everything needed before deleting loop2.
    second_restart_expected_timestamp = (
        loop2.last_processed_timestamp
    )

    second_restart_expected_flat = (
        loop2.agent.trading_engine.trade_manager.position
        is None
    )

    del loop2

    # ============================================================
    # PROCESS 3 - restart after position was closed
    # ============================================================

    loop3 = AgentLoop(
        config=config,
        state_file=str(STATE_FILE)
    )

    restored_after_close = (
        loop3.agent.trading_engine.trade_manager.position
    )

    second_restart_flat = check(
        "SECOND RESTART FLAT STATE",
        restored_after_close is None
        and second_restart_expected_flat
    )

    second_restart_timestamp = check(
        "SECOND RESTART TIMESTAMP",
        loop3.last_processed_timestamp
        == second_restart_expected_timestamp
    )

    # ============================================================
    # RESULT
    # ============================================================

    all_ok = all([
        position is not None,
        STATE_FILE is not None,
        position_recovered,
        position_identical,
        timestamp_recovered,
        candles_recovered,
        candle_processed,
        position_closed,
        take_profit,
        exit_timestamp,
        history_updated,
        second_restart_flat,
        second_restart_timestamp,
    ])

    STATE_FILE.unlink(missing_ok=True)

    print("-" * 100)

    if all_ok:
        print(
            "RESULT: PASS - RESTARTED POSITION CONTINUED AND CLOSED CORRECTLY"
        )
    else:
        print("RESULT: FAIL")

    print("=" * 100)

    if not all_ok:
        raise AssertionError(
            "Restart position continuation audit failed."
        )


if __name__ == "__main__":
    main()
