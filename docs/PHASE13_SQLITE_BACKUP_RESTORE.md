# PHASE 13 A.6 — SQLITE BACKUP AND RESTORE

## Status

Implemented and verified using temporary SQLite databases only.

No production database was created.
No JSON or JSONL data was migrated.
No runtime was switched to SQLite.

## Backup mechanism

SQLite backups use the native sqlite3 connection backup API.

This is preferred over copying the main database file directly because the future writer uses WAL mode.

The backup operation is refused while the repository has an active atomic_cycle.

The backup destination must not already exist.

The source database cannot be used as its own backup destination.

## Backup verification

Every backup is verified before being accepted.

Verification includes:

- PRAGMA integrity_check
- PRAGMA foreign_key_check
- required table inventory
- schema_version presence
- expected schema version

Invalid backup files fail closed.

Foreign-key-invalid backups fail closed.

## Restore

restore_from_backup first verifies the backup source.

The restore destination must not already exist.

Restore uses SQLite backup API to create a new database.

The restored database is verified again before being returned as a writer repository.

## Snapshot semantics

A backup is a point-in-time snapshot.

Writes committed to the source after the backup do not appear in the backup.

## State preserved

Tests verify preservation of:

- orders
- portfolio transactions
- cash state
- persistent HALT
- HALT reason
- last processed timestamp
- schema identity

The restored database also passes cash reconciliation.

## Live database

data/live/trading.db was not created.

All backup and restore paths in A.6 are pytest temporary paths.

## Migration

A.6 is not a migration.

No legacy persistence was read for migration.
No legacy persistence was modified.
No cutover occurred.

The next stage may build a migration dry-run against copies only.

Real migration remains behind HARD STOP.
