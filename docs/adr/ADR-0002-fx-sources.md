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
- Yahoo USDPLN=X
- Yahoo EURPLN=X
- maximum quality STALE_PRONE until a better source is validated

USDT/USD:
- use a real USDT/USD market leg
- Phase 07 empirically verified Coinbase Exchange USDT-USD

## Consequences

No single provider is falsely described as suitable for every FX role.

Phase 09 must preserve provider, timestamp, effective date and complete
conversion path.
