# ADR-0001 — Market calendars and timezone rules

Date: 2026-09-16
Status: Accepted for Phase 07

## Context

The project needs holidays, early closes, DST and non-equity weekly
sessions for crypto, FX, Nasdaq equities and futures proxies.

No market-calendar package is currently installed.

The initial Phase 07 research decision expected Python standard-library
`zoneinfo` to provide the required IANA time zones.

Runtime verification on the project's Windows/Python environment
showed that the local IANA timezone database is unavailable:

- `America/New_York` cannot be assumed available
- `America/Chicago` cannot be assumed available

Installing the external `tzdata` package would add a dependency and
therefore requires a MASTER_SPEC HARD STOP.

## Options considered

1. Add the `tzdata` dependency.
2. Add a third-party exchange-calendar package.
3. Hardcode fixed UTC offsets.
4. Use versioned repository market calendars plus deterministic US DST
   transition rules for the two currently required US time zones.

## Decision

Use option 4 in Phase 07.

MarketSessionService uses:
- timezone-aware UTC input
- versioned calendar data in the repository
- deterministic US DST rules for:
  - America/New_York
  - America/Chicago
- no new external dependency

The implemented US DST rules follow the post-2007 United States rule:
- DST starts on the second Sunday in March
- DST ends on the first Sunday in November

Conversion is performed from a UTC instant, avoiding ambiguous local
input timestamps.

Holiday and early-close dates remain versioned data and are not hidden
inside Python session logic.

## Consequences

Advantages:
- zero new dependency
- works on the current Windows Python environment
- deterministic offline tests
- DST transition tests are independent of host timezone data
- source versions remain visible in Git
- calendar expiry can fail closed

Costs:
- timezone law changes require a code/config review
- the deterministic converter is intentionally limited to currently
  required US zones
- this is not a general-purpose world timezone database

If a future phase adopts `tzdata`, `exchange_calendars`,
`pandas_market_calendars`, or another timezone/calendar dependency,
the normal HARD STOP is required first.
