# Phase 10 A.15 - Append-only Realized Accounting Journal

Hard-stop approval 10C authorizes durable persistence of completed
realized PLN bookings in a new append-only file under an explicitly
selected Phase 10 state directory.

## File

The journal filename is:

`phase10_realized_accounting.jsonl`

It is separate from:

- `execution_journal.jsonl`,
- `state.json`,
- `phase10_startup_metadata.jsonl`.

No existing persistence format is modified.

## Persistence point

The existing REALISTIC_V2 execution cycle and Phase 10 accounting cycle
run first.

Only when an accounting asset result contains a successful
`realized_result` is a realized accounting record persisted.

The persistence wrapper does not modify the execution result or the
accounting calculation.

A persistence failure is surfaced fail-closed to the controlling
entrypoint after the already-completed paper execution/accounting cycle.

## Identity and idempotency

The booking identity is:

- asset id,
- position id,
- entry execution id,
- exit execution id.

The SHA256 of that identity is the `booking_key`.

Before append, the complete existing journal is verified.

If the same booking key already exists with exactly the same semantic
payload, the operation is idempotent and does not append a second line.

If the same booking key exists with different accounting evidence or
amounts, persistence fails with
`REALIZED_ACCOUNTING_IDEMPOTENCY_CONFLICT`.

Duplicate booking keys already present in the file are treated as
corruption and fail closed.

This provides deterministic sequential retry/restart idempotency.

Concurrent multi-process append arbitration is not introduced in A.15
and must not be claimed as supported.

## Record evidence

Each record persists:

- asset id,
- position id,
- entry execution id,
- exit execution id,
- UTC close timestamp,
- native currency when present in the accounting record,
- net realized native PnL,
- realized FX rate,
- realized FX path,
- net realized PLN PnL,
- full normalized FX booking evidence,
- full normalized realized accounting evidence,
- accounting limitations,
- exit execution config hash,
- Phase 10 global config hash,
- UTC persistence timestamp,
- booking key,
- record SHA256.

Decimals are persisted as strings to avoid binary floating-point
reinterpretation.

## Integrity and durability

Each record hash covers the canonical JSON payload.

Append uses OS append mode followed by `fsync`.

After append, the journal is read and verified again.

Malformed JSON, hash mismatch, identity mismatch or duplicate booking key
fails closed.

## Entrypoint wiring

`scripts/run_phase10_persisted_accounting_smoke.py` is wired to this
journal only for an actual `--run-cycle`.

An OPEN cycle with no realized booking does not create
`phase10_realized_accounting.jsonl`.

A successful CLOSE with realized accounting creates exactly one booking
record.

## Boundaries unchanged

A.15 does not modify:

- execution-journal format,
- state-store format,
- startup-metadata format,
- PaperBroker,
- RealisticPaperRuntime,
- fill/slippage/fee execution semantics,
- LEGACY_V1,
- frozen strategy parameters,
- existing assertions,
- `data/live_state`,
- SQLite.

A.15 is not a cash ledger and does not persist unrealized MTM snapshots.
