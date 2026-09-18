# PHASE 13 A.18 — SQLITE-ONLY COMPOSITION AND RESTART RESTORE

A.18 closes the restart gap for injected SQLite mode without modifying
the existing RealisticPaperRuntime, PaperBroker, JSON state store or JSONL
execution journal implementations.

## SQLite open-position restoration

SQLiteOpenPositionLoader reads status=OPEN rows from the Phase 13
positions table and reconstructs REALISTIC_V2 Position objects.

The loader fails closed if more than one OPEN position exists for the
same asset or if a persisted position is not REALISTIC_V2.

## Volatile runtime state store

VolatilePositionStateStore implements the existing runtime
load_positions/save_positions interface entirely in memory.

It has no path and performs no durable filesystem write.

This lets RealisticPaperRuntime keep its current state-store contract
while SQLite remains the only durable persistence system in injected
mode.

## SQLite entry execution recovery

SQLiteEntryExecutionResolver replaces JournalEntryExecutionResolver for
SQLite-only restart accounting.

It resolves the exact persisted ENTRY execution by execution_id and
verifies:

- asset identity
- order intent ENTRY
- order status FILLED
- position asset identity
- position entry execution identity

It reconstructs the execution fields required by the existing accounting
bridge from the SQLite orders/executions records.

No JSONL journal is required.

## Composition guard

assert_sqlite_only_components requires:

- VolatilePositionStateStore
- no durable state-store path
- broker.execution_journal is None

A legacy file-backed state store or JSONL execution journal is rejected.

## Real runtime restart proof

The A.18 test constructs the actual RealisticPaperRuntime with:

- SQLite-restored OPEN position
- VolatilePositionStateStore
- PaperBroker(execution_journal=None)

After simulated restart the runtime sees the existing OPEN position and
returns POSITION_ALREADY_OPEN for a new ENTRY decision.

No .json or .jsonl file is created.

## Production boundary

A.18 still does not:

- use data/live/trading.db
- clear the real persistent HALT
- modify the default production entrypoint
- activate paper-live trading
- enable multi-asset injected execution

## Next phase

A.19 should compose the actual Phase 10/11 accounting bridge with
SQLiteEntryExecutionResolver and SQLite cash authority on a temporary
database, proving an EXIT after restart can be fully booked without any
legacy journal/cash-ledger files.

A separate HARD STOP remains required before real live database cutover.
