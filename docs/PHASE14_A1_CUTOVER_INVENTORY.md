# PHASE 14 A.1 — LIVE SQLITE CUTOVER INVENTORY

Phase 14 begins with an audit-only inventory from Phase 13 commit cd5b186.

A.1 does not wire data/live/trading.db into runtime, does not open the
live database as a runtime writer, does not clear HALT and does not run
paper trading.

The repository was scanned dynamically for current production entrypoints,
runtime construction, Phase 10/11/12 wrappers, legacy JSON/JSONL durable
writers and any existing Phase 13 SQLite bundle production reference.

The exact inventory is stored in:
docs/evidence/PHASE14_A1_CUTOVER_INVENTORY.txt

A.2 may add only an explicit opt-in construction seam on TEMP/TEST SQLite.
The default path must remain unchanged.

HARD STOP remains required before:
- real data/live/trading.db writer wiring
- real HALT clear
- paper-live activation
- any real-money order path
