# Phase 12 A.6 — Controlled Capital Admission Runtime Wiring

HARD STOP 12A authorizes cash-backed capital admission for new LONG ENTRY in
the controlled REALISTIC_V2 path.

A.6 adds an optional pre-broker admission hook to `RealisticPaperRuntime` and a
Phase 12 wiring layer. The hook defaults to `None`, so existing callers retain
prior behavior unless Phase 12 explicitly installs the provider.

For `ENTRY + BUY`, the hook reads settled cash only from the Phase 11 cash
ledger, uses the Phase 10 prefetched FX cache plus the A.4 BTCUSDT exposure
calculator, and applies the A.3 cash-backed limit before any broker call.
Rejected admission never creates an order and never reaches `PaperBroker`.

EXIT bypasses capital admission completely. SELL ENTRY also bypasses the Phase
12 hook, leaving the existing realistic-paper synthetic-short gate unchanged.

A.6 adds additive runtime status `CAPITAL_REJECTED` and carries admission
evidence in `RuntimeAssetResult.capital_admission`.

`wire_phase12_capital_runtime()` requires the Phase 12 feature flag, builds the
Phase 12 startup fingerprint, reuses Phase 11 settled cash and Phase 10 FX,
and installs the provider on the base runtime. No Phase 12 startup file is
persisted yet.

A.6 does not add a public all-asset runner, margin, collateral, leverage, short
financing, reservation persistence, cash debit on OPEN, SQLite, or changes to
Phase 10/11 persistence formats.
