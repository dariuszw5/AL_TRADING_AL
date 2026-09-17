# Phase 10 A.12 - Append-only Startup Metadata Journal

## Purpose

A.11 proved that realized PLN accounting can recover the complete entry
Execution from the existing execution journal after process restart.

The next unresolved reproducibility requirement is startup metadata
persistence.

A.12 adds the persistence primitive only.

It does not yet wire that primitive into an entrypoint.

## New file scope

`StartupMetadataJournal` writes to an explicitly supplied path.

The intended future production path is a new file such as:

`phase10_startup_metadata.jsonl`

inside the explicitly selected Phase 10 state directory.

A.12 does not write to:

- `execution_journal.jsonl`,
- `state.json`,
- `data/live_state`,
- any SQLite database.

## Append-only format

The format is JSONL.

Each line is a complete startup metadata record containing:

- startup timestamp in UTC,
- Phase 10 metadata schema,
- PaperBroker execution config hash,
- Phase 09 base global config hash,
- Phase 10 global config hash,
- asset registry hash,
- paper mode,
- resolved feature flags,
- complete resolved runtime policy,
- startup limitations,
- SHA256 record hash.

Writes use append mode, flush to the OS and `fsync`.

Existing records are not overwritten.

## Integrity

Each record contains a SHA256 over its canonical JSON payload.

`read_records()` verifies every record.

Malformed JSON, blank records, schema mismatch or hash mismatch fail
closed.

This is integrity evidence, not cryptographic authentication.

## Time

Startup timestamps must be timezone-aware.

They are normalized to UTC before persistence.

Production uses the existing Clock abstraction.

Tests use injected deterministic clocks.

## Security / privacy

The startup metadata record intentionally contains configuration
fingerprints and policy values only.

It does not persist API keys, credentials, market-data payloads, account
identifiers or user secrets.

## Boundaries unchanged

A.12 does not modify:

- PaperBroker,
- execution semantics,
- RealisticPaperRuntime,
- execution journal format,
- state-store format,
- LEGACY_V1,
- frozen strategy parameters,
- existing assertions,
- existing live_state,
- SQLite,
- accounting-record persistence.

## Next step

A later Phase 10 step may wire this append-only metadata journal into a
new controlled startup path.

Existing Phase 10 smoke-entrypoint assertions remain unchanged.

No existing entrypoint is silently changed by A.12.
