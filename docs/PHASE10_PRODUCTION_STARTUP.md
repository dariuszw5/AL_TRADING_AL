# Phase 10 A.4 - Fingerprinted Production Accounting Wiring

## Purpose

A.4 joins the already verified Phase 10 resolver and scheduler layers into
one production accounting construction contract.

It still does not enable the public REALISTIC_V2 execution entrypoint.

## Explicit runtime policy

`Phase10AccountingRuntimePolicy` requires the caller to provide:

- realized market FX maximum age,
- realized daily-reference maximum age in days,
- FX prefetch timeout,
- FX prefetch worker limit,
- REALISTIC_V2 cycle timeout.

There is intentionally no default for the realized daily-reference age.

A.4 therefore does not silently choose an accounting policy that was not
previously accepted.

## Accepted Phase 09 MTM policy

The startup fingerprint also records the already accepted production MTM
freshness thresholds from Phase 09:

- weekday max FX age: 7200 seconds,
- weekend max FX age: 7200 seconds,
- unavailable boundary: 345600 seconds.

## Cycle-budget guard

The FX prefetch timeout must be strictly less than the complete cycle
timeout.

A prefetch timeout above 50 percent of the cycle timeout is allowed only
with an explicit startup limitation:

`FX_PREFETCH_BUDGET_ABOVE_50_PERCENT`

The production entrypoint can therefore display or reject that policy
before a live cycle is started.

## Global configuration fingerprint

A.4 keeps the existing PaperBroker execution hash untouched.

It also keeps the existing Phase 09 base global hash contract untouched.

The Phase 10 startup hash is derived from:

- the Phase 09 base global config hash,
- the complete resolved Phase 10 accounting runtime policy.

Therefore a change to:

- asset registry,
- PaperBroker execution configuration,
- paper mode,
- feature flags,
- MTM freshness policy,
- realized FX policy,
- FX prefetch scheduling,
- cycle timeout,

changes the Phase 10 startup global configuration hash.

The execution hash remains a separate value and is not mutated.

## Feature-flag gate

Actual production accounting wiring requires all four resolved flags:

- `AL_TRADING_REALISTIC_V2_ENABLED`
- `AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED`
- `AL_TRADING_FX_ENABLED`
- `AL_TRADING_PLN_ACCOUNTING_ENABLED`

If any flag is disabled, the runtime decision provider is not wrapped.

## Runtime construction

`wire_phase10_production_runtime()` constructs:

- `ParallelProductionFxResolver`,
- `BrokerExitFeeEstimator`,
- `Phase09RuntimeAccountingBridge`,
- `SnapshotCaptureDecisionProvider`,
- `Phase09AccountingRuntime`,
- `Phase10ProductionAccountingRuntime`,
- reproducibility/startup metadata.

The existing `RealisticPaperRuntime` and `PaperBroker` implementations are
not modified.

## Cash and persistence

A.4 does not invent a cash ledger.

`cash_pln_resolver` remains optional.

Accounting persistence is still not implemented.

The complete entry Execution remains in-memory only in the Phase 09
accounting wrapper.

No SQLite migration is started.

No existing `data/live_state` file is modified.

## Next step

A later Phase 10 step may connect this construction contract to a
controlled REALISTIC_V2 entrypoint and persist only startup metadata in a
new, explicitly scoped state location.

That step must keep `scripts/run_paper_live.py` untouched and must not
silently enable real-exchange orders.
