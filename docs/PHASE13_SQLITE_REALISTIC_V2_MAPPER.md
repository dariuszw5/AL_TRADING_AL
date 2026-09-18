# PHASE 13 A.17 — REALISTIC_V2 SQLITE RESULT MAPPER

A.17 maps the existing REALISTIC_V2 runtime/accounting result shape to
the Phase 13 SQLite persistence contracts.

The expected result path is:

RuntimeAccountingCycleResult
-> execution_cycle.results[asset_id]
-> broker_result
-> order / execution / position

EXIT financial evidence is read from:

accounting_results[asset_id]
-> realized_result
-> accounting_record / fx_booking

No missing PLN/FX cost evidence is fabricated.

Two explicit callbacks are required:

1. execution_evidence_resolver
   - fee_pln
   - fx_path
   - fx_rate
   - fx_provider
   - fx_timestamp_utc
   - fx_quality

2. realized_evidence_resolver
   - fees_pln
   - spread_cost_pln
   - slippage_pln
   - fx_pair
   - fx_provider
   - fx_timestamp_utc
   - fx_quality

Missing evidence fails closed.

Realized trade and REALIZED_PNL transaction identities are deterministic
SHA-256 identities over:

asset_id + position_id + entry_execution_id + exit_execution_id

A.17 also corrects A.16 NOOP reporting:

NOOP -> persisted=False

ENTRY and EXIT behavior is unchanged.

Integration proves:

- actual REALISTIC_V2-shaped ENTRY result -> SQLite ENTRY persistence
- restart
- persistent HALT
- actual REALISTIC_V2-shaped EXIT + accounting result
- atomic close + realized settlement
- cash update
- HALT remains active
- NOOP creates no durable rows

data/live/trading.db is unchanged.
Default RealisticPaperRuntime is unchanged.
PaperBroker is unchanged.
Trading is not activated.

Next: A.18 composition guard proving injected mode has no legacy JSON/JSONL
durable writers and can restore SQLite positions/execution evidence for
runtime restart.

A separate HARD STOP remains required before real live database cutover.
