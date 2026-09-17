# Phase 10 A.3 - Bounded Production FX Prefetch

## Purpose

Phase 10 A.2 introduced the production FX/accounting resolver layer.

Before that resolver is connected to a production construction path,
A.3 adds a bounded parallel prefetch implementation so FX collection
does not silently consume the complete REALISTIC_V2 cycle budget.

## Explicit scheduling contract

`ParallelProductionFxResolver` requires two explicit caller values:

- `prefetch_timeout_seconds`
- `max_workers`

There is deliberately no hidden production timeout or worker-count
default in this layer.

A later production-construction step must choose those values as part of
the reproducible startup policy.

## Parallel fetch

Independent FX provider calls are submitted concurrently.

For a BTCUSDT accounting cycle this can include:

- Yahoo USD/PLN for MTM,
- NBP USD/PLN for realized accounting evidence,
- Coinbase USDT/USD for both MTM and realized evidence.

Results are collected and written to the resolver state by the caller
thread, not by worker threads.

## Hard timeout behavior

The resolver returns after the explicit prefetch timeout even if a
provider worker is still running.

Timed-out legs are labelled:

`FX_PREFETCH_TIMEOUT`

A timed-out leg is not replaced with a fabricated quote.

Existing Phase 09 conversion/accounting logic therefore fails closed for
the missing leg.

## No overlapping FX fetch generations

Python cannot safely force-kill a running provider thread.

A.3 preserves that limitation explicitly.

If a timed-out worker is still alive when the next accounting cycle
starts, the resolver does not submit another FX fetch generation.

The next prefetch is blocked with:

`PREVIOUS_FX_PREFETCH_STILL_RUNNING`

Execution semantics remain outside this resolver. Accounting stays
fail-closed while the prior provider task is unresolved.

## Timing telemetry

The resolver exposes:

- `last_prefetch_duration_seconds`
- `last_prefetch_timed_out`
- `last_prefetch_blocked_by_previous`

Durations use a monotonic source.

A.3 does not yet claim a live-cycle performance result. The production
wiring must be measured later against the existing 20-second cycle
budget.

## Unchanged boundaries

A.3 does not modify:

- `PaperBroker`,
- `RealisticPaperRuntime`,
- execution pricing or fills,
- journal/state-store semantics,
- LEGACY_V1,
- frozen strategy parameters,
- existing assertions,
- `data/live_state`,
- SQLite,
- continuous-futures accounting activation.

GOLD_FUT_CONT and WTI_FUT_CONT remain fail-closed.
