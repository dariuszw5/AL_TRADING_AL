# Phase 09 A.12 FX probe acceptance

Date: 2026-09-17

Probe type: read-only public market-data GET requests.

No orders were placed.

## Yahoo PLN FX observations

`PLN=X`:
- observed price: 3.7973
- provider timestamp age at probe: about 1.7 seconds
- `exchangeDataDelayedBy`: unavailable/None

`USDPLN=X`:
- observed price: 3.7973
- provider timestamp age at probe: about 0.7 seconds
- `exchangeDataDelayedBy`: unavailable/None

`EURPLN=X`:
- observed price: 4.3576
- provider timestamp age at probe: about 1.7 seconds
- `exchangeDataDelayedBy`: unavailable/None

For all three Yahoo series:
- requested chart window: 7 days / 1 hour,
- observed points: 163,
- median gap: 1 hour,
- maximum observed gap: 49 hours,
- maximum gap crossed the weekend.

Yahoo remains `UNOFFICIAL / DEGRADED_BY_DESIGN` with quality ceiling
`STALE_PRONE`.

## Coinbase USDT-USD

Observed:
- bid: 0.99912
- ask: 0.99913
- public provider time available.

The probe printed provider clock age around `-1.4s`, but the probe
captured its fixed `NOW` before subsequent network calls. This is not
accepted as evidence of provider future-clock drift.

## NBP Table A

Observed:
- USD/PLN: 3.803
- EUR/PLN: 4.3632
- table: 181/A/NBP/2026
- effective date: 2026-09-17

NBP remains `DAILY_REFERENCE`, not intraday LIVE FX.

## Accepted A.12 decisions

Canonical Yahoo USD/PLN symbol:

`PLN=X`

Production freshness defaults:
- weekday: 7200 seconds,
- weekend: 7200 seconds,
- `FX_STALE` begins at age >= 7200 seconds,
- exactly 96 hours remains `FX_STALE`,
- age > 96 hours becomes `FX_UNAVAILABLE`.

Future provider timestamps remain fail-closed:

`FUTURE_FX_TIMESTAMP`

No timestamp is artificially refreshed.
