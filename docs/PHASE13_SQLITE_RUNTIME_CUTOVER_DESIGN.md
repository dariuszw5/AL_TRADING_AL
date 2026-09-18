# PHASE 13 A.10 — SQLITE RUNTIME CUTOVER DESIGN

## Status

Design and audit only.

The real database already exists at:

data/live/trading.db

It remains HALTED.

This phase does not wire the runtime to SQLite and does not clear HALT.

## Current persistence boundary

The REALISTIC_V2 runtime currently has persistence responsibilities split
across JSON/JSONL components, including:

- RealisticPaperStateStore for active position state
- RealisticExecutionJournal for PREPARED / COMMITTED execution recovery
- RealizedAccountingJournal for realized accounting
- Phase11CashLedger for settled PLN cash
- Phase 10 startup metadata persistence
- Phase 12 startup metadata persistence

The Phase 13 SQLite repository already provides the target durable
primitives for:

- orders
- executions
- positions
- portfolio transactions
- trades
- equity snapshots
- asset equity snapshots
- AI decisions
- system events
- persistent system state
- persistent HALT
- last processed timestamp
- cash reconciliation
- realized-PnL reconciliation
- backup / restore
- idempotent writes
- atomic BEGIN IMMEDIATE cycles

## Cutover principle

SQLite becomes the single authoritative persistence layer for the new
paper-live runtime.

Legacy JSON/JSONL persistence must not remain a second writer after
cutover.

The old files may remain as historical evidence but must become
read-only / unused by the cutover runtime.

## Required runtime adapter

The implementation phase should introduce a narrow SQLite runtime
persistence adapter or unit-of-work boundary.

The execution strategy, market-data providers, PaperBroker pricing logic,
asset registry and frozen BTC LEGACY_V1 strategy are outside this
persistence cutover.

The adapter must provide startup reconstruction for:

- persistent HALT state
- active positions
- execution idempotency state
- settled cash
- relevant completed trade/accounting state
- last processed timestamp

## Atomic cycle rule

For a successfully processed market timestamp, all SQLite financial and
execution effects belonging to that cycle must commit together.

The target transaction boundary is:

BEGIN IMMEDIATE

then, as applicable:

1. validate persistent HALT / reconciliation state
2. persist idempotent order identity
3. persist execution
4. persist position open/update/close
5. persist realized trade
6. persist REALIZED_PNL portfolio transaction
7. update settled cash
8. persist equity / audit events when produced
9. persist last_processed_timestamp_utc

then:

COMMIT

Any exception before COMMIT must roll back the whole database cycle.

## HALT semantics

HALT remains persistent in SQLite.

While HALTED:

- new ENTRY admission is blocked
- no new position may be opened
- existing-position safety/exit management must remain possible once
  runtime cutover is implemented
- HALT may not be silently cleared on restart

A.10 does not clear HALT.

## Idempotency

client_order_id remains the external idempotency identity.

A duplicate replay with the same semantic payload must not create a
second order or execution.

A conflicting replay must fail closed.

The last processed timestamp must not advance independently from the
financial effects of its cycle.

## Existing PREPARED / COMMITTED journal semantics

The current JSONL execution journal writes PREPARED before broker
processing and COMMITTED after runtime-state persistence.

Moving this crash-recovery contract into one SQLite transaction affects
execution/persistence ordering.

Therefore this behavior must not be changed implicitly.

The implementation phase must include explicit tests for:

- crash before transaction begin
- crash after order creation but before execution persistence
- crash after execution persistence but before commit
- database rollback
- restart replay
- duplicate client_order_id
- conflicting client_order_id
- no duplicate position
- no duplicate realized PnL
- no processed-timestamp advance on rollback

## Fresh database boundary

The live database was created by fresh bootstrap.

It contains:

- explicit initial settled cash only
- persistent HALT
- no inherited order history
- no inherited execution history
- no inherited positions
- no inherited trades
- NULL last processed timestamp

The incomplete REALISTIC_V2 smoke-state and legacy live_state are not
migration inputs.

## Cutover activation sequence

The future implementation/cutover must be split into separate safety
steps:

1. implement SQLite runtime adapter against temporary databases
2. controlled RED tests
3. adapter/unit tests
4. integration tests with fake market data
5. crash/restart tests
6. full offline regression
7. BTC LEGACY_V1 golden
8. read-only validation of data/live/trading.db
9. wire runtime to live SQLite while database remains HALTED
10. verify startup/restart with zero ENTRY execution
11. separate HARD STOP
12. only then consider explicit HALT clear / paper-live activation

## Forbidden in A.10

A.10 must not:

- modify data/live/trading.db
- clear HALT
- create orders
- create executions
- create positions
- create trades
- run a paper-live execution cycle
- wire production runtime to SQLite
- delete legacy persistence files
- change accounting semantics
- change PaperBroker execution semantics
- change the frozen BTC LEGACY_V1 strategy

## Next phase

A.11 may implement the SQLite runtime persistence adapter against
temporary databases only.

Real runtime cutover remains a later explicit step.

HALT clear remains a separate explicit action after cutover validation.
