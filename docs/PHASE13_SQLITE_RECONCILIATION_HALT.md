# PHASE 13 A.4 — SQLITE RECONCILIATION AND PERSISTENT HALT

## Status

Implemented and verified on temporary SQLite databases only.

No production database was created.
No migration was performed.
No paper-live runtime was switched to SQLite.

## Added repository contracts

- position persistence with idempotent replay
- trade persistence with idempotent replay
- system event persistence with idempotent replay
- realized PnL reconciliation
- persistent HALT
- explicit audited HALT clear
- reconciliation mismatch -> persistent HALT

## Cash invariant

Existing A.3 invariant remains:

sum(portfolio_transactions.amount_pln)
equals
system_state.cash_balance_pln

Exact Python Decimal arithmetic is used.

## Realized PnL invariant

Every trade must reference exactly one REALIZED_PNL portfolio transaction.

The linked amount must equal the trade realized_pnl_pln.

All REALIZED_PNL transactions must be linked to trades.

Aggregate trade realized PnL must equal aggregate REALIZED_PNL ledger amount.

Any mismatch raises:

RECONCILIATION_MISMATCH

## Persistent HALT

reconcile_or_halt performs both reconciliation checks.

On mismatch:

- system_state.halted = 1
- halt_reason = RECONCILIATION_MISMATCH
- SYSTEM_HALT event is persisted
- the mismatch exception is re-raised

HALT survives database reopen.

## HALT clear

HALT cannot be silently cleared.

clear_halt_explicitly requires a non-empty reason and writes a SYSTEM_HALT_CLEARED audit event.

## Runtime boundary

A.4 does NOT yet wire persistent SQLite HALT into paper-live entry admission.

Existing runtime behavior is unchanged.

That integration remains a later focused step.

## Live database

data/live/trading.db was not created.

All A.4 tests use temporary pytest databases.

## Migration

No JSON or JSONL migration was performed.

Real migration remains behind the existing HARD STOP.
