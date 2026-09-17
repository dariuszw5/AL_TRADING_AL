# Phase 10 A.13 - Persisted Controlled Accounting Entrypoint

Hard-stop approval 10B authorizes startup metadata persistence for a
controlled Phase 10 REALISTIC_V2 accounting path.

## Additive entrypoint

A.13 adds:

`scripts/run_phase10_persisted_accounting_smoke.py`

The existing `scripts/run_phase10_accounting_smoke.py` is not modified.

This preserves all pre-existing entrypoint assertions and keeps the
earlier non-persistent smoke path available as diagnostic evidence.

## Explicit state directory

`--state-dir` is required.

The only new persistent file created by this entrypoint is:

`<state-dir>/phase10_startup_metadata.jsonl`

The path is not inferred from `data/live_state`.

## Ordering contract

Before any PaperBroker cycle:

1. construct the controlled REALISTIC_V2 runtime,
2. compute the Phase 10 startup metadata and global config hash,
3. verify every existing startup-metadata record,
4. append the new startup record,
5. fsync it,
6. read and verify the complete metadata journal again,
7. verify the appended record hash and global config hash,
8. only then allow `run_cycle()`.

Therefore metadata persistence or integrity failure blocks the paper
execution cycle.

## Construction-only persisted mode

Without `--run-cycle`, the new entrypoint still writes and verifies one
startup metadata record, but it does not:

- run market-data fetch,
- run FX prefetch,
- submit a PaperBroker order,
- send a real exchange order.

This mode is used for deterministic integration verification.

## Stateful paper cycle

A paper cycle requires both:

- `--run-cycle`
- `--confirm-paper-accounting-smoke`

The broker remains PaperBroker.

There is no real-exchange order path.

## Existing files not changed

A.13 does not modify:

- `execution_journal.jsonl` format,
- `state.json` format,
- PaperBroker,
- RealisticPaperRuntime,
- execution semantics,
- LEGACY_V1,
- frozen strategy parameters,
- existing assertions,
- `data/live_state`,
- SQLite.

## Remaining debt

Accounting result persistence is still not implemented.

Cash / ledger accounting remains unresolved.

The original non-persistent A.5 smoke entrypoint remains a diagnostic
tool and is not the persisted startup path.

Production readiness must therefore be assessed against the persisted
A.13 entrypoint, not the older A.5 diagnostic command.
