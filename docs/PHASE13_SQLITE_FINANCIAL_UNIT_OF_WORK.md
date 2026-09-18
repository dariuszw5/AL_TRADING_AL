# PHASE 13 A.12 — SQLITE FINANCIAL UNIT OF WORK

## Status

Implemented and tested against temporary SQLite databases only.

data/live/trading.db was not modified.
Runtime SQLite wiring was not performed.
HALT was not cleared.

## Financial settlement boundary

A.12 introduces one atomic realized-financial settlement containing:

1. REALIZED_PNL portfolio transaction persistence
2. realized trade persistence
3. settled cash mutation
4. processed timestamp
5. cash reconciliation
6. realized-PnL reconciliation

All effects commit together or roll back together.

The REALIZED_PNL record is inserted before the trade because the trades
schema enforces a foreign-key dependency from realized_transaction_id to
the portfolio transaction.

## Exact cash semantics

The REALIZED_PNL portfolio amount must exactly equal the trade's
realized_pnl_pln.

The trade must reference the same realized transaction ID.

The portfolio transaction must reference the same trade identity.

On a newly-created settlement:

new settled cash = previous settled cash + REALIZED_PNL amount

On an exact replay, the transaction and trade are both idempotent and
settled cash is not changed a second time.

## Fail-closed reconciliation

Before beginning a new settlement, the unit calls the repository
reconcile_or_halt contract.

A pre-existing cash or realized-PnL mismatch therefore persists
RECONCILIATION_MISMATCH HALT before any new financial write.

Inside the atomic settlement, both cash and realized-PnL reconciliation
must pass before COMMIT.

## HALT semantics

Financial settlement for an exit is allowed while the database is
HALTED.

This is deliberate: HALT blocks new exposure but must not prevent
existing-position exit/accounting safety work.

A.12 never clears HALT.

## Rollback

If any failure occurs after transaction, trade or cash mutation but
before commit, the complete financial transaction is rolled back,
including the processed timestamp.

## Implementation correction during A.12

The first implementation attempted to persist the trade before its
REALIZED_PNL transaction. SQLite correctly rejected that ordering with a
foreign-key failure.

The production module was corrected without weakening the schema or
changing the test expectations: REALIZED_PNL is now persisted first and
the trade second, inside the same atomic transaction.

## Production boundary

A.12 is not wired to:

- RealisticPaperRuntime
- PaperBroker
- Phase 12 production entrypoint
- data/live/trading.db

The existing Phase 10/11 JSON/JSONL runtime remains untouched.

## Next phase

A.13 should compose the A.11 execution persistence adapter and A.12
financial unit of work into a temporary-database integration harness.

That phase should exercise:

- open cycle
- close cycle
- restart
- replay
- crash rollback
- HALT entry block
- HALT exit completion

Real runtime cutover remains a later explicit step.
