# PHASE 07 — MARKET SESSIONS, INSTRUMENT RULES AND FX POLICY RESEARCH

Date: 2026-09-16

Branch:
`phase-07-market-sessions-fx-research`

## SUMMARY

Phase 07 established:
- FX source research and policy
- session-source policy
- architecture decision records
- a deterministic MarketSessionService
- versioned repository calendar data
- offline tests for session transitions, holidays, early closes and DST

Phase 07 did not change execution semantics.

MarketSessionService is intentionally not connected to:
- AgentEngine
- TradingEngine
- BacktestEngine
- paper execution

No CurrencyConverter was implemented.

No PLN accounting was implemented.

No REALISTIC_V2 execution was implemented.

## RESEARCH VERIFIED

Empirical Phase 07 source probe completed successfully.

NBP:
- USD reference rate available
- EUR reference rate available
- effective date 2026-09-16
- USD/PLN mid observed: 3.7639
- EUR/PLN mid observed: 4.3435

Yahoo:
- USDPLN=X reachable
- EURPLN=X reachable
- EURUSD=X reachable
- AAPL reachable
- GC=F reachable
- CL=F reachable

Observed Yahoo `exchangeDataDelayedBy`:
- unavailable / None for all tested symbols

Coinbase Exchange:
- USDT-USD reachable
- observed price: 0.99933
- observed bid: 0.99932
- observed ask: 0.99933

This empirically confirms that the project must not use an
unconditional 1 USDT = 1 USD conversion.

Research evidence:
`docs/evidence/PHASE07_SESSION_FX_PROBE_2026-09-16.json`

## FX POLICY

Reference accounting candidate:
- NBP Table A
- quality role: DAILY_REFERENCE

MTM candidates:
- Yahoo USDPLN=X
- Yahoo EURPLN=X
- source remains UNOFFICIAL / DEGRADED_BY_DESIGN
- no LIVE quality claim is made

Canonical crypto conversion path:

`USDT -> USD -> PLN`

USDT/USD:
- real market-data leg
- Coinbase Exchange empirically verified in Phase 07

Weekend policy:
- preserve last real FX timestamp
- never refresh timestamp artificially
- FX_FRESH inside configured freshness threshold
- FX_STALE beyond freshness threshold but <= 96h
- FX_UNAVAILABLE beyond 96h or with missing conversion path

No numerical max_fx_age was frozen in Phase 07.

KNOWN_LIMITATION:
`FX_CONVERSION_COST_NOT_MODELLED`

## MARKET SESSION SERVICE

Implemented:
`src/market/market_session.py`

Supported identities:
- CRYPTO_24_7
- NASDAQ_REGULAR_REFERENCE
- FX_24_5_REFERENCE
- CME_GLOBEX_REFERENCE

Session states:
- OPEN
- PRE_MARKET
- REGULAR
- AFTER_HOURS
- MAINTENANCE
- CLOSED
- UNKNOWN

Session quality:
- EXCHANGE_CALENDAR
- APPROXIMATED
- UNKNOWN

## VERSIONED MARKET CALENDAR

Implemented:
`config/market_calendars/market_calendars_v1.json`

Nasdaq coverage:
- 2023-01-01 through 2026-12-31

Includes:
- full closures
- early closes
- exceptional 2025-01-09 closure

A request outside verified Nasdaq calendar coverage fails closed:

`state = UNKNOWN`

CME proxy calendar coverage:
- 2026 only

Dates with potentially special CME holiday hours fail closed:

`state = UNKNOWN`

until exact product-level hours are verified.

The implementation does not pretend that Yahoo GC=F or CL=F is the
same thing as directly trading a CME futures contract.

## VERIFIED / FIXED

Verified:
- crypto 24/7 session status
- AAPL pre-market
- AAPL regular market
- AAPL after-hours
- AAPL weekend close
- Nasdaq holidays
- Nasdaq exceptional closure
- Nasdaq early close
- calendar expiry -> UNKNOWN
- FX Sunday weekly open
- FX Friday weekly close
- March DST transition
- November DST transition
- CME proxy normal session
- CME daily maintenance
- CME Sunday reopen
- CME special-schedule dates -> UNKNOWN
- CME calendar expiry -> UNKNOWN
- UTC normalization

Reproduced and fixed:
- Windows/Python environment does not provide the required local IANA
  timezone database for ZoneInfo("America/Chicago")
- equivalent limitation was confirmed for required IANA-zone
  availability assumptions

Initial session run:
- 24 failed
- 15 passed
- principal reproduced failure:
  `ZoneInfoNotFoundError: No time zone found with key America/Chicago`

Resolution:
- no external tzdata dependency was added
- deterministic post-2007 US DST rules were introduced for:
  - America/New_York
  - America/Chicago
- UTC instants remain canonical inputs
- direct DST-boundary tests were added

Final targeted result:
- 42 passed in 0.19s

## ZARZUTY / ISSUES NOT REPRODUCED

None were silently dismissed.

The session implementation exposed a real environment limitation and
that limitation was reproduced before the fix.

## TEST RESULTS

Phase 07 targeted:
- 42 passed in 0.19s

Full deterministic offline regression:
- 395 passed in 64.44s
- exit code 0

Excluded network-dependent tests:
- tests/test_agent_data_flow.py
- tests/test_real_backtest.py
- tests/test_real_data_provider.py

Execution wiring audit:
- MarketSessionService references in agent/trading/backtest core: NONE

Dependency audit:
- no dependency file changed
- no new package installed by Phase 07

## BTC LEGACY_V1 REGRESSION

Dataset:
BTCUSDT 1m frozen 5000 candles

Result:
- Initial balance: 1000.0
- Final balance: 1014.8392976799995
- Trades: 13
- Wins: 7
- Losses: 6
- Win rate: 53.84615384615385%
- Total profit: 14.839297679999504
- Max drawdown: 18.485012400000187
- Profit factor: 1.692128777090018
- Average win: 5.182768514285695
- Average loss: 3.573346986666712
- Largest win: 13.000798400000047
- Largest loss: 9.580003080000042
- Expectancy: 1.1414844369230388

BTC LEGACY_V1 golden is unchanged.

## REALISTIC RESULT

Not applicable.

REALISTIC_V2 has not been implemented in Phase 07.

## FILES

Research/policy commit:
- docs/FX_POLICY.md
- docs/MARKET_SESSION_POLICY.md
- docs/adr/ADR-0001-market-calendars.md
- docs/adr/ADR-0002-fx-sources.md
- docs/adr/ADR-0003-fx-weekend-policy.md
- docs/adr/ADR-0004-usdt-conversion-path.md
- docs/evidence/PHASE07_SESSION_FX_PROBE_2026-09-16.json
- scripts/probe_phase07_sessions_fx.py

Session implementation:
- config/market_calendars/market_calendars_v1.json
- src/market/__init__.py
- src/market/market_session.py
- tests/test_market_sessions.py

Closeout:
- docs/PAPER_READINESS.md
- docs/PHASE_07_MARKET_SESSIONS_FX_REPORT.md

## PAPER_READINESS CHANGES

SESSION_QUALITY improved:

BTCUSDT:
- EXCHANGE_CALENDAR

ETHUSDT:
- EXCHANGE_CALENDAR

SOLUSDT:
- EXCHANGE_CALENDAR

BNBUSDT:
- EXCHANGE_CALENDAR

XRPUSDT:
- EXCHANGE_CALENDAR

AAPL:
- EXCHANGE_CALENDAR within verified calendar coverage
- UNKNOWN outside coverage or intentionally unverified exceptional
  windows

EURUSD:
- APPROXIMATED

GOLD_FUT_CONT:
- APPROXIMATED
- may become UNKNOWN on unverified special-schedule dates

WTI_FUT_CONT:
- APPROXIMATED
- may become UNKNOWN on unverified special-schedule dates

FX_QUALITY remains UNAVAILABLE at runtime for every asset because
Phase 07 performed policy/research only and did not implement
CurrencyConverter.

Overall PAPER_READINESS therefore remains NOT_READY.

Yahoo-backed DATA_QUALITY is recorded as UNRELIABLE because the current
source does not provide reliable delay metadata.

## ZAŁOŻENIA SPECYFIKACJI, KTÓRE OKAZAŁY SIĘ NIEPRAWDZIWE

No MASTER_SPEC requirement was shown to be false.

An implementation assumption made during Phase 07 was false:

Assumption:
the Windows Python standard library would have the local IANA database
needed by `zoneinfo`.

Reality:
the required zone keys were unavailable in the project environment.

MASTER_SPEC was not changed because it requires correct UTC/DST
handling, but does not mandate ZoneInfo or an external tzdata package.

The implementation was changed instead.

## ZARZUTY Z PROMPTU, KTÓRE NIE POTWIERDZIŁY SIĘ TESTEM

None.

## DŁUG TECHNICZNY DODANY ŚWIADOMIE W TEJ FAZIE

1. The custom deterministic timezone conversion covers only the two US
   zones currently required by the project:
   - America/New_York
   - America/Chicago

2. It follows the post-2007 US DST rules and is intentionally not a
   general world timezone database.

3. Nasdaq calendar data currently ends at 2026-12-31.

4. CME proxy calendar currently covers 2026 only.

5. Exact product-level CME holiday hours are not yet encoded; affected
   dates fail closed to UNKNOWN.

6. EURUSD weekly-session rules remain APPROXIMATED relative to the
   current Yahoo data source.

7. CurrencyConverter is not implemented.

8. PLN accounting is not implemented.

9. Yahoo FX source remains unofficial and stale-prone by design.

## WPŁYW NA CZAS TRWANIA CYKLU

Current impact on the production/paper execution cycle:
NONE.

MarketSessionService is not wired into execution.

The service performs:
- in-memory datetime arithmetic
- dictionary/set lookups
- no provider request
- no network request per session lookup

If integrated in a later phase, cycle-duration impact must be measured
again as part of that phase.

## ROLLBACK PLAN

Revert the Phase 07 session implementation commit.

The earlier Phase 07 research/policy commit may remain because it
contains empirical evidence and architectural documentation.

No database migration exists.
No live-state migration exists.
No frozen BTC parameter changed.
No execution profile changed.

## CZY WYMAGANY JEST HARD STOP PRZED NASTĘPNĄ FAZĄ

A HARD STOP is not required to begin read-only design/research for the
next phase.

A HARD STOP IS required before implementing any next-phase change that:
- changes execution semantics
- implements REALISTIC_V2 fills
- changes PLN accounting
- adds a dependency
- changes existing assertions
- performs SQLite migration
- modifies frozen BTC strategy parameters
- overwrites live-state/data semantics

In particular, design work for REALISTIC_V2 may begin without approval,
but implementation of new execution semantics requires explicit HARD
STOP approval.
