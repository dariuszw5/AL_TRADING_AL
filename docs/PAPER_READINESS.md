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
