# PHASE 13 A.16 — OPTIONAL INJECTED SQLITE RUNTIME MODE

## Authorization

A.16 was started only after the explicit HARD STOP at the runtime
execution/persistence ordering boundary was released by the operator.

## Scope

A.16 introduces a separate opt-in SQLite persistence runtime wrapper.

The default REALISTIC_V2 runtime source and PaperBroker source are not
modified.

The wrapper requires an explicit pre-existing SQLite database path.

The real data/live/trading.db path is forbidden by the A.16 constructor.

## Ordering change

In injected mode the wrapped runtime produces an in-memory cycle result
first.

Only after the complete result exists does A.16 perform the durable
SQLite persistence step.

ENTRY uses the Phase 13 runtime adapter.

EXIT uses the A.14 atomic trade-cycle coordinator:

- EXIT order
- EXIT execution
- OPEN -> CLOSED
- REALIZED_PNL
- trade
- settled cash
- processed timestamp
- reconciliation

This is intentionally different from the legacy JSON/JSONL durability
order and is available only through explicit opt-in construction.

## HALT

A persistent SQLite HALT blocks execution of an asset when SQLite has no
OPEN position for that asset.

An asset with an existing OPEN SQLite position may still run while
HALTED so that EXIT/safety management remains possible.

The real live database HALT is not cleared.

## Memory rollback

The wrapper requires explicit snapshot_provider and restore_snapshot
callbacks.

If durable SQLite persistence fails after the in-memory paper runtime
cycle, the runtime memory snapshot is restored and the exception is
propagated.

The broker remains paper-only; A.16 sends no real-market order.

## Single-asset boundary

A.16 accepts exactly one asset per run_cycle.

This is deliberate.

Cross-asset atomic batch semantics are not introduced implicitly.

A later phase must design multi-asset batching before any all-assets
production cutover.

## Legacy persistence

A.16 itself performs no JSON/JSONL writes.

The caller is responsible for constructing the wrapped runtime without
legacy durable writers.

A future composition phase must prove that requirement against the real
runtime stack.

## Production boundary

A.16 does not:

- use data/live/trading.db
- modify the real live database
- clear the real persistent HALT
- modify default RealisticPaperRuntime behavior
- modify PaperBroker behavior
- activate paper-live trading
- enable multi-asset live execution

## Next phase

A.17 should provide the concrete mapper/composition for actual
REALISTIC_V2 runtime result objects and prove that legacy durable writers
are disabled in injected mode.

A.17 must still use temporary/test SQLite paths only.

A separate HARD STOP remains required before real data/live/trading.db
cutover.
