# PHASE 13 A.20 — COMPLETE TEMP SQLITE-ONLY RUNTIME BUNDLE

A.20 assembles the Phase 13 temporary SQLite-only runtime path into one
explicit bundle while leaving the default production runtime untouched.

## Single SQLite writer

SQLiteInjectedRuntime now accepts an optional already-open
SQLiteLedgerRepository.

When an external repository is injected:

- it must be a writable SQLiteLedgerRepository
- SQLiteInjectedRuntime does not own or close it
- the bundle owns the repository lifetime
- accounting recovery and durable persistence share the same writer

Legacy database-path construction remains backward compatible.

## Bundle composition

build_sqlite_only_runtime_bundle performs:

1. live-path rejection before database open
2. one SQLite writer open
3. startup cash reconciliation through SQLiteCashAuthority
4. OPEN position restore through SQLiteOpenPositionLoader
5. VolatilePositionStateStore construction
6. SQLite-only component guard
7. SnapshotCaptureDecisionProvider wrapping
8. actual RealisticPaperRuntime construction
9. existing Phase 09 accounting construction with SQLite entry resolver
10. A.17 mapper construction
11. A.16 injected durable runtime using the same repository

## Actual restart EXIT proof

The A.20 integration test seeds only historical ENTRY evidence in a
temporary SQLite database.

It then simulates process restart and constructs the complete bundle.

The database remains persistently HALTED, but because AAPL has an OPEN
position the safety EXIT path is allowed.

The actual RealisticPaperRuntime and actual PaperBroker generate the EXIT
execution from a REAL_BOOK market snapshot.

The existing accounting implementation recovers ENTRY execution from
SQLite and computes:

- net realized native PnL = 19.58 USD
- net realized PnL = 78.320 PLN

A.17 maps the runtime/accounting result and A.14 commits atomically:

- EXIT order
- EXIT execution
- OPEN -> CLOSED
- REALIZED_PNL
- trade
- settled cash
- processed timestamp
- reconciliation

Settled cash becomes 1078.320 PLN.

HALT remains active.

After another simulated restart there is no OPEN position. HALT therefore
blocks a new ENTRY before the runtime or decision provider executes.

## Durable writer proof

The integration creates no .json or .jsonl persistence files.

SQLite is the only durable writer in this bundle.

## Production boundary

A.20 still does not:

- use data/live/trading.db
- clear the real HALT
- change default RealisticPaperRuntime
- change PaperBroker
- send real orders
- activate paper-live trading
- enable multi-asset runtime batching

## Next boundary

The temporary single-asset SQLite-only runtime path is now complete enough
for a live-cutover preflight.

A.21 should be DESIGN/AUDIT ONLY against data/live/trading.db while it
remains HALTED and read-only from the runtime perspective.

A separate HARD STOP is required before wiring the real live database or
clearing its HALT.
