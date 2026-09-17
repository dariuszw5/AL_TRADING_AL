# ADR-0002 — FX sources

Date: 2026-09-16
Status: Accepted for research policy

## Context

PLN reporting requires USD/PLN, EUR/PLN and a defensible path for
USDT-denominated assets.

NBP is authoritative as a Polish reference source but is not an
intraday live market feed.

Yahoo provides reachable FX last prices but the current endpoint is
unofficial and the Phase 07 probe did not expose reliable delay
metadata.

## Decision

Separate reference accounting from MTM.

Reference accounting:
- NBP Table A
- quality DAILY_REFERENCE

MTM research candidates:
- Yahoo PLN=X (canonical project symbol for USD/PLN)
- Yahoo EURPLN=X
- maximum quality STALE_PRONE until a better source is validated

USDT/USD:
- use a real USDT/USD market leg
- Phase 07 empirically verified Coinbase Exchange USDT-USD

## Consequences

No single provider is falsely described as suitable for every FX role.

Phase 09 must preserve provider, timestamp, effective date and complete
conversion path.

## Phase 09 A.12 symbol reconciliation

A read-only probe on 2026-09-17 returned the same USD/PLN market value
for both Yahoo `PLN=X` and `USDPLN=X`.

The implemented provider already uses `PLN=X`.

Decision:

- project canonical USD/PLN Yahoo symbol: `PLN=X`,
- `USDPLN=X` is not used as the canonical runtime identifier,
- historical Phase 07 evidence that referenced `USDPLN=X` remains
  historical evidence and is not rewritten,
- Yahoo remains `UNOFFICIAL / DEGRADED_BY_DESIGN` with quality ceiling
  `STALE_PRONE`; successful HTTP responses do not upgrade it to LIVE.
