# PHASE 13 A.11 — SQLITE RUNTIME PERSISTENCE ADAPTER

## Status

Implemented and tested against temporary SQLite databases only.

No production runtime wiring was performed.
data/live/trading.db was not modified.
Persistent HALT was not cleared.

## Scope

A.11 introduces a narrow non-financial SQLite runtime persistence
boundary.

The adapter supports:

- startup read of persistent HALT state
- startup read of settled cash
- startup read of last processed timestamp
- atomic order persistence
- atomic execution persistence
- atomic position persistence
- atomic processed-timestamp persistence
- exact replay through repository idempotency
- transaction rollback on persistence failure

## HALT behavior

When SQLite system_state is HALTED:

- ENTRY persistence is rejected before any database write
- EXIT persistence is permitted
- HALT is not cleared by the adapter

This preserves the required distinction between blocking new exposure and
allowing safety/exit management.

## Atomicity

A successful non-financial execution cycle is persisted inside one
repository atomic_cycle.

Order, execution, position and processed timestamp therefore commit
together or roll back together.

## Deliberate A.11 boundary

A.11 does NOT accept:

- portfolio transactions
- realized trades
- settled cash mutations
- realized-PnL booking

Those financial semantics remain unchanged and will be integrated in a
separate phase.

This prevents the persistence cutover from silently changing Phase 10/11
accounting semantics.

## Production boundary

The adapter is not connected to RealisticPaperRuntime, PaperBroker, the
Phase 12 entrypoint, or data/live/trading.db.

The live database remains HALTED.

## Next phase

A.12 should add the financial SQLite unit-of-work contract on temporary
databases:

- realized trade
- REALIZED_PNL portfolio transaction
- settled cash update
- cash reconciliation
- realized-PnL reconciliation
- processed timestamp in the same transaction

Only after those semantics are independently tested should runtime
integration be considered.
