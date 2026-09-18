# ADR — SQLITE LEDGER SCHEMA

## Status

PROPOSED FOR IMPLEMENTATION.

Production migration remains NOT APPROVED.

## Decision

Use SQLite as the future durable unified paper-live ledger.

Target path:

data/live/trading.db

SQLite is already available through Python standard library.

No new dependency is required.

## Writer model

There will be one financial writer:

paper-live runtime.

FastAPI and other readers use read-only connections.

## Connection policy

Required:

- WAL
- busy_timeout
- foreign_keys ON
- synchronous FULL

## Financial values

Financial decimal values are stored as canonical decimal TEXT.

Repository code uses Python Decimal.

This avoids introducing a silent floating-point or rounding policy during migration.

## Identity

client_order_id is UNIQUE.

execution_id is unique through its primary key.

transaction_id is unique through its primary key.

trade_id and position_id are unique through their primary keys.

Idempotent replay returns the previously persisted logical result.

Identifier reuse with conflicting content fails closed.

## Atomicity

Processed timestamp and financial effects of one paper-live cycle belong to one database transaction.

A processed timestamp must never be persisted ahead of the corresponding financial state.

## Reconciliation

Cash invariant:

portfolio transaction history equals materialized cash balance.

Realized invariant:

trade realized PnL equals REALIZED_PNL ledger accounting.

Mismatch causes persistent HALT for new entries.

Existing position management remains available.

## Migration

Real migration is not part of this ADR approval.

Required first:

- repository implementation
- tests
- backup test
- restore test
- migration dry-run on a copy
- pre/post diff
- reconciliation
- explicit HARD STOP approval

## Consequences

Benefits:

- one transaction boundary
- explicit idempotency
- durable HALT state
- auditable financial ledger
- consistent read model for future API

Costs:

- migration complexity
- repository layer required
- backup and recovery procedures required
- cutover must be conservative

## Rollback

Before cutover, existing persistence remains authoritative.

A failed dry-run is discarded.

A failed future cutover requires HALT, preservation of the failed DB for audit, restoration from verified backup and reconciliation before resume.
