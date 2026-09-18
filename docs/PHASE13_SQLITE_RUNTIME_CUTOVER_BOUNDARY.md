# PHASE 13 A.15 — RUNTIME SQLITE CUTOVER BOUNDARY

## Status

Audit and design only.

No execution runtime source was modified.
No PaperBroker source was modified.
data/live/trading.db was not modified.
HALT was not cleared.
Trading was not activated.

## Current runtime persistence order

The current REALISTIC_V2 execution path performs the relevant operations
in this order:

1. PaperBroker submit / execution
2. runtime active-position state save
3. execution journal commit

PaperBroker also performs execution-journal PREPARED persistence before
the simulated broker execution.

This ordering is internally consistent with the current JSON/JSONL crash
recovery contract.

## Phase 13 target

The validated SQLite target established by A.11 through A.14 requires a
single atomic SQLite transaction for the full durable cycle.

For EXIT settlement the target transaction includes:

- order identity
- execution
- OPEN -> CLOSED position transition
- REALIZED_PNL transaction
- realized trade
- settled cash
- processed timestamp
- reconciliation

A.14 proved this contract on temporary SQLite databases.

## Boundary finding

The current runtime ordering cannot be replaced by the A.14 atomic SQLite
cycle through a simple state-store or journal adapter.

A state-store adapter is insufficient because save_positions does not
receive complete execution/accounting evidence.

A journal adapter is insufficient because journal commit occurs after
runtime position persistence.

Trying to run SQLite beside the existing JSON/JSONL writers would create
dual authoritative persistence and is forbidden.

## Required semantic change

The runtime must gain one explicit injectable persistence boundary that
receives a completed execution result plus the position/accounting effects
and commits them through the Phase 13 SQLite transaction coordinator.

The runtime must call that boundary before considering a cycle durably
processed.

This changes persistence/execution ordering and therefore qualifies as an
execution-semantics change.

## HARD STOP

Per the project safety contract, implementation must stop before changing:

- RealisticPaperRuntime execution ordering
- PaperBroker journal ordering
- PREPARED / COMMITTED recovery semantics
- the production entrypoint persistence path

The next implementation requires explicit authorization.

## Proposed next phase after authorization

A.16 should be limited to an optional injected persistence mode used only
with temporary/test SQLite database paths.

Requirements:

- default runtime behavior remains unchanged
- JSON/JSONL tests remain unchanged
- SQLite mode must be explicit
- live data/live/trading.db path must be rejected in A.16
- SQLite mode must use A.14 atomic coordinator
- ENTRY and EXIT crash/restart tests required
- no real HALT clear
- no paper-live activation
- full offline regression
- BTC LEGACY_V1 golden unchanged

Only after A.16 passes should a separate hard stop be taken before any
live database cutover.
