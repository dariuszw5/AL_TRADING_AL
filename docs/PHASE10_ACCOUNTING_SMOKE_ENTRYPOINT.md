# Phase 10 A.5 - Controlled Accounting Smoke Entrypoint

## Purpose

A.5 connects the Phase 10 production accounting construction contract to
a controlled REALISTIC_V2 PaperBroker entrypoint.

It is intentionally separate from:

- `scripts/run_realistic_paper.py`,
- `scripts/run_realistic_smoke_fill.py`,
- `scripts/run_paper_live.py`.

Those existing entrypoints are not modified by A.5.

## Default behavior

The new entrypoint defaults to construction verification only.

Without `--run-cycle` it:

- resolves all Phase 10 feature flags,
- validates an explicit accounting runtime policy,
- constructs the existing controlled REALISTIC_V2 smoke runtime,
- wraps it with the Phase 10 production accounting runtime,
- prints reproducibility/startup metadata,
- does not start the market-data/execution cycle,
- does not run production FX prefetch,
- does not submit a paper order,
- does not send a real exchange order.

## Stateful paper cycle

A stateful paper cycle requires both:

- `--run-cycle`
- `--confirm-paper-accounting-smoke`

The entrypoint remains BTCUSDT-only, matching the existing controlled
Phase 08 smoke boundary.

The underlying broker is still `PaperBroker`.

There is no path in this entrypoint that sends a real exchange order.

## Required feature flags

The command requires all four resolved flags:

- `AL_TRADING_REALISTIC_V2_ENABLED`
- `AL_TRADING_REALISTIC_V2_EXECUTION_ENABLED`
- `AL_TRADING_FX_ENABLED`
- `AL_TRADING_PLN_ACCOUNTING_ENABLED`

A disabled FX or PLN flag stops before runtime construction.

## Explicit policy arguments

The command requires explicit values for:

- realized market FX maximum age,
- realized daily-reference maximum age,
- FX prefetch timeout,
- FX prefetch worker limit,
- complete cycle timeout.

A policy that allocates more than 50 percent of the full cycle timeout
to FX prefetch is blocked by this controlled entrypoint.

## Known limitation retained

A.5 does not persist Phase 10 startup metadata yet.

It prints the Phase 10 global configuration hash and the complete
resolved policy, but reports:

`STARTUP METADATA PERSISTED: NO`

The system is therefore not ready to claim the MASTER_SPEC requirement
that startup configuration metadata is saved for every production start.

That persistence boundary is deferred to a later Phase 10 step.

## Restart-safe realized accounting

The existing Phase 09 limitation also remains:

the complete entry Execution is cached in memory only.

A close after process restart can still execute in PaperBroker, while
realized PLN accounting fails closed with `ENTRY_EXECUTION_REQUIRED`.

A.5 does not reconstruct entry evidence from `Position.entry_price`.

## Unchanged boundaries

A.5 does not modify:

- execution pricing/fill semantics,
- PaperBroker,
- RealisticPaperRuntime,
- execution journal semantics,
- state-store semantics,
- LEGACY_V1,
- frozen strategy parameters,
- existing assertions,
- existing live_state,
- SQLite,
- GOLD_FUT_CONT / WTI_FUT_CONT accounting activation.
