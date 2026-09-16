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
