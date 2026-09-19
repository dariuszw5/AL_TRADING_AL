# PHASE 14 A.3 — SQLITE CUTOVER FACTORY

A.3 connects the Phase 14 A.2 cutover selector to the actual Phase 13
build_sqlite_only_runtime_bundle factory.

## Default path

Default mode remains legacy.

When mode is omitted:

- only legacy_builder is called
- SQLite bundle dependencies are not required
- build_sqlite_only_runtime_bundle is not called
- existing Phase 10/11/12 entrypoints remain unchanged

## Explicit SQLite path

When mode=sqlite:

1. Phase 14 validates the exact Phase 13 bundle dependency set.
2. A.2 path safety rules run.
3. The exact live database path is rejected.
4. Every candidate under the live directory is rejected.
5. Only after those guards pass is build_sqlite_only_runtime_bundle called.

This is now a real construction bridge from the Phase 14 seam into the
Phase 13 SQLite-only runtime implementation.

## Scope boundary

A.3 still does not patch any existing production entrypoint.

A.3 does not open data/live/trading.db as a runtime writer, does not clear
HALT and does not execute a paper cycle.

## Next

A.4 should integrate build_phase14_runtime into a dedicated Phase 14
entrypoint with explicit CLI confirmation, still using TEMP/TEST SQLite
only.

HARD STOP remains required before real live database writer wiring or HALT
clear.
