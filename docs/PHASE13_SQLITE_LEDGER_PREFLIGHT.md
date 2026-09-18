# PHASE 13 — SQLITE LEDGER DESIGN PREFLIGHT

## Status

DESIGN PREFLIGHT COMPLETE

No SQLite database was created.
No live data was migrated.
No persistence format was changed.
No trading mathematics were changed.

UTC: 2026-09-18T16:03:58.7178124Z

Base commit: 37302f2
Branch: phase-13-sqlite-ledger-preflight

## Python SQLite capability

Python stdlib sqlite3: AVAILABLE
SQLite runtime version: 3.50.4

No new dependency is required for the design phase.

## Current persistence inventory

Persistence-related source files discovered: 48

- src\accounting\__init__.py
- src\accounting\cash_ledger.py
- src\accounting\cash_runtime.py
- src\accounting\journal_entry_recovery.py
- src\accounting\mtm_kernel.py
- src\accounting\pln_kernel.py
- src\accounting\portfolio_snapshot.py
- src\accounting\production_fx_scheduler.py
- src\accounting\production_resolvers.py
- src\accounting\production_startup.py
- src\accounting\realized_persistence.py
- src\accounting\runtime_bridge.py
- src\accounting\runtime_integration.py
- src\accounting\startup_metadata_store.py
- src\agent\agent_engine.py
- src\agent\agent_loop.py
- src\agent\agent_state.py
- src\agent\ai_manager.py
- src\agent\live_state_store.py
- src\agent\multi_asset_runner.py
- src\backtest\backtest_engine.py
- src\backtest\backtest_runner.py
- src\backtest\strategy_optimizer.py
- src\backtest\test_runner.py
- src\backtest\validation_runner.py
- src\config_fingerprint.py
- src\data\assets.py
- src\data\data_provider.py
- src\execution\capital_admission.py
- src\execution\capital_exposure.py
- src\execution\capital_runtime.py
- src\execution\capital_startup.py
- src\execution\capital_startup_store.py
- src\execution\execution_journal.py
- src\execution\execution_policy.py
- src\execution\live_preflight.py
- src\execution\paper_broker.py
- src\execution\runtime.py
- src\execution\state_store.py
- src\fx\converter.py
- src\fx\freshness.py
- src\fx\models.py
- src\fx\providers.py
- src\fx\realized_booking.py
- src\fx\realized_selection.py
- src\market\__init__.py
- src\market\market_session.py
- src\trading\paper_trading.py

## Persistence test inventory

Persistence-related test files discovered: 16

- tests/test_agent_state.py
- tests/test_agent_state_integration.py
- tests/test_agent_state_manager.py
- tests/test_phase10_journal_entry_recovery.py
- tests/test_phase10_persisted_accounting_entrypoint.py
- tests/test_phase10_production_startup.py
- tests/test_phase10_realized_accounting_persistence.py
- tests/test_phase10_startup_metadata_store.py
- tests/test_phase11_cash_accounting_entrypoint.py
- tests/test_phase11_cash_ledger.py
- tests/test_phase11_cash_runtime.py
- tests/test_phase12_capital_startup.py
- tests/test_phase12_capital_startup_store.py
- tests/test_realistic_v2_execution_journal.py
- tests/test_realistic_v2_reconciliation.py
- tests/test_realistic_v2_state_store.py

## SQLite implementation search

- C:\Users\ddare\Desktop\Al_Trading_Al\src\accounting\mtm_kernel.py:148: update cash/equity/exposure, persist a ledger, or introduce SQLite.
- C:\Users\ddare\Desktop\Al_Trading_Al\src\accounting\__pycache__\mtm_kernel.cpython-314.pyc:78: update cash/equity/exposure, persist a ledger, or introduce SQLite.

## Required target architecture for next design step

Target database path:
data/live/trading.db

Required schema domains:
- schema_version
- portfolio_transactions
- orders
- executions
- trades
- positions
- equity_snapshots
- asset_equity_snapshots
- ai_decisions
- system_events
- system_state / HALT

Required SQLite policy:
- journal_mode=WAL
- busy_timeout
- foreign_keys=ON
- synchronous=FULL
- one writer: paper-live
- API uses read-only access

Required financial invariants:

SUM(portfolio_transactions.amount_pln) == cash_balance_pln

realized PnL from trades == REALIZED_PNL ledger transactions

Mismatch must become RECONCILIATION_MISMATCH and HALT new entries.

## Explicitly deferred

- No JSON -> SQLite migration.
- No live-state replacement.
- No deletion of legacy persistence.
- No production trading.db creation.
- No API switch to SQLite.
- No Flutter changes.
- No real-money execution.

## Next step

Phase 13 A.2 should design the SQLite schema, repository interfaces, transaction boundaries, idempotency keys, reconciliation rules, backup/restore procedure and migration dry-run strategy.

Actual migration remains behind a separate HARD STOP.

## Regression

Targeted persistence tests: PASS

Full offline regression: PASS

BTC LEGACY_V1 golden: MATCH

Expected final balance: 1014.8392976799995
Expected total profit: 14.839297679999504
Expected profit factor: 1.692128777090018
Expected trades: 13
