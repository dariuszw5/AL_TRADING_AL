# PHASE 14 A.8 — ENTRYPOINT APPLICATION BINDING INTEGRATION

A.8 integrates the A.7 application binding adapter into the dedicated
Phase 14 cutover entrypoint.

## Dependency resolution precedence

The dedicated entrypoint now resolves SQLite construction dependencies in
this order:

1. explicit sqlite_bundle_kwargs_provider
2. explicit paper_dependency_context
3. explicit application_binding_inputs converted by the A.7 adapter
4. fail closed with SQLITE BUNDLE DEPENDENCY PROVIDER REQUIRED

The default legacy mode touches none of these dependency inputs.

## Path safety ordering

The A.2 TEMP/TEST path guard still executes before application binding.

Therefore the real data/live/trading.db path and every candidate beneath
the live directory are rejected before application services are created.

## Application binding failure

If A.7 rejects missing or ambiguous inputs, A.8 returns
EXIT_APPLICATION_BINDING_FAILED and performs no SQLite runtime construction.

No fallback market data, decision, FX/PLN evidence or execution evidence is
fabricated.

## TEMP SQLite proof

A real Phase14ApplicationBindingInputs object is passed into the dedicated
entrypoint against a fresh TEMP Phase 13 SQLite database.

The path is:

A.7 application adapter
-> A.5 real paper dependency composition
-> A.3 SQLite cutover factory
-> Phase 13 SQLite-only runtime bundle
-> immediate close

run_cycle is never called.

The TEMP database remains HALTED with INITIAL_CASH only and matching cash
and realized reconciliation.

No JSON or JSONL durable files are created.

## Existing behavior

Default mode remains legacy.

Real data/live/trading.db remains unchanged and HALTED.

A.8 does not authorize live writer wiring or HALT clear.

## Next

A.9 should define the production application-binding provider for the
remaining explicit market-data, decision, FX and evidence dependencies,
with construction-only tests and no live cycle.

HARD STOP remains required before real live DB writer wiring or HALT clear.
