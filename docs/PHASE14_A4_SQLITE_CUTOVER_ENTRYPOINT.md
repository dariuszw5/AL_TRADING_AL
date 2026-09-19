# PHASE 14 A.4 — DEDICATED OPT-IN SQLITE CUTOVER ENTRYPOINT

A.4 adds scripts/run_phase14_sqlite_cutover.py as a dedicated Phase 14
construction-only entrypoint.

## Default behavior

Without arguments the entrypoint selects legacy mode and performs no SQLite
construction.

It does not replace or modify the existing Phase 10/11/12 entrypoints.

## Explicit SQLite construction

SQLite construction requires all of:

1. --mode sqlite
2. --sqlite-db pointing to an existing TEMP/TEST database
3. --confirm-temp-sqlite-construction
4. an explicit SQLite bundle dependency provider

Before dependency acquisition the A.2 path guard runs.

The real data/live/trading.db path and every candidate beneath its live
directory remain forbidden.

## Construction-only guarantee

On successful SQLite construction:

- A.3 build_phase14_runtime constructs the Phase 13 SQLite-only bundle
- the bundle is immediately closed
- run_cycle is never called
- HALT clear is never requested
- no real order path is used

## Scope

A.4 still does not provide production dependency wiring.

A.5 should define the real paper-runtime dependency composition for this
dedicated entrypoint, still on TEMP/TEST SQLite only, and prove construction
against a valid temporary Phase 13 database.

HARD STOP remains required before real data/live/trading.db writer wiring
or HALT clear.
