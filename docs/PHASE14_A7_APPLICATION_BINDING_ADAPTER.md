# PHASE 14 A.7 — APPLICATION BINDING ADAPTER

A.7 converts the A.6 repository inventory into a fail-closed application
binding adapter for Phase14PaperDependencyContext.

## Automatically bound components

A.6 identified these application components unambiguously enough for safe
defaults:

- MarketSessionService
- SystemClock
- get_asset

A.7 binds those components by default.

## Explicit components

A.6 found multiple or ambiguous candidates for market data, decisions and
FX, and no dedicated evidence resolver definitions.

Therefore A.7 deliberately requires explicit:

- market_data_service
- decision_provider
- fx_conversion_resolver
- estimated_exit_fee_resolver
- realized_quotes_resolver
- execution_evidence_resolver
- realized_evidence_resolver

Missing dependencies fail closed.

No fallback market price, decision, FX rate, PLN conversion or execution
evidence is fabricated.

## TEMP SQLite integration proof

The A.7-built context is passed through the existing A.5 composition and
A.4 dedicated entrypoint against a fresh TEMP Phase 13 SQLite database.

The real Phase 13 bundle constructs and immediately closes.

No run_cycle occurs.

The TEMP database remains HALTED with no orders, executions, positions or
trades and only INITIAL_CASH.

No JSON or JSONL durable writer is created.

## Existing runtime behavior

A.7 does not modify existing Phase 10/11/12 entrypoints, the A.4 cutover
entrypoint, PaperBroker or RealisticPaperRuntime.

The real data/live/trading.db remains unchanged.

## Next

A.8 should integrate this application binding adapter into the dedicated
Phase 14 entrypoint through an explicit application binding provider.

A.8 must still perform construction only on TEMP/TEST SQLite.

HARD STOP remains required before real live DB writer wiring or HALT clear.
