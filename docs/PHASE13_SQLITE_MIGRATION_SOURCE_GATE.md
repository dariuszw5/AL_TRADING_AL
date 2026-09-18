# PHASE 13 A.7 — COPY-ONLY MIGRATION SOURCE GATE

## Purpose

A.7 validates actual persistence sources before any financial migration.

## Safety rule

Existing REALISTIC_V2 runtime evidence must not be converted into a
financial SQLite ledger by inventing missing settled cash.

The Phase 11 cash ledger remains the authoritative settled-cash source.

## Procedure

A.7:

1. discovers REALISTIC_V2 persistence directories,
2. hashes original files,
3. copies them to a temporary dry-run directory,
4. verifies copy hashes,
5. validates copied files with the current production readers,
6. checks source completeness,
7. verifies original hashes remain unchanged,
8. explicitly excludes legacy data/live_state from authoritative cash,
9. runs repository regression,
10. runs full offline regression,
11. verifies BTC LEGACY_V1 golden,
12. creates no SQLite production database,
13. migrates no financial records.

## Required current source set

For a current Phase 12 financial source to be eligible for the next
mapping dry-run, A.7 expects:

- state.json
- execution_journal.jsonl
- phase10_startup_metadata.jsonl
- phase10_realized_accounting.jsonl
- phase11_cash_ledger.jsonl
- phase12_startup_metadata.jsonl

## Fail-closed condition

If runtime evidence exists without phase11_cash_ledger.jsonl, the source
is classified as blocked.

No initial cash value is fabricated.

No legacy live_state balance is promoted to authoritative settled cash.

## Boundary

A.7 is a source-readiness gate.

It does not create data/live/trading.db.
It does not wire SQLite into runtime.
It does not perform cutover.
It does not migrate real financial data.

A mapping migration dry-run is allowed only for a source set that passes
this gate.

Real migration remains behind HARD STOP.
