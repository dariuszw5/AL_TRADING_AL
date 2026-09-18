# PHASE 13 A.14 — TEMP SQLITE TRADE CYCLE INTEGRATION

A.14 integrates the Phase 13 persistence contracts on temporary SQLite
databases only.

The ENTRY cycle uses the A.11 runtime persistence adapter.

The EXIT cycle uses a new coordinator that places all exit-side effects
inside one SQLite atomic_cycle:

- EXIT order
- EXIT execution
- OPEN -> CLOSED position transition
- REALIZED_PNL portfolio transaction
- realized trade
- settled cash update
- processed timestamp
- cash reconciliation
- realized-PnL reconciliation

A.14 also adds a public in-transaction financial settlement primitive to
SQLiteFinancialUnitOfWork so the coordinator can keep the complete EXIT
cycle atomic instead of committing the exit timestamp early.

The integration test covers:

- explicit temporary activation
- ENTRY persistence
- database restart
- persistent HALT
- HALT blocks a new ENTRY
- HALT still allows existing-position EXIT completion
- CLOSED position persistence
- realized PnL settlement
- exact PLN cash update
- database restart after settlement
- exact replay without duplicates or second cash mutation
- forced failure rollback across order, execution, close, financial state
  and processed timestamp

data/live/trading.db is unchanged.
Production runtime is not wired to SQLite.
HALT is not cleared on the real database.
Trading is not activated.

Next: A.15 runtime cutover adapter wiring on temporary/injected database
paths only, followed by a separate live cutover hard stop.
