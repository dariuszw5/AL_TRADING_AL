# PAPER READINESS

This document tracks readiness conservatively per asset.

A phase may update only the dimensions it actually verifies.
Unknown or unresolved dimensions must not be silently promoted.

## Phase 05 — Asset Registry / Config

| Asset | Validation status | Instrument clarity | Phase 05 readiness change |
|---|---|---|---|
| BTCUSDT | FROZEN | CONFIRMED | No promotion |
| ETHUSDT | EXPERIMENTAL | CONFIRMED | No promotion |
| SOLUSDT | EXPERIMENTAL | CONFIRMED | No promotion |
| BNBUSDT | EXPERIMENTAL | CONFIRMED | No promotion |
| XRPUSDT | EXPERIMENTAL | CONFIRMED | No promotion |
| GOLD_FUT_CONT | EXPERIMENTAL | PROXY | No promotion |
| WTI_FUT_CONT | EXPERIMENTAL | PROXY | No promotion |
| EURUSD | EXPERIMENTAL | CONFIRMED | No promotion |
| AAPL | EXPERIMENTAL | CONFIRMED | No promotion |

Phase 05 does not establish or promote:
- DATA_QUALITY
- EXECUTION_QUALITY
- FX_QUALITY
- SESSION_QUALITY
- REALISTIC_V2 PAPER_READINESS

Those dimensions remain governed by their dedicated phases and
provider evidence.

GOLD_FUT_CONT and WTI_FUT_CONT remain continuous-futures proxies and
cannot exceed EXPERIMENTAL until rollover/tradability limitations are
resolved.

## Phase 06 — Market Data Contract

Provider capabilities were measured empirically on 2026-09-16.

No asset is promoted to FULL/LIMITED paper readiness by this phase
alone. Phase 06 establishes market-data and execution-quality
classification only.

| Asset | DATA_QUALITY | EXECUTION_QUALITY | FX_QUALITY | SESSION_QUALITY | INSTRUMENT_CLARITY | PAPER_READINESS |
|---|---|---|---|---|---|---|
| BTCUSDT | REALTIME_BOOK | REAL_BOOK | UNAVAILABLE | UNKNOWN | CONFIRMED | NOT_READY |
| ETHUSDT | REALTIME_BOOK | REAL_BOOK | UNAVAILABLE | UNKNOWN | CONFIRMED | NOT_READY |
| SOLUSDT | REALTIME_BOOK | REAL_BOOK | UNAVAILABLE | UNKNOWN | CONFIRMED | NOT_READY |
| BNBUSDT | REALTIME_BOOK | REAL_BOOK | UNAVAILABLE | UNKNOWN | CONFIRMED | NOT_READY |
| XRPUSDT | REALTIME_BOOK | REAL_BOOK | UNAVAILABLE | UNKNOWN | CONFIRMED | NOT_READY |
| GOLD_FUT_CONT | REALTIME_LAST* | UNTRADEABLE | UNAVAILABLE | UNKNOWN | PROXY | NOT_READY |
| WTI_FUT_CONT | REALTIME_LAST* | UNTRADEABLE | UNAVAILABLE | UNKNOWN | PROXY | NOT_READY |
| EURUSD | REALTIME_LAST* | UNTRADEABLE | UNAVAILABLE | UNKNOWN | CONFIRMED | NOT_READY |
| AAPL | REALTIME_LAST* | UNTRADEABLE | UNAVAILABLE | UNKNOWN | CONFIRMED | NOT_READY |

`*` Yahoo returned current last/volume data during the empirical probe,
but did not expose a reliable delay classification. Runtime
`MarketSnapshot.data_quality` therefore remains `UNKNOWN` when the
provider does not supply a delay hint. `REALTIME_LAST*` in this table
means only that last-price data was reachable during the probe; it must
not be interpreted as a guarantee of realtime delivery.

Binance observations:
- real bid: available
- real ask: available
- depth: available
- last: available
- instrument metadata: available
- tick size: available
- quantity rules: available
- measured feed classification during probe: REALTIME
- execution classification: REAL_BOOK

Yahoo observations for GOLD_FUT_CONT, WTI_FUT_CONT, EURUSD and AAPL:
- bid: unavailable
- ask: unavailable
- depth: unavailable
- last: available
- delay classification: UNKNOWN
- tick size from current source: unavailable
- quantity rules from current source: unavailable
- API classification: UNOFFICIAL / DEGRADED_BY_DESIGN
- execution classification in Phase 06: UNTRADEABLE

No DERIVED_SPREAD or SIMULATED_SPREAD model is introduced in Phase 06.
No REALISTIC_V2 fill model is introduced.

Overall PAPER_READINESS remains NOT_READY because later phases still
need to establish FX policy/conversion, market-session quality and
realistic execution rules.

## Phase 07 — Market Sessions and FX Research

This section is the current readiness state after Phase 07 and
supersedes older per-asset readiness rows for current-state reporting.

Phase 07 adds a deterministic MarketSessionService and completes FX
source/policy research.

It does NOT:
- wire session status into execution
- implement CurrencyConverter
- book PLN values into the portfolio
- implement REALISTIC_V2

Therefore FX_QUALITY remains UNAVAILABLE at runtime for all assets even
though reference and candidate FX sources have now been researched.

| Asset | DATA_QUALITY | EXECUTION_QUALITY | FX_QUALITY | SESSION_QUALITY | INSTRUMENT_CLARITY | PAPER_READINESS |
|---|---|---|---|---|---|---|
| BTCUSDT | REALTIME_BOOK | REAL_BOOK | UNAVAILABLE | EXCHANGE_CALENDAR | CONFIRMED | NOT_READY |
| ETHUSDT | REALTIME_BOOK | REAL_BOOK | UNAVAILABLE | EXCHANGE_CALENDAR | CONFIRMED | NOT_READY |
| SOLUSDT | REALTIME_BOOK | REAL_BOOK | UNAVAILABLE | EXCHANGE_CALENDAR | CONFIRMED | NOT_READY |
| BNBUSDT | REALTIME_BOOK | REAL_BOOK | UNAVAILABLE | EXCHANGE_CALENDAR | CONFIRMED | NOT_READY |
| XRPUSDT | REALTIME_BOOK | REAL_BOOK | UNAVAILABLE | EXCHANGE_CALENDAR | CONFIRMED | NOT_READY |
| GOLD_FUT_CONT | UNRELIABLE | UNTRADEABLE | UNAVAILABLE | APPROXIMATED | PROXY | NOT_READY |
| WTI_FUT_CONT | UNRELIABLE | UNTRADEABLE | UNAVAILABLE | APPROXIMATED | PROXY | NOT_READY |
| EURUSD | UNRELIABLE | UNTRADEABLE | UNAVAILABLE | APPROXIMATED | CONFIRMED | NOT_READY |
| AAPL | UNRELIABLE | UNTRADEABLE | UNAVAILABLE | EXCHANGE_CALENDAR | CONFIRMED | NOT_READY |

### Session evidence

Crypto:
- explicit 24/7 scheduled-session model
- provider outage remains a separate provider-health condition

AAPL:
- versioned Nasdaq calendar
- pre-market
- regular session
- after-hours
- weekends
- full holidays
- early closes
- exceptional closure support
- US DST transitions
- outside verified calendar coverage -> UNKNOWN

EURUSD:
- Sunday-Friday FX reference week
- weekend boundaries
- US DST-aware transitions
- SESSION_QUALITY remains APPROXIMATED

GOLD_FUT_CONT / WTI_FUT_CONT:
- CME/COMEX/NYMEX reference characteristics
- explicit daily maintenance window
- continuous-futures proxy identity retained
- special holiday schedules fail closed to UNKNOWN until exact
  product-level hours are verified
- SESSION_QUALITY remains APPROXIMATED

### FX research state

Empirically verified on 2026-09-16:

NBP:
- USD/PLN reference available
- EUR/PLN reference available
- role: future DAILY_REFERENCE accounting source

Yahoo:
- USDPLN=X reachable
- EURPLN=X reachable
- delay metadata not reliably available
- remains UNOFFICIAL / DEGRADED_BY_DESIGN

Coinbase Exchange:
- USDT-USD bid/ask/last empirically reachable
- confirms that unconditional 1 USDT = 1 USD must not be used

Planned canonical crypto conversion path:

USDT -> USD -> PLN

No runtime FX conversion is enabled by Phase 07.
