# Phase 09 A.13 - Runtime Feature Flag Resolution

Phase 09 feature flags are resolved explicitly at the REALISTIC_V2
entrypoint boundary.

Resolved flags:
- AL_TRADING_REALISTIC_V2_ENABLED
- AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED
- AL_TRADING_REALISTIC_V2_PAPER_MODE
- AL_TRADING_FX_ENABLED
- AL_TRADING_PLN_ACCOUNTING_ENABLED

The resolver reuses the existing A.11 normalized feature-flag contract
through build_phase09_feature_flags(). It does not create a second hash
algorithm.

scripts/run_realistic_paper.py remains PRE-FLIGHT ONLY. It reports the
resolved FX and PLN/accounting flags but still submits no orders.

A.13 does not modify:
- scripts/run_paper_live.py
- scripts/run_realistic_smoke_fill.py
- PaperBroker
- RealisticPaperRuntime
- execution journal
- state store
- config_fingerprint.py
- frozen BTC strategy
- LEGACY_V1
- data/live_state
- SQLite

Actual FX/PLN accounting runtime integration remains A.14.