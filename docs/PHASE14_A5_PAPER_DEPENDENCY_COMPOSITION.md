# PHASE 14 A.5 — REAL PAPER DEPENDENCY COMPOSITION

A.5 composes the real paper-runtime core used by the Phase 13 SQLite-only
bundle and connects it to the dedicated Phase 14 A.4 construction
entrypoint.

## Real components

The composition creates:

- real PaperBroker
- FixedBpsSlippage
- PaperMode.REALISTIC_PAPER
- real Phase09RuntimeAccountingBridge
- real RealizedFxSelectionPolicy
- real RealizedFxBooker
- real RealisticV2SQLiteMapper

PaperBroker is constructed with execution_journal=None because SQLite is
the sole durable authority on this path.

## Explicit injected dependencies

A.5 does not fabricate external evidence.

These remain explicit injected dependencies:

- market_data_service
- market_session_service
- decision_provider
- asset_resolver
- FX conversion resolver
- exit-fee resolver
- realized FX quote resolver
- execution evidence resolver
- realized evidence resolver
- clock

This prevents construction code from inventing market prices or PLN/FX
values.

## TEMP SQLite proof

A.5 bootstraps a temporary Phase 13 SQLite database and invokes the A.4
dedicated entrypoint with:

- mode=sqlite
- explicit temp construction confirmation
- Phase14PaperDependencyContext

The real Phase 13 SQLite-only runtime bundle is constructed and immediately
closed.

No run_cycle occurs.

The temporary database remains HALTED, contains only INITIAL_CASH and has
matching cash and realized-PnL reconciliation.

No JSON or JSONL durable files are created.

## Existing application behavior

Existing Phase 10/11/12 entrypoints are unchanged.

The default Phase 14 CLI path remains legacy.

The real data/live/trading.db is unchanged and remains HALTED.

## Next

A.6 should bind the actual application market/session/decision/FX services
into Phase14PaperDependencyContext, still without running a live cycle.

HARD STOP remains required before real data/live/trading.db writer wiring
or HALT clear.
