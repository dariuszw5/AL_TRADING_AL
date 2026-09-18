# PHASE 13 A.3 — SQLITE REPOSITORY FOUNDATION

## Status

IMPLEMENTED FOR TEMPORARY DATABASES ONLY.

No live SQLite database was created.
No JSON or JSONL data was migrated.
No runtime was switched to SQLite.

## Scope

A.3 adds the first SQLite repository foundation:

- writer connection
- read-only reader connection
- WAL writer policy
- busy timeout
- foreign keys ON
- synchronous FULL
- query_only reader
- approved schema initialization
- schema checksum verification
- BEGIN IMMEDIATE atomic cycle
- rollback on failure
- order idempotency
- execution idempotency
- portfolio transaction idempotency
- exact Decimal text normalization
- system_state initialization
- exact Decimal cash reconciliation

## Idempotency

Orders use:

client_order_id + order identity + order_fingerprint

Exact replay returns the existing record.

Conflicting identifier reuse raises:

IdempotencyConflictError

Executions use execution_id.

Portfolio transactions use transaction_id.

Exact replay is idempotent.

Conflicting replay fails closed.

## Atomic cycle

Financial writes require an active:

BEGIN IMMEDIATE

transaction through atomic_cycle().

Successful cycles COMMIT.

Exceptions ROLLBACK.

Nested cycles are rejected.

## Decimal policy

Financial values remain canonical decimal TEXT.

Python Decimal is used for exact reconciliation.

SQLite floating-point SUM is not used for the authoritative cash invariant.

## Read-only API foundation

open_reader() uses SQLite URI read-only mode and PRAGMA query_only=ON.

A.3 does not connect FastAPI to this reader yet.

## Reconciliation

A.3 implements exact cash reconciliation:

sum(portfolio_transactions.amount_pln)
equals
system_state.cash_balance_pln

Mismatch raises:

RECONCILIATION_MISMATCH

Persistent automatic HALT wiring is intentionally deferred to the next focused step.

## Explicitly unchanged

- PaperBroker
- REALISTIC_V2 execution
- Phase 10 persistence
- Phase 11 cash runtime
- Phase 12 capital admission
- existing JSON and JSONL formats
- public all-asset runner
- BTC LEGACY_V1
- FastAPI
- Flutter
- live_state
- production persistence wiring

## Live database

data/live/trading.db was not created.

All A.3 SQLite tests use pytest temporary directories.

## Next step

Phase 13 A.4 should add repository-level:

- persistent HALT state
- reconciliation mismatch -> HALT
- system event audit
- realized PnL reconciliation
- trade / REALIZED_PNL linkage tests

Still no production migration.
