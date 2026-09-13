from pathlib import Path

from src.agent.agent_loop import AgentLoop
from src.agent.agent_config import AgentConfig


STATE_FILE = Path(
    "data/live_state/test_history_risk_restart.json"
)


def main():
    print("=" * 100)
    print("=== TRADE HISTORY + RISK GUARD RESTART AUDIT ===")
    print("=" * 100)

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.unlink(missing_ok=True)

    config = AgentConfig()

    # ============================================================
    # PROCESS 1
    # ============================================================

    loop1 = AgentLoop(
        config=config,
        state_file=str(STATE_FILE)
    )

    # Simulate a closed losing trade.
    trade = {
        "side": "BUY",
        "entry_price": 100000.0,
        "exit_price": 99000.0,
        "quantity": 0.01,
        "stop_loss": 99000.0,
        "take_profit": 102000.0,
        "entry_timestamp": 100,
        "exit_timestamp": 200,
        "profit": -10.0,
        "exit_reason": "STOP_LOSS",
    }

    loop1.agent.trade_history.add_trade(trade)

    loop1.agent.risk_guard.record_loss(
        amount=10.0,
        timestamp=200
    )

    loop1._save_state()

    history_before = list(
        loop1.agent.trade_history.get_trades()
    )

    risk_before = {
        "max_daily_loss":
            loop1.agent.risk_guard.max_daily_loss,
        "daily_loss":
            loop1.agent.risk_guard.daily_loss,
        "current_day":
            loop1.agent.risk_guard.current_day,
    }

    print(
        "TRADE HISTORY CREATED              "
        + ("PASS" if len(history_before) == 1 else "FAIL")
    )

    print(
        "RISK LOSS RECORDED                  "
        + (
            "PASS"
            if loop1.agent.risk_guard.daily_loss == 10.0
            else "FAIL"
        )
    )

    # ============================================================
    # PROCESS RESTART
    # ============================================================

    del loop1

    loop2 = AgentLoop(
        config=config,
        state_file=str(STATE_FILE)
    )

    history_after = list(
        loop2.agent.trade_history.get_trades()
    )

    risk_after = {
        "max_daily_loss":
            loop2.agent.risk_guard.max_daily_loss,
        "daily_loss":
            loop2.agent.risk_guard.daily_loss,
        "current_day":
            loop2.agent.risk_guard.current_day,
    }

    print(
        "TRADE HISTORY AFTER RESTART        "
        + (
            "PASS"
            if history_after == history_before
            else "FAIL"
        )
    )

    print(
        "RISK STATE AFTER RESTART            "
        + (
            "PASS"
            if risk_after == risk_before
            else "FAIL"
        )
    )

    print()
    print("STATE BEFORE RESTART:")
    print(risk_before)
    print()

    print("STATE AFTER RESTART:")
    print(risk_after)
    print()

    print("TRADE HISTORY BEFORE RESTART:")
    print(history_before)
    print()

    print("TRADE HISTORY AFTER RESTART:")
    print(history_after)

    STATE_FILE.unlink(missing_ok=True)

    print("-" * 100)
    print(
        "RESULT: DIAGNOSTIC COMPLETE - "
        "CURRENT PERSISTENCE COVERAGE IDENTIFIED"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()
