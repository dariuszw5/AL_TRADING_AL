# PHASE 13 A.19 — SQLITE ACCOUNTING BRIDGE + CASH AUTHORITY

A.19 reuses the existing Phase 09 realized-accounting implementation
after process restart while replacing legacy durable recovery/cash
sources with SQLite.

## Entry execution recovery

build_sqlite_phase09_accounting_runtime constructs the existing
JournalBackedPhase09AccountingRuntime with SQLiteEntryExecutionResolver.

The existing accounting formulas, FX selection and RealizedFxBooker are
not modified.

After restart, the exact persisted ENTRY execution is read from SQLite
and temporarily supplied to the existing accounting bridge.

## Cash authority

SQLiteCashAuthority reads settled PLN cash from system_state only after
verifying exact reconciliation against portfolio_transactions.

SQLiteLedgerRepository may fail closed by raising
ReconciliationMismatchError directly. SQLiteCashAuthority translates
that repository-level failure into SQLiteAccountingAuthorityError while
preserving the original exception as the cause.

No Phase11CashLedger JSONL file is used.

## Restart accounting proof

The A.19 integration test:

1. bootstraps temporary SQLite with 1000 PLN
2. persists AAPL ENTRY order/execution/OPEN position
3. closes and reopens the database to simulate restart
4. restores the OPEN position from SQLite
5. recovers the exact ENTRY execution from SQLite
6. runs the existing Phase 09 accounting calculation
7. obtains:
   - net realized native PnL = 19.58 USD
   - net realized PnL = 78.320 PLN
8. confirms accounting alone does not mutate settled cash
9. maps the realized result through the A.17 mapper
10. settles EXIT through the A.14 atomic SQLite trade cycle
11. verifies settled cash = 1078.320 PLN
12. verifies cash and realized-PnL reconciliation
13. replays the exact EXIT and proves cash is not double-booked

No JSON or JSONL accounting/cash file is created by the test.

## Production boundary

A.19 does not:

- use data/live/trading.db
- clear the real HALT
- change existing Phase09/10/11 implementations
- modify RealisticPaperRuntime
- modify PaperBroker
- activate trading

## Next phase

A.20 should assemble the complete temporary SQLite-only runtime bundle:
real runtime + volatile state + SQLite restart recovery + existing
accounting + A.17 mapper + A.16 injected durability.

That phase should prove an actual paper EXIT after restart end-to-end
without legacy durable writers.

A separate HARD STOP remains required before any real live database
cutover.
