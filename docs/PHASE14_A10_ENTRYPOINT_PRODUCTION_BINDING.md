# PHASE 14 A.10 — ENTRYPOINT PRODUCTION BINDING INTEGRATION

A.10 integrates the A.9 Phase14ProductionBindingInputs object directly into
the dedicated Phase 14 cutover entrypoint.

## Dependency resolution precedence

The dedicated entrypoint now resolves SQLite construction dependencies in
this order:

1. explicit sqlite_bundle_kwargs_provider
2. explicit paper_dependency_context
3. explicit application_binding_inputs
4. explicit production_binding_inputs converted by A.9 and then A.7
5. fail closed

Higher-priority dependency sources are never inspected through lower-priority
objects.

## Path safety ordering

The A.2 TEMP/TEST SQLite path guard still executes before production binding.

The real data/live/trading.db path is rejected before A.9 validation and
before any production resolver method can be invoked.

## Production binding failure

Invalid Phase14ProductionBindingInputs return
EXIT_PRODUCTION_BINDING_FAILED.

No SQLite runtime construction occurs after a production binding failure.

## Construction-only integration proof

The tested path is:

A.9 production binding provider
-> A.7 application binding adapter
-> A.5 real paper dependency composition
-> A.3 SQLite cutover factory
-> Phase 13 SQLite-only runtime bundle
-> immediate close

The test uses existing ProductionFxResolver and BrokerExitFeeEstimator object
types without calling provider I/O.

No run_cycle occurs.

The TEMP database remains HALTED with INITIAL_CASH only.

No JSON or JSONL durable files are created.

## Existing behavior

Default mode remains legacy.

A.9 source, A.7 source, production_resolvers.py, PaperBroker and runtime.py
remain unchanged.

The real data/live/trading.db remains unchanged.

## Next

A.11 should perform a final construction-only readiness audit for the
remaining explicit market-data, decision and evidence dependencies and
define the exact activation boundary.

HARD STOP remains required before any real live DB writer wiring, live
run_cycle or HALT clear.
