# Phase 12 A.7 — Startup Metadata Persistence

HARD STOP 12A requires Phase 12 capital admission to have its own auditable
startup fingerprint without changing the Phase 10 startup metadata format.

A.7 adds a separate append-only JSONL journal:

`phase12_startup_metadata.jsonl`

The file is not wired into the command-line smoke entrypoint yet.

## Persisted evidence

Each record persists:

- Phase 12 journal schema,
- UTC startup timestamp,
- Phase 12 metadata schema,
- execution config hash,
- Phase 10 global config hash,
- Phase 12 global config hash,
- asset-registry hash,
- paper mode,
- Phase 10 feature flags,
- Phase 12 feature flags,
- Phase 10 runtime policy,
- approved Phase 12 capital policy,
- inherited limitations,
- canonical SHA256 record hash.

## Durability and integrity

The journal is:

- append-only,
- canonical JSON,
- fsynced before close,
- hash-verified on every read,
- fail-closed on blank, invalid JSON or tampering.

A.7 deliberately follows the existing Phase 10 startup-metadata persistence
pattern and does not alter that file or format.

## Boundaries

A.7 does not modify:

- `state.json`,
- `execution_journal.jsonl`,
- `phase10_startup_metadata.jsonl`,
- `phase10_realized_accounting.jsonl`,
- `phase11_cash_ledger.jsonl`,
- `PaperBroker`,
- runtime execution semantics,
- LEGACY_V1,
- frozen strategy,
- public all-asset runner.

The next step can add a controlled BTCUSDT Phase 12 entrypoint that persists
both existing Phase 10 startup metadata and the separate Phase 12 startup
metadata before any paper cycle.
