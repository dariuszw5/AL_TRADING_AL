# PHASE 08 — REALISTIC_V2 DESIGN GATE

Date: 2026-09-16

Status:
HARD STOP — IMPLEMENTATION NOT YET AUTHORIZED

## Completed in Part A

- reviewed MASTER_SPEC execution-quality rules
- reviewed Phase 07 report
- captured current AssetRegistry execution metadata
- designed BrokerInterface
- designed PaperBroker
- designed Order / Execution / Position
- separated SIGNAL -> ORDER -> EXECUTION -> POSITION
- designed bid/ask entry and exit rules
- designed stale/delayed policy
- designed STOP_GAP
- designed EXIT_PENDING
- designed market-closed behavior
- designed short capability checks
- designed deterministic slippage
- defined test matrix
- defined rollback
- defined benchmark separation

No execution code changed.

## Files expected to be added after approval

- src/execution/__init__.py
- src/execution/models.py
- src/execution/broker_interface.py
- src/execution/paper_broker.py
- src/execution/slippage.py
- src/execution/execution_policy.py
- tests/test_realistic_v2_execution.py
- scripts/run_realistic_v2_benchmark.py

## Files potentially changed after approval

- src/agent/agent_config.py
- src/agent/agent_engine.py
- src/backtest/backtest_runner.py
- paper-live orchestration entry point

Exact files will be audited before modification.

## Protected data

Phase 08 implementation will not intentionally:
- overwrite data/live_state
- modify frozen candle datasets
- migrate database/storage
- change strategy thresholds
- change existing test assertions

## Rollback

REALISTIC_V2 remains behind an explicit execution profile.

Rollback:
- disable REALISTIC_V2 selection
- preserve LEGACY_V1
- revert Phase 08 implementation commits if required

No data migration rollback is expected.

## Expected impact

LEGACY_V1:
zero intended benchmark impact.

REALISTIC_V2:
new benchmark expected to differ because it includes executable quote
side, spread, slippage and gap behavior.

No profitability target exists.

Strategy thresholds will not be optimized in response to the result.

## HARD STOP

Implementation changes execution semantics.

Explicit human approval is required before Part B.
