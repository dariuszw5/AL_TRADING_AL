# ADR-0003 — FX weekend policy

Date: 2026-09-16
Status: Accepted for design

## Context

Crypto trades on weekends while ordinary fiat FX sources may stop
updating.

Rejecting PLN reporting immediately on Friday would make weekend crypto
monitoring unnecessarily unusable.

Pretending the Friday rate is fresh is also incorrect.

## Decision

Keep the last valid FX observation with its original timestamp.

Classification:
- within configured freshness limit: FX_FRESH
- older than freshness limit but <= 96h: FX_STALE
- older than 96h or missing: FX_UNAVAILABLE

FX_STALE output must show:
- stale label
- quote age
- source timestamp

Business-day and weekend freshness thresholds are separately
configurable.

Phase 07 does not freeze the numeric threshold.

## Consequences

Weekend crypto can still show indicative PLN MTM without disguising an
old FX rate as live.

No accounting value may silently refresh its timestamp.

## Phase 09 A.12 accepted numeric defaults

The 2026-09-17 empirical Yahoo PLN FX probe measured:

- median chart cadence: 1 hour,
- observed weekend gap: 49 hours.

Accepted production defaults:

- business-day freshness threshold: 2 hours,
- weekend freshness threshold: 2 hours,
- hard unavailable boundary: age > 96 hours.

The two freshness thresholds remain separately configurable.

Equal defaults are intentional. Weekend usability is provided by the
explicit `FX_STALE` state, not by pretending a Friday quote is fresh
for tens of hours.

At exactly 96 hours the quote remains `FX_STALE`.
Only age strictly greater than 96 hours is `FX_UNAVAILABLE`.
