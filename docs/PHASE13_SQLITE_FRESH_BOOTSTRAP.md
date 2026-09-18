# PHASE 13 A.8 — FRESH SQLITE BOOTSTRAP CONTRACT

## Status

Implemented and tested using temporary SQLite databases only.

No data/live/trading.db was created.
No legacy or smoke-state financial data was migrated.
No runtime was wired to SQLite.

## Why fresh bootstrap exists

Phase 13 A.7 found no eligible authoritative source set for financial
migration.

The existing REALISTIC_V2 smoke state contains runtime execution evidence
but does not contain the authoritative Phase 11 cash ledger or the full
Phase 10/12 accounting metadata set.

Therefore the system must not fabricate settled cash from legacy state,
configuration defaults or historical smoke files.

## Fresh bootstrap contract

A fresh database requires explicit:

- database path
- initial_cash_pln
- bootstrap_id
- creation timestamp

The initial cash must be finite and non-negative.

The bootstrap creates exactly one INITIAL_CASH portfolio transaction and
sets system_state.cash_balance_pln to the same explicit amount.

Cash reconciliation must pass before bootstrap succeeds.

## Safety state

A fresh database starts HALTED with:

FRESH_BOOTSTRAP_REQUIRES_EXPLICIT_ACTIVATION

This prevents a freshly-created ledger from admitting new entries before
a later explicit activation/cutover procedure.

## Empty inherited state

Fresh bootstrap creates no:

- orders
- executions
- positions
- trades
- equity snapshots
- asset equity snapshots
- AI decisions

The last processed timestamp remains NULL.

No legacy live_state or smoke-state records are imported.

## Failure behavior

Existing destination databases are never overwritten.

If bootstrap fails after database creation, the partial database and
SQLite WAL/SHM sidecars are removed.

## Backup and restore

A freshly bootstrapped database remains valid through the Phase 13 A.6
backup/restore contract and retains:

- explicit initial cash
- persistent HALT
- NULL processed timestamp
- successful cash reconciliation

## Production boundary

A.8 defines and tests bootstrap semantics only.

Creation of data/live/trading.db is NOT authorized by this phase.

Any real database creation or runtime cutover remains behind HARD STOP.
