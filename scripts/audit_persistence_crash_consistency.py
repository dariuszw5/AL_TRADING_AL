from pathlib import Path
from src.agent.agent_loop import AgentLoop
from src.agent.agent_config import AgentConfig


print("=" * 100)
print("=== LIVE PERSISTENCE CRASH-CONSISTENCY + TRADEMANAGER HISTORY AUDIT ===")
print("=" * 100)

# ---------------------------------------------------------------------------
# 1. Inspect runtime history ownership
# ---------------------------------------------------------------------------

config = AgentConfig()
loop = AgentLoop(config=config, state_file=None)

engine_history = loop.agent.trade_history.get_trades()
manager_history = loop.agent.trading_engine.trade_manager.trade_history

print(f"AgentEngine trade history type : {type(engine_history).__name__}")
print(f"TradeManager trade history type: {type(manager_history).__name__}")
print(f"Same history object             : {engine_history is manager_history}")

# ---------------------------------------------------------------------------
# 2. Create a known completed trade in BOTH histories through normal engine
# ---------------------------------------------------------------------------

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

loop.agent.trade_history.add_trade(dict(trade))
loop.agent.trading_engine.trade_manager.trade_history.append(dict(trade))

print(f"AgentEngine history before restart : {len(loop.agent.trade_history.get_trades())}")
print(f"TradeManager history before restart: {len(loop.agent.trading_engine.trade_manager.trade_history)}")

# ---------------------------------------------------------------------------
# 3. Persist
# ---------------------------------------------------------------------------

state_path = Path("data/live_state/audit_history_runtime.json")

if state_path.exists():
    state_path.unlink()

persisted_loop = AgentLoop(config=config, state_file=str(state_path))
persisted_loop.agent.trade_history.add_trade(dict(trade))
persisted_loop.agent.trading_engine.trade_manager.trade_history.append(dict(trade))
persisted_loop._save_state()

print(f"STATE FILE CREATED                 : {'PASS' if state_path.exists() else 'FAIL'}")

# ---------------------------------------------------------------------------
# 4. Restart
# ---------------------------------------------------------------------------

restored = AgentLoop(config=config, state_file=str(state_path))

restored_agent_history = restored.agent.trade_history.get_trades()
restored_manager_history = restored.agent.trading_engine.trade_manager.trade_history

print(f"AgentEngine history after restart : {len(restored_agent_history)}")
print(f"TradeManager history after restart: {len(restored_manager_history)}")

agent_history_ok = restored_agent_history == [trade]
manager_history_ok = restored_manager_history == [trade]

print(f"AGENTENGINE HISTORY RECOVERED     : {'PASS' if agent_history_ok else 'FAIL'}")
print(f"TRADEMANAGER HISTORY RECOVERED    : {'PASS' if manager_history_ok else 'FAIL'}")

# ---------------------------------------------------------------------------
# 5. Crash-consistency simulation
#
# Persist a valid state, mutate runtime state, then simulate process crash
# BEFORE _save_state(). Restart and verify persisted state is unchanged.
# ---------------------------------------------------------------------------

crash_path = Path("data/live_state/audit_crash_consistency.json")

if crash_path.exists():
    crash_path.unlink()

crash_loop = AgentLoop(config=config, state_file=str(crash_path))

crash_loop.agent.balance = 1000.0
crash_loop.agent.peak_balance = 1000.0
crash_loop.agent.market_price = 100000.0
crash_loop.last_processed_timestamp = 1234567890000

crash_loop._save_state()

valid_state = crash_loop.state_store.load()

# Runtime mutations that represent a completed cycle which has NOT yet
# reached _save_state().
crash_loop.agent.balance = 987.65
crash_loop.agent.peak_balance = 1005.0
crash_loop.agent.market_price = 99000.0
crash_loop.last_processed_timestamp = 1234567950000

# Deliberately do NOT call _save_state().
# This simulates a process crash between run_cycle() and persistence.

restored_after_crash = AgentLoop(
    config=config,
    state_file=str(crash_path)
)

restored_state = restored_after_crash.state_store.load()

balance_ok = restored_after_crash.agent.balance == valid_state["balance"]
peak_ok = restored_after_crash.agent.peak_balance == valid_state["peak_balance"]
price_ok = restored_after_crash.agent.market_price == valid_state["market_price"]
timestamp_ok = (
    restored_after_crash.last_processed_timestamp
    == valid_state["last_processed_timestamp"]
)

print(f"PERSISTED STATE SURVIVES PRE-SAVE CRASH : {'PASS' if balance_ok and peak_ok and price_ok and timestamp_ok else 'FAIL'}")
print(f"BALANCE ROLLBACK TO LAST SAVE          : {'PASS' if balance_ok else 'FAIL'}")
print(f"PEAK BALANCE ROLLBACK                  : {'PASS' if peak_ok else 'FAIL'}")
print(f"MARKET PRICE ROLLBACK                  : {'PASS' if price_ok else 'FAIL'}")
print(f"TIMESTAMP ROLLBACK                     : {'PASS' if timestamp_ok else 'FAIL'}")

# ---------------------------------------------------------------------------
# 6. Cleanup
# ---------------------------------------------------------------------------

if state_path.exists():
    state_path.unlink()

if crash_path.exists():
    crash_path.unlink()

tmp_path = crash_path.with_suffix(".tmp")
if tmp_path.exists():
    tmp_path.unlink()

print("-" * 100)

all_pass = (
    state_path.exists() is False
    and crash_path.exists() is False
    and agent_history_ok
    and manager_history_ok
    and balance_ok
    and peak_ok
    and price_ok
    and timestamp_ok
)

print(
    "RESULT: PASS - PERSISTENCE CRASH-CONSISTENCY VERIFIED"
    if all_pass
    else
    "RESULT: REVIEW REQUIRED - PERSISTENCE GAP DETECTED"
)

print("=" * 100)
