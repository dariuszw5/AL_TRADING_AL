# PHASE 14 A.2 — OPT-IN SQLITE CUTOVER CONSTRUCTION SEAM

A.2 introduces an explicit runtime-construction selector without changing
the current Phase 10/11/12 entrypoints.

## Default contract

The default mode is legacy.

When no mode is supplied:

- only legacy_builder is called
- sqlite_builder is not called
- no SQLite database path is required
- the current application construction path is unchanged

## SQLite opt-in contract

SQLite mode is explicit.

In A.2 it is restricted to TEMP/TEST use:

- sqlite_database_path is required
- the database must already exist
- the exact real live database is rejected
- every candidate under the real live database directory is rejected
- legacy_builder is not called
- sqlite_builder receives resolved database_path and live_database_path

The seam itself does not open the database, clear HALT or run a cycle.

## Why the existing Phase 12 entrypoint is unchanged

A.1 identified scripts/run_phase12_capital_accounting_smoke.py as the
current end of the Phase 10 -> 11 -> 12 accounting chain.

A.2 deliberately does not patch that file yet.

This keeps the default production behavior unchanged while establishing a
tested cutover selector that can be integrated in A.3.

## Next

A.3 may integrate this selector into a dedicated opt-in Phase 14
construction entrypoint or a narrowly scoped Phase 12 seam.

A.3 must still use TEMP/TEST SQLite only.

HARD STOP remains required before real data/live/trading.db writer wiring
or real HALT clear.
