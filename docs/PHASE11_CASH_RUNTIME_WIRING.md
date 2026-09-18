# Phase 11 A.5 - Cash Runtime Wiring

Hard-stop approval 11A authorizes the controlled Phase 11 runtime to use the
Phase 11 cash ledger as its authoritative settled-cash PLN source.

A.5 implements the runtime wiring layer. It does not yet add or enable a new
CLI entrypoint; that follows in A.6.

## Startup reconciliation

A realized booking and its cash settlement are two durable records in two
separate append-only journals.

A process can therefore terminate after the Phase 10 realized booking is
fsynced but before the Phase 11 cash settlement is fsynced.

To close that crash window, Phase 11 startup reconciliation:

1. verifies the cash ledger,
2. verifies every Phase 10 realized booking,
3. iterates every realized booking,
4. settles it through the cash ledger idempotency contract,
5. leaves already-settled bookings unchanged.

This makes a persisted realized booking recoverable into settled cash after
restart without re-running a broker CLOSE.

## Runtime ordering

For a normal successful CLOSE cycle the controlled Phase 11 wrapper executes:

1. unchanged REALISTIC_V2 PaperBroker cycle,
2. Phase 09 realized PLN accounting,
3. Phase 10 realized-accounting persistence,
4. Phase 11 cash settlement from that persisted booking,
5. portfolio snapshot rebuild using current authoritative cash.

The cash delta is never reconstructed from execution prices. It comes only
from the persisted `net_realized_pnl_pln`.

## Portfolio snapshot timing

Phase 09 computes its portfolio snapshot before Phase 11 cash settlement would
normally occur.

A.5 therefore rebuilds the returned portfolio snapshot after settlement using:

- current settled cash from `phase11_cash_ledger.jsonl`,
- the already-computed successful MTM records for positions still open.

This avoids returning stale pre-settlement cash/equity on a CLOSE cycle.

If any still-open requested position lacks a successful MTM record, the
portfolio snapshot remains fail-closed with
`PORTFOLIO_PARTIAL_ACCOUNTING_BLOCKED`.

## Authoritative resolver

`wire_phase11_cash_runtime()` passes only:

`cash_ledger.current_cash_pln`

as the Phase 10 `cash_pln_resolver`.

No execution state, position state, notional, margin or caller-supplied
floating value is used as cash.

## Explicit limitations

The A.4 cash semantic remains unchanged:

`ENTRY_FEE_SETTLED_AT_REALIZATION`

This runtime still does not implement:

- buying power,
- notional reservation,
- margin,
- collateral,
- short financing,
- persistent unrealized MTM,
- all-asset production enablement,
- SQLite.

## Persistence failure semantics

Paper execution is not rolled back if accounting persistence fails after a
paper fill.

The controlled entrypoint must surface the failure and stop further work.

On restart, already-persisted Phase 10 realized bookings are reconciled
idempotently into the Phase 11 cash ledger.

## Protected boundaries

A.5 does not modify:

- PaperBroker,
- execution semantics,
- state.json,
- execution_journal.jsonl,
- Phase 10 startup metadata format,
- Phase 10 realized-accounting format,
- frozen strategy,
- existing assertions,
- data/live_state,
- public all-asset runner.
