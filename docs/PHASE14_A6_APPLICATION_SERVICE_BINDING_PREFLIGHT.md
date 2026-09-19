# PHASE 14 A.6 — APPLICATION SERVICE BINDING PREFLIGHT

A.6 is an audit-only step.

A.5 established the exact Phase14PaperDependencyContext contract.
A.6 inventories the current application repository for concrete candidates
that can satisfy that contract.

The inventory covers:

- market data
- market session
- decision provider
- FX services/resolvers
- asset registry/resolver
- clock
- execution/realized evidence

The exact repository-derived inventory is stored in:

docs/evidence/PHASE14_A6_APPLICATION_SERVICE_BINDING_PREFLIGHT.txt

A.6 does not modify runtime/source code, does not run a paper cycle, does
not open data/live/trading.db as a runtime writer and does not clear HALT.

A.7 must use the exact A.6 evidence to implement a narrow application
binding adapter. Missing or ambiguous bindings must fail closed instead of
inventing market, execution or PLN/FX evidence.

HARD STOP remains required before real live database writer wiring or
activation.
