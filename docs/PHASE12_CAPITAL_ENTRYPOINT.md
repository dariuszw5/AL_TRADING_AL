# Phase 12 A.8 — Controlled Capital Accounting Entrypoint

HARD STOP 12A authorizes the first Phase 12 runtime wiring and BTCUSDT-only
paper smoke.

A.8 adds a controlled command-line entrypoint:

`python -m scripts.run_phase12_capital_accounting_smoke`

It composes the verified Phase 10 accounting runtime, Phase 11 authoritative
settled cash and Phase 12 capital admission.

## Startup persistence order

Before any optional paper cycle the entrypoint:

1. constructs the existing REALISTIC_V2 PaperBroker runtime,
2. verifies or initializes the Phase 11 cash ledger,
3. reconciles persisted realized bookings into cash,
4. constructs the Phase 10 accounting wiring,
5. constructs the feature-flagged Phase 12 capital provider,
6. persists and verifies `phase10_startup_metadata.jsonl`,
7. persists and verifies the separate `phase12_startup_metadata.jsonl`,
8. verifies current settled cash.

Any failure before step 8 prevents the paper cycle.

## Feature flags

The controlled entrypoint requires all five:

- `AL_TRADING_REALISTIC_V2_ENABLED`
- `AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED`
- `AL_TRADING_FX_ENABLED`
- `AL_TRADING_PLN_ACCOUNTING_ENABLED`
- `AL_TRADING_CAPITAL_ADMISSION_ENABLED`

Phase 12 capital admission remains default-off outside this explicit path.

## First start and restart

First start requires explicit:

`--initial-cash-pln`

Restart reads the existing Phase 11 cash ledger and may omit the initial cash
argument. Conflicting restart initial cash fails closed.

## Cycle confirmation

`--run-cycle` is not enough by itself.

A live-market PaperBroker cycle additionally requires:

`--confirm-phase12-capital-smoke`

No real exchange order API is used.

## Capital evidence

For a new BTCUSDT LONG entry the output exposes:

- admission allowed/rejected,
- admission reason,
- proposed exposure PLN,
- explicit FX path,
- FX freshness,
- authoritative settled cash PLN,
- capital limit PLN,
- remaining headroom PLN.

Rejected capital admission does not reach PaperBroker and therefore creates no
paper execution.

EXIT remains outside capital admission.

## Boundaries

A.8 remains:

- BTCUSDT-only,
- controlled smoke-only,
- PaperBroker-only.

It does not modify the public all-asset runner, margin, collateral, leverage,
short financing, state/journal schemas, Phase 10/11 persistence formats,
LEGACY_V1 or frozen strategy.

The next step is a live temporary-state Phase 12 smoke covering both an
allowed LONG and an oversized rejected LONG, followed by restart/EXIT
verification.
