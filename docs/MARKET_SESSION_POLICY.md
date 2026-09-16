# MARKET SESSION POLICY

Status: Phase 07 research/design
Date reviewed: 2026-09-16

## Principle

`MarketSessionService` will be the single runtime source of truth for
market-session state.

It will use:
- versioned calendar data stored in the repository
- deterministic US DST transition rules for `America/New_York` and `America/Chicago`
- no new third-party dependency in Phase 07

No execution rule is changed by introducing the service.

## BTCUSDT / ETHUSDT / SOLUSDT / BNBUSDT / XRPUSDT

Session identity:
CRYPTO_24_7

Policy:
OPEN continuously except an actual provider/venue outage.

A provider outage is a data/provider-health condition, not a scheduled
market close.

## AAPL

Reference venue:
Nasdaq.

Timezone:
America/New_York

Current day-session structure:
- PRE_MARKET: 04:00-09:30 ET
- REGULAR: 09:30-16:00 ET
- AFTER_HOURS: 16:00-20:00 ET
- CLOSED otherwise

On an official Nasdaq early-close day:
- pre-market remains separate
- REGULAR ends at the published early-close time
- extended-hours handling follows the versioned calendar/source
- the service must not infer a normal 16:00 close

Holidays and special closures must come from versioned repository
calendar data.

The calendar must support exceptional closures, not only recurring
holiday formulas.

Example:
the special Nasdaq closure on 2025-01-09 must be representable.

If a requested date is outside verified calendar coverage:
SESSION_QUALITY = UNKNOWN
and market status must not be guessed.

DST:
handled by deterministic US transition rules evaluated from UTC. The current Windows Python environment does not provide the IANA timezone database required by `zoneinfo`. Fixed year-round UTC offsets are not used.

## EURUSD

Asset identity:
FX_REFERENCE

The current Yahoo feed is not an exchange calendar.

For research/session reference the project uses the documented
institutional FX weekly convention:

- opens Sunday 17:00 America/New_York
- closes Friday 17:00 America/New_York

Reference full-day exceptions include:
- New Year's Day
- Christmas Day

This is a reference session model, not proof that Yahoo itself
publishes every minute throughout the entire interval.

SESSION_QUALITY:
APPROXIMATED until the feed/session relationship is validated.

## GOLD_FUT_CONT

Provider symbol:
GC=F

Instrument:
continuous_future_proxy

Do not call this XAUUSD or spot gold.

Reference market characteristics:
COMEX/CME Gold futures.

Regular reference schedule:
- Sunday-Friday
- 17:00-16:00 America/Chicago
- scheduled maintenance 16:00-17:00

Holiday hours are product/date-specific.

If exact holiday hours are not present in the versioned source:
status = UNKNOWN for the affected holiday window.

SESSION_QUALITY:
APPROXIMATED for the Yahoo continuous-futures proxy.

## WTI_FUT_CONT

Provider symbol:
CL=F

Instrument:
continuous_future_proxy

Do not call this WTI spot.

Reference market characteristics:
NYMEX/CME WTI futures.

Regular reference schedule:
- Sunday-Friday
- 17:00-16:00 America/Chicago
- scheduled maintenance 16:00-17:00

Holiday hours are product/date-specific.

If exact holiday hours are not available:
status = UNKNOWN rather than assuming normal trading.

SESSION_QUALITY:
APPROXIMATED for the Yahoo continuous-futures proxy.

## Calendar expiry

Versioned calendars carry explicit coverage.

Outside verified coverage:
- do not extrapolate an exchange holiday calendar
- return UNKNOWN
- emit enough metadata to identify the missing calendar version

## Source hierarchy

AAPL:
Nasdaq official trading rules and trading calendar.

EURUSD reference:
Cboe FX published hours/holidays used only as a reference convention.

GOLD_FUT_CONT / WTI_FUT_CONT:
CME published product/trading-hours and holiday materials.

Crypto:
venue schedule identity is continuous 24/7; provider health remains a
separate concern.

## Future Nasdaq extended/night sessions

Future announced or proposed sessions must not become active merely
because documentation describes them.

A new effective session schedule requires:
- confirmed effective date
- versioned calendar/rules update
- regression tests

No future Nasdaq night session is enabled by Phase 07.
