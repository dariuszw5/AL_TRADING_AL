# ADR-0001 — Market calendars

Date: 2026-09-16
Status: Accepted for Phase 07

## Context

The project needs holidays, early closes, DST and non-equity weekly
sessions for crypto, FX, Nasdaq equities and futures proxies.

No market-calendar package is currently installed.

Adding a dependency requires HARD STOP approval.

## Options considered

1. Add a third-party exchange-calendar package.
2. Hardcode dates directly in Python.
3. Use standard-library `zoneinfo` plus versioned repository calendar
   data.

## Decision

Use option 3.

`MarketSessionService` will use:
- timezone-aware UTC input
- `zoneinfo`
- versioned calendar data in the repository

Holiday and early-close dates will not be hidden in Python logic.

## Consequences

Advantages:
- zero new dependency
- deterministic offline tests
- source versions visible in Git
- explicit expiry behaviour
- exceptional closures can be represented

Costs:
- calendar data requires maintenance
- new exchange rules require an explicit calendar update
- futures holiday hours remain UNKNOWN until product-level hours are
  recorded

If a future phase determines that a maintained external calendar
library is preferable, adding it requires the normal HARD STOP.
