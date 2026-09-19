# PHASE 14 A.9 — PRODUCTION APPLICATION BINDING PROVIDER

A.9 adds a production-facing provider that reuses existing Phase 10
production accounting resolver objects without duplicating their logic.

## Production resolver bindings

A.9 requires concrete existing instances of:

- ProductionFxResolver
- BrokerExitFeeEstimator

Those are bound into A.7 application inputs as:

- fx_conversion_resolver = ProductionFxResolver.conversion_for
- realized_quotes_resolver = ProductionFxResolver.resolve_realized_quotes
- estimated_exit_fee_resolver = BrokerExitFeeEstimator

The provider only passes existing bound methods/callables. It does not
invoke provider I/O during construction.

## Explicit dependencies retained

A.6 showed ambiguity for market-data and decision-provider choice, and no
dedicated production mapper-evidence resolver definitions.

Therefore A.9 deliberately keeps these explicit:

- market_data_service
- decision_provider
- execution_evidence_resolver
- realized_evidence_resolver

Wrong or missing types fail closed.

## Integration proof

A.9 output is accepted by the A.7 binding adapter and the A.8 dedicated
entrypoint.

Against a fresh TEMP Phase 13 SQLite database the real SQLite-only bundle
constructs and immediately closes.

No run_cycle occurs.

The TEMP database remains HALTED and contains only INITIAL_CASH.

No JSON or JSONL durable files are created.

## Existing behavior

A.9 does not modify:

- ProductionFxResolver
- BrokerExitFeeEstimator
- PaperBroker
- RealisticPaperRuntime
- the Phase 14 entrypoint

The real data/live/trading.db remains unchanged.

## Next

A.10 should integrate Phase14ProductionBindingInputs directly into the
dedicated Phase 14 entrypoint, preserving the existing dependency
precedence and construction-only safety boundary.

HARD STOP remains required before real live DB writer wiring or HALT clear.
