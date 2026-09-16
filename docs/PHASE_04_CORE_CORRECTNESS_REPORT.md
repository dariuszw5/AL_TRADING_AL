# Phase 04 — Core Correctness Report

Date: 2026-09-16
Branch: `phase-04-core-correctness`

## Scope

Phase 04 verified six suspected correctness defects using the required
reproduction-first RED/GREEN procedure.

No suspected behavior was changed unless its reproduction test failed first.

## Pre-fix reproduction result

Result:

- 2 passed
- 4 failed

### NOT CONFIRMED — no production behavior changed

1. Repeated backtest state leakage
   - Reproduction test: GREEN before fixes.
   - Same runner produced deterministic repeated results.
   - No fix applied.

2. Cross-asset state leakage
   - Reproduction test: GREEN before fixes.
   - Asset loops, agents, trade managers, risk guards and mutable state
     remained isolated.
   - No fix applied.

### CONFIRMED — fixed

3. AI ranking sorted before learning bonus
   - Reproduction test: RED.
   - Ranking was sorted before `learning_bonus` was added.
   - Selection could therefore use stale ordering.
   - Fixed by sorting after final score calculation.

4. AI simulation surplus mutated PLN user cash
   - Reproduction test: RED.
   - `simulation_units` were transferred 1:1 into a ledger labelled PLN.
   - This violated currency/unit separation.
   - HARD STOP approval was explicitly granted by the user.
   - Production sweep was disabled.
   - Existing tests that required the obsolete transfer semantics were updated.
   - Historical state was not migrated or deleted.

5. `last_processed_timestamp` advanced before successful completion
   - Reproduction test: RED.
   - Timestamp advanced before `agent.run_cycle()` and persistence succeeded.
   - Fixed so a failed cycle does not consume the candle.
   - On persistence failure the previous timestamp is restored.

6. Backtest public drawdown lacked a separate full MTM metric
   - Reproduction test: RED.
   - `BacktestResult.get_max_drawdown()` represented LEGACY_V1 realized
     closed-trade equity.
   - HARD STOP approval was explicitly granted by the user.
   - Added separate `get_mtm_max_drawdown()`.
   - Existing LEGACY_V1 `get_max_drawdown()` semantics were preserved.

## Post-fix contract tests

`tests/test_phase04_core_correctness.py`

Result:

- 6 passed

## Offline regression

Known real-provider/network test files were excluded from the offline suite.

Result:

- 341 passed in 66.81s

## BTC LEGACY_V1 golden regression

Frozen dataset:

`data/backtest/BTCUSDT_1m_5000.json`

Configuration remained unchanged:

- BUY RSI: 33.8
- SELL RSI: 68.5
- RSI: classic
- max position candles: 241
- trading fee: 0.0004
- initial balance: 1000.0

Observed benchmark:

- Final balance: 1014.8392976799995
- Trades: 13
- Wins: 7
- Losses: 6
- Win rate: 53.84615384615385%
- Total profit: 14.839297679999504
- LEGACY max drawdown: 18.485012400000187
- Profit factor: 1.692128777090018
- Average win: 5.182768514285695
- Average loss: 3.573346986666712
- Largest win: 13.000798400000047
- Largest loss: 9.580003080000042
- Expectancy: 1.1414844369230388

The LEGACY_V1 benchmark and its realized drawdown semantics were not changed.

## Safety / contract notes

Phase 04 did not:

- change frozen BTC strategy parameters,
- change LEGACY_V1 execution semantics,
- migrate or delete live-state data,
- perform JSON-to-SQLite migration,
- introduce a new dependency,
- credit simulated AI units into PLN,
- modify real-money trading behavior,
- enable real-money trading.

Temporary diagnostic files and local UI backup directories are intentionally
excluded from the Phase 04 commit.

## Final Phase 04 classification

### CONFIRMED + FIXED

- AI ranking after learning bonus
- AI simulation units incorrectly credited to PLN
- processed timestamp advanced too early
- missing separate MTM maximum drawdown metric

### NOT CONFIRMED

- repeated backtest state leakage
- cross-asset state leakage

Phase 04 is complete subject to the recorded test and benchmark evidence above.
