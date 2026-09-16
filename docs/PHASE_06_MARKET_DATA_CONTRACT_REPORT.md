# PHASE 06 — TIME, MARKET DATA CONTRACT AND DATA QUALITY

Date: 2026-09-16

Branch: `phase-06-market-data-contract`

Baseline:
- Phase 05 implementation commit: `37db8d8`
- Provider capability commit: `5018516`
- MASTER_SPEC commit: `98f6b7d`

## SUMMARY

Phase 06 established an explicit market-data contract and empirical
provider capability matrix without changing LEGACY_V1 trading
mathematics or implementing REALISTIC_V2 execution.

Implemented:
- empirical provider capability probe for all 9 assets
- Clock abstraction
- SystemClock using UTC-aware datetime
- deterministic FixedClock for tests
- monotonic duration measurement
- NormalizedCandle
- MarketSnapshot
- DataQuality
- ExecutionQuality
- ProviderStatus
- ProviderHealth
- candle validation
- duplicate/out-of-order protection
- stale-data classification
- provider request deadlines
- cycle timeout
- non-blocking cycle lock
- per-asset failure isolation
- cycle-duration measurement

No PaperBroker was implemented.
No new fill model was implemented.
No simulated or derived spread was introduced.

## BUGS / ISSUES VERIFIED

The required provider capability matrix did not exist at the beginning
of Phase 06.

Empirical probe result:

Binance for:
- BTCUSDT
- ETHUSDT
- SOLUSDT
- BNBUSDT
- XRPUSDT

confirmed:
- bid YES
- ask YES
- depth YES
- last YES
- volume YES
- feed probe REALTIME
- instrument metadata YES
- tick size YES
- quantity rules YES

Yahoo for:
- GOLD_FUT_CONT / GC=F
- WTI_FUT_CONT / CL=F
- EURUSD / EURUSD=X
- AAPL / AAPL

confirmed:
- bid NO
- ask NO
- depth NO
- last YES
- volume YES
- delay UNKNOWN
- metadata YES
- tick size from source NO
- quantity rules from source NO
- API UNOFFICIAL / DEGRADED_BY_DESIGN

During implementation the first targeted regression reproduced an
incomplete integration:
`DataProvider.__init__()` did not yet accept the injected Clock.

Failure:
- 2 failed
- 26 passed

The failure was corrected by integrating Clock and the snapshot
contract into DataProvider.

## BUGS FIXED

- DataProvider now supports injected Clock
- UTC-aware timestamps are used in the new market-data contract
- durations use monotonic time
- MarketSnapshot validates bid/ask/last and timestamp consistency
- REAL_BOOK requires real bid and ask
- unknown Yahoo delay is not falsely reported as realtime
- stale quotes are classified explicitly
- malformed/duplicate/out-of-order candles are rejected
- provider health records success/failure state and latency
- provider requests support a monotonic deadline
- a failing asset is isolated from remaining assets in a cycle
- cycle timeout prevents further asset work after the deadline
- overlapping market-data cycles are rejected by a non-blocking lock

## CLAIMS THAT DID NOT REPRODUCE

No Prompt 06 defect claim was bypassed or dismissed.

The expected Yahoo delay metadata was not available during the actual
probe for the four Yahoo-backed instruments, so the runtime correctly
keeps their delay classification UNKNOWN rather than inventing a
realtime/delayed value.

## CHANGED FILES

- `src/data/data_provider.py`
- `docs/PAPER_READINESS.md`
- `TODO_HARDENING.md`

## NEW FILES

Provider capability commit:
- `docs/PROVIDER_CAPABILITY.md`
- `scripts/probe_provider_capability.py`

Market-data implementation:
- `src/core/__init__.py`
- `src/core/clock.py`
- `src/data/market_data.py`
- `src/data/market_data_service.py`
- `tests/test_market_data_contract.py`
- `docs/PHASE_06_MARKET_DATA_CONTRACT_REPORT.md`

## TESTS ADDED

Market-data contract coverage includes:
- SystemClock is UTC-aware
- FixedClock deterministic advancement
- legacy candle normalization to UTC
- duplicate timestamp rejection
- unknown delay is not treated as realtime
- stale quote classification
- REAL_BOOK requires bid and ask
- Binance snapshot classifies REAL_BOOK
- Yahoo without bid/ask is not REAL_BOOK
- failure isolation per asset
- cycle-lock overlap protection
- cycle timeout behavior

## TEST RESULT

Initial targeted run:
- 26 passed
- 2 failed

Confirmed failure:
`DataProvider.__init__() got an unexpected keyword argument 'clock'`

After integration fix:
- 28 passed in 0.50s

Full offline regression:
- 365 passed in 119.14s
- exit code 0

Excluded network-dependent tests:
- tests/test_agent_data_flow.py
- tests/test_real_backtest.py
- tests/test_real_data_provider.py

Provider capability probe:
- 9 assets checked
- ERROR assets: NONE
- DEGRADED assets: NONE
- exit code 0

## LEGACY BTC REGRESSION RESULT

Execution profile:
LEGACY_V1

Dataset:
BTCUSDT 1m, frozen 5000 candles

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
- benchmark exit code: 0

The LEGACY_V1 BTC golden result is unchanged.

## REALISTIC RESULT

Not applicable.

Phase 06 does not implement REALISTIC_V2 or a PaperBroker.

ExecutionQuality is classification metadata only.

## PAPER_READINESS CHANGES

No asset is promoted to paper-ready status.

Crypto:
- DATA_QUALITY evidence: REALTIME_BOOK
- EXECUTION_QUALITY: REAL_BOOK
- FX_QUALITY: UNAVAILABLE/not yet implemented
- SESSION_QUALITY: UNKNOWN
- PAPER_READINESS: NOT_READY

Yahoo-backed instruments:
- last-price data available
- delay classification UNKNOWN
- no bid/ask
- no depth
- EXECUTION_QUALITY: UNTRADEABLE
- FX/session work incomplete
- PAPER_READINESS: NOT_READY

GOLD_FUT_CONT and WTI_FUT_CONT remain explicit continuous-futures
proxies and remain EXPERIMENTAL.

## SPEC ASSUMPTIONS THAT WERE FALSE

No MASTER_SPEC amendment was required.

One empirical uncertainty was resolved conservatively:
Yahoo `exchangeDataDelayedBy` was not available in the observed
responses for the four Yahoo-backed assets.

The specification required this field to be checked, not assumed, so
MASTER_SPEC remains correct.

## ZAŁOŻENIA SPECYFIKACJI, KTÓRE OKAZAŁY SIĘ NIEPRAWDZIWE

None requiring a MASTER_SPEC update.

Yahoo delay metadata could not be relied upon in the observed probe,
therefore no realtime claim is made for those assets.

## CLAIMS / ZARZUTY Z PROMPTU, KTÓRE NIE POTWIERDZIŁY SIĘ TESTEM

None.

The missing Clock integration did reproduce as a targeted test failure
and was fixed before the full regression.

## NEW TECHNICAL DEBT

- Yahoo v8 chart remains an unofficial dependency
- reliable Yahoo-backed delay classification is unresolved
- streaming capability was intentionally not probed
- non-Binance tick/quantity rules remain unavailable
- MarketDataService currently processes assets sequentially
- no DERIVED_SPREAD model exists yet
- no SIMULATED_SPREAD model exists yet
- no final PaperBroker exists yet
- FX conversion to PLN is not implemented in this phase
- session/calendar quality is not established in this phase

## DŁUG TECHNICZNY DODANY ŚWIADOMIE W TEJ FAZIE

The sequential cycle implementation is intentionally simple and
deterministic. It may later require concurrency if measured provider
latency makes the 9-asset cycle exceed its time budget.

Yahoo remains isolated behind provider-facing code so it can be
replaced later without changing trading core.

## CYCLE DURATION IMPACT

Cycle duration is now measured using monotonic time and returned in
MarketDataCycleResult.

A hard cycle timeout and provider-request deadline are implemented.

No production network latency benchmark for the complete 9-asset cycle
was performed in this phase.

Potential cost:
- Binance MarketSnapshot currently requires two HTTP reads per asset
  (bookTicker + ticker/24hr)
- Yahoo MarketSnapshot requires one chart request per asset
- assets are processed sequentially

This is explicit technical debt and must be measured before production
paper execution.

## WPŁYW NA CZAS TRWANIA CYKLU

Runtime now exposes deterministic cycle duration and a hard deadline.

The exact 9-market production cycle latency remains unmeasured.

No claim is made that the current sequential implementation always
fits inside a 1-minute candle interval.

## ZMIANY W PAPER_READINESS PER ASSET

BTCUSDT:
- market data improved to empirically confirmed real book
- overall NOT_READY pending FX/session/later execution work

ETHUSDT:
- real book confirmed
- overall NOT_READY

SOLUSDT:
- real book confirmed
- overall NOT_READY

BNBUSDT:
- real book confirmed
- overall NOT_READY

XRPUSDT:
- real book confirmed
- overall NOT_READY

GOLD_FUT_CONT:
- last available
- no real book
- delay unknown
- continuous-futures proxy
- overall NOT_READY

WTI_FUT_CONT:
- last available
- no real book
- delay unknown
- continuous-futures proxy
- overall NOT_READY

EURUSD:
- last available
- no real book
- delay unknown
- overall NOT_READY

AAPL:
- last available
- no real book
- delay unknown
- overall NOT_READY

## ROLLBACK PLAN

Revert the Phase 06 implementation commit.

The empirical provider capability commit may remain because it is
observational documentation and a diagnostic script rather than a
change to trading semantics.

No database migration exists.
No live-state migration exists.
No frozen strategy parameter changed.

## HARD STOP REQUIRED BEFORE NEXT PHASE

No new HARD STOP is required merely to start the next read-only
research/design phase.

Any future action that changes execution semantics, introduces a new
dependency, modifies existing assertions, changes PLN accounting,
migrates JSON to SQLite, overwrites live state or changes frozen BTC
parameters still requires explicit HARD STOP approval.

## CZY WYMAGANY JEST HARD STOP PRZED NASTĘPNĄ FAZĄ

Not for read-only research/configuration work.

A HARD STOP remains mandatory before any later implementation that
changes execution semantics.
