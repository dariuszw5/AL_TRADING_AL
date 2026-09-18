# PHASE 13 — SQLITE LEDGER SCHEMA AND REPOSITORY CONTRACT

## Status

DESIGN ONLY.

No production database has been created.
No live JSON or JSONL data has been migrated.
No runtime persistence has been switched to SQLite.

Base commit before A.2: 530a66f

## Target database

Future target path:

data/live/trading.db

The target path is reserved only.
Phase 13 A.2 does not create it.

## Required connection policy

Writer connection:

- journal_mode = WAL
- foreign_keys = ON
- synchronous = FULL
- busy_timeout must be explicitly configured

Writer ownership:

- exactly one paper-live writer

API:

- read-only connection
- API must not become a competing financial writer

## Financial representation

SQLite REAL must not be the authoritative representation for financial values.

Financial values are designed as canonical decimal TEXT and future repository code must convert them to and from Python Decimal.

Reason:

- existing accounting already contains precision beyond two decimal places
- A.2 must not introduce a new rounding policy
- migration must preserve existing accounting semantics

A future rounding or fixed-scale integer policy would be a separate accounting decision and therefore requires explicit review.

## Schema domains

The V1 design contains:

1. schema_version
2. system_state
3. orders
4. executions
5. positions
6. portfolio_transactions
7. trades
8. equity_snapshots
9. asset_equity_snapshots
10. ai_decisions
11. system_events

## Idempotency

Orders:

client_order_id is UNIQUE.

order_id is PRIMARY KEY.

order_fingerprint is persisted for conflict detection.

Executions:

execution_id is PRIMARY KEY.

Portfolio transactions:

transaction_id is PRIMARY KEY.

Trades:

trade_id is PRIMARY KEY.

A duplicate market cycle must reuse deterministic order identity and must not create a second financial order.

The future repository must distinguish:

- exact idempotent replay
- conflicting replay using the same identifier with different payload

Conflicting replay must fail closed.

## Atomic cycle contract

A future paper-live financial cycle must use one SQLite transaction.

The transaction boundary must include all financial effects belonging to the processed event.

For an entry this can include:

- order persistence
- execution persistence
- position persistence
- system processed timestamp

For an exit this can include:

- exit order
- exit execution
- position close
- trade
- REALIZED_PNL portfolio transaction
- cash balance update
- equity snapshot if produced by that cycle
- processed timestamp

The processed timestamp must not commit before the financial effects of the same cycle.

Recommended transaction mode for the single writer:

BEGIN IMMEDIATE

Then:

COMMIT on success.

ROLLBACK on any failure.

A.2 does not wire this transaction into runtime.

## Cash invariant

Authoritative financial history:

portfolio_transactions

Materialized current cash:

system_state.cash_balance_pln

Required invariant:

sum of all portfolio transaction amounts in PLN
equals
system_state.cash_balance_pln

Because decimal values are stored as canonical TEXT, reconciliation must parse values with Python Decimal rather than SQLite floating-point arithmetic.

## Realized PnL invariant

For every realized trade:

trades.realized_transaction_id
must identify exactly one
portfolio_transactions transaction.

That transaction must represent REALIZED_PNL.

Aggregate realized PnL recorded by trades must equal aggregate REALIZED_PNL ledger transactions using exact Decimal arithmetic.

## Reconciliation failure

Any mismatch must produce:

RECONCILIATION_MISMATCH

System behavior:

- set persistent HALT
- reject new entries
- continue management of existing positions
- log a system event
- do not silently repair financial history

Removal of HALT must remain explicit and auditable.

## Repository contract for future implementation

The future repository layer should expose responsibilities equivalent to:

- initialize_schema
- read_schema_version
- apply_versioned_migration
- open_single_writer
- open_read_only_reader
- begin_atomic_cycle
- get_order_by_client_order_id
- insert_order_idempotent
- insert_execution_idempotent
- save_position
- close_position
- append_portfolio_transaction_idempotent
- append_trade_idempotent
- append_equity_snapshot
- append_asset_equity_snapshot
- append_ai_decision
- append_system_event
- read_system_state
- update_system_state
- set_halt
- clear_halt_explicitly
- reconcile_cash
- reconcile_realized_pnl

These are behavioral contracts, not final Python method names.

A.2 does not create a second parallel accounting engine.

## Migration design

Migration remains separate from schema design.

Before a real migration:

1. discover exact source files and versions
2. calculate hashes of every source file
3. create backup
4. verify backup readability
5. create a temporary SQLite database outside the live path
6. migrate into the temporary copy
7. validate row counts
8. validate identifiers
9. validate cash reconciliation
10. validate realized PnL reconciliation
11. compare pre/post financial values
12. test restart from the migrated copy
13. test backup restore
14. produce migration report
15. HARD STOP

Only after explicit approval may a later phase replace or supplement live persistence.

## Rollback design

Before real migration:

- keep original JSON and JSONL files untouched
- do not overwrite live state
- use a separate temporary SQLite destination
- preserve source file hashes

If validation fails:

- discard temporary database
- retain original persistence
- keep system on pre-migration storage
- record the failure

If future live cutover fails:

- HALT new entries
- stop SQLite writer
- preserve failed database for audit
- restore the verified backup
- verify reconciliation again before resuming

## Retention

Financial records are not candidates for silent retention deletion.

Potential retention policies apply only to non-financial streams such as:

- verbose system events
- old operational metrics
- bounded AI decision history
- caches

Retention implementation is deferred.

## Explicit non-goals of A.2

A.2 does not:

- create data/live/trading.db
- migrate live data
- modify existing JSON or JSONL formats
- change cash semantics
- change realized PnL semantics
- change PaperBroker
- change REALISTIC_V2 execution
- change Phase 12 capital admission
- change BTC LEGACY_V1
- change Flutter
- switch FastAPI to SQLite
- add a dependency

## Next implementation stage

Phase 13 A.3 should implement the repository foundation against a temporary or in-memory database only.

It must be test-first.

No production migration is authorized by A.2.
