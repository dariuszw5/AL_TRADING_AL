# Phase 09 A.15 - Additive REALISTIC_V2 Accounting Integration

## Decision

A.15 integrates the Phase 09 accounting bridge with REALISTIC_V2 through
an additive wrapper.

The existing execution runtime is not modified.

The wrapper calls the existing runtime first and performs accounting only
after that execution cycle returns.

Accounting failures therefore cannot rewrite an already-produced
execution result.

## Snapshot boundary

REALISTIC_V2 already passes the exact market snapshot to its decision
provider.

A.15 adds `SnapshotCaptureDecisionProvider`, a transparent wrapper around
the existing decision provider.

It records that already-consumed snapshot and returns the delegate
decision unchanged.

The capture is cleared before every cycle so an old snapshot cannot be
silently reused for a later accounting cycle.

## Unrealized MTM

For every still-open position after an execution cycle, A.15 supplies the
captured BID/ASK snapshot, an explicit unit FX conversion and an explicit
estimated exit fee to the A.14 bridge.

FX conversion and exit-fee resolution are injected dependencies.

A.15 does not invent either value.

## Realized PnL

When an entry execution occurs, A.15 caches the complete `Execution`
object in memory.

If the same process later receives the closing execution, the exact
entry and exit executions are passed to the A.14 bridge.

The cache is deliberately not persisted.

After process restart, if the complete entry execution is unavailable,
realized accounting fails closed with:

`ENTRY_EXECUTION_REQUIRED`

A.15 does not reconstruct an execution from `Position.entry_price`.

## Multi-asset isolation

Accounting is processed independently per asset.

An accounting failure for one asset does not replace or mutate the
REALISTIC_V2 execution cycle for another asset.

Portfolio aggregation is blocked when an open position lacks a complete
PLN MTM record. Partial portfolios are never silently summed.

## Futures

`GOLD_FUT_CONT` and `WTI_FUT_CONT` remain fail-closed through the A.9
instrument accounting contract.

A.15 does not activate the reference multipliers 100 or 1000.

## Persistence

Accounting records are not persisted.

The existing known limitation remains:

`ACCOUNTING_PERSISTENCE_NOT_IMPLEMENTED`

No SQLite migration is started.

No existing `data/live_state` file is modified.

## Feature flags

A.15 does not change the A.13 flag contract.

The integration object must be constructed by a caller only when the
Phase 09 FX/PLN accounting feature flags are intentionally enabled.

Production entrypoint wiring remains disabled until the Phase 09 closure
confirms readiness and known limitations.

## Existing surfaces intentionally unchanged

A.15 does not modify:

- `src/execution/runtime.py`
- `src/execution/paper_broker.py`
- `src/execution/execution_journal.py`
- `src/execution/state_store.py`
- `scripts/run_paper_live.py`
- `scripts/run_realistic_paper.py`
- `scripts/run_realistic_smoke_fill.py`
- frozen strategy parameters
- LEGACY_V1
- existing test assertions
- existing runtime state
