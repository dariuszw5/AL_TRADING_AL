# PHASE 08 — REALISTIC_V2 EXECUTION REPORT

Date: 2026-09-16

Branch: `phase-08-realistic-v2-execution-design`

## SUMMARY

Phase 08 introduced REALISTIC_V2 as an isolated paper-execution profile while preserving LEGACY_V1 historical behavior.

The phase implemented:

- isolated REALISTIC_V2 execution kernel,
- realistic bid/ask execution semantics,
- adverse deterministic slippage,
- explicit execution-quality gating,
- short-support gating,
- deterministic idempotent client order IDs,
- feature flags with fail-closed defaults,
- a signal-only adapter that does not call legacy execution,
- a separate REALISTIC_V2 runtime,
- live-data preflight,
- bounded parallel market-data fetch,
- atomic REALISTIC_V2 active-position persistence,
- write-ahead execution journal,
- restart idempotency,
- state/journal reconciliation,
- controlled technical BTCUSDT paper smoke,
- deterministic REALISTIC_V2 execution benchmark.

The main `scripts/run_realistic_paper.py --execute` path remains deliberately blocked.

No real exchange order was submitted.

## VERIFIED

Verified during Phase 08:

- LEGACY_V1 remains operational and unchanged in behavior.
- BTC frozen benchmark remains bit-for-bit numerically consistent with the Phase 04 golden values used by the regression gate.
- REALISTIC_V2 entry BUY executes from ask plus adverse slippage.
- REALISTIC_V2 long exit SELL executes from bid minus adverse slippage.
- fee is included in execution records.
- config hash includes paper mode.
- REALISTIC_V2 feature flag defaults OFF.
- execution feature flag defaults OFF.
- stale data is rejected.
- delayed data is rejected in `realistic_paper`.
- delayed data may be labelled in `research_paper`.
- UNTRADEABLE is rejected.
- unknown/unverified session state is rejected.
- synthetic short is not silently represented as a real short.
- invalid position/asset/side/quantity combinations are rejected.
- idempotent replay returns the previous execution.
- conflicting client-order reuse is rejected.
- unresolved WAL is fail-closed.
- active positions survive restart.
- state and execution journal are reconciled after restart.
- the nine-asset live data cycle does not overlap itself.
- bounded parallel market fetch reduced measured cycle duration materially.
- controlled BTCUSDT paper smoke completed OPEN -> restart -> CLOSE -> restart.
- final smoke state contains zero open positions and zero unresolved WAL records.

## FIXED

Confirmed problems fixed in this phase:

1. REALISTIC_V2 did not previously exist as an isolated execution path.
2. Execution previously had no explicit realistic bid/ask semantics.
3. REALISTIC_V2 lacked explicit execution-quality gating.
4. REALISTIC_V2 lacked fail-closed feature gating.
5. There was no restart-safe REALISTIC_V2 position persistence.
6. There was no cross-restart execution idempotency journal.
7. There was no state/journal reconciliation.
8. Sequential nine-asset market-data preflight consumed 11.1200591 s, above 50% of the proposed 20 s cycle budget.
9. The initial WAL serializer treated string-backed Enum values as plain strings; this was reproduced by test and corrected by serializing Enum before primitive string types.

## NOT REPRODUCED

The following concerns did not reproduce as regressions:

- no change to BTC LEGACY_V1 benchmark,
- no modification of legacy `scripts/run_paper_live.py`,
- no modification of legacy `AgentLoop`, `AgentEngine`, `TradingEngine`, backtest strategy semantics or frozen strategy parameters,
- no modification of existing legacy `data/live_state`,
- no modification of frozen backtest datasets,
- no real exchange-order submission,
- no unresolved WAL remained after the controlled round trip.

## FILES

Major Phase 08 implementation areas:

- `src/execution/models.py`
- `src/execution/slippage.py`
- `src/execution/broker_interface.py`
- `src/execution/execution_policy.py`
- `src/execution/paper_broker.py`
- `src/execution/runtime.py`
- `src/execution/feature_flags.py`
- `src/execution/signal_adapter.py`
- `src/execution/live_preflight.py`
- `src/execution/state_store.py`
- `src/execution/execution_journal.py`
- `src/data/parallel_market_data_service.py`
- `scripts/run_realistic_paper.py`
- `scripts/run_realistic_smoke_fill.py`
- `scripts/run_realistic_v2_execution_benchmark.py`
- Phase 08 tests under `tests/`
- Phase 08 evidence under `docs/evidence/`

## TESTS AND RESULTS

Key checkpoints:

- B.1 targeted: 77 passed
- B.2 targeted: 86 passed
- B.2 full offline: 427 passed
- B.3 targeted: 98 passed
- B.3 full offline: 439 passed
- B.4 targeted: 117 passed
- B.4 full offline: 458 passed
- B.5 targeted: 129 passed
- B.5 full offline: 470 passed
- B.6B targeted: 94 passed
- B.6B full offline: 477 passed
- B.6C targeted: 89 passed
- B.6C full offline: 484 passed
- B.6D targeted: 96 passed
- B.6D full offline: 491 passed
- B.6E targeted: 103 passed
- B.6E full offline: 498 passed
- B.6F targeted: 86 passed
- B.6F full offline: 500 passed

Final regression evidence is recorded separately under `docs/evidence/`.

All normal Phase 08 offline tests use deterministic fixtures and do not require network access.

## BTC REGRESSION

Frozen BTC LEGACY_V1 golden remained:

- initial balance: 1000.0
- final balance: 1014.8392976799995
- trades: 13
- wins: 7
- losses: 6
- win rate: 53.84615384615385%
- total profit: 14.839297679999504
- max drawdown: 18.485012400000187
- profit factor: 1.692128777090018
- average win: 5.182768514285695
- average loss: 3.573346986666712
- largest win: 13.000798400000047
- largest loss: 9.580003080000042
- expectancy: 1.1414844369230388

Phase 08 did not change this historical execution behavior.

## REALISTIC RESULT

### Deterministic execution benchmark

A dedicated deterministic quote fixture verifies REALISTIC_V2 execution semantics.

It is explicitly labelled:

`DETERMINISTIC_EXECUTION_FIXTURE_NOT_MARKET_PERFORMANCE`

It is not a strategy backtest and is not a claim about market profitability.

Fixture parameters:

- BTCUSDT
- REALISTIC_V2
- realistic_paper
- REAL_BOOK fixture
- 1 bp adverse slippage
- fee rate 0.0004

The benchmark verifies both entry and exit execution pricing, spread, slippage, fees, config-hash consistency and zero residual position after the round trip.

### Live technical smoke

Controlled BTCUSDT paper execution used real market data but did not originate from the trading strategy.

OPEN:

- reference price: 75770.01
- execution price: 75777.58700099999
- slippage: 7.577000999997836
- fee: 0.0030311034800399998

CLOSE:

- reference price: 75654.0
- execution price: 75646.43460000001
- slippage: 7.5653999999922235
- fee: 0.0030258573840000005

Final recovery state:

- open positions: 0
- journal expected open assets: 0
- unresolved WAL: 0
- real exchange orders sent: 0

No PLN conversion or portfolio-accounting conclusion is drawn from these execution observations.

## READINESS CHANGES

Five crypto assets now have verified live execution-path evidence for:

- runtime REALTIME data,
- REAL_BOOK bid/ask execution,
- connected provider,
- open 24/7 crypto session.

However PAPER_READINESS remains NOT_READY because the required PLN FX/accounting layer has not yet been implemented.

Yahoo-backed assets remain blocked for REALISTIC_V2 execution under the current source.

No asset is promoted to FULL, LIMITED or RESEARCH_ONLY solely because the execution kernel is operational.

See `docs/PAPER_READINESS.md`.

## ROLLBACK

Phase 08 is isolated from LEGACY_V1.

Rollback options:

1. keep `REALISTIC_V2` feature flags disabled; this is the default,
2. do not invoke the controlled smoke runner,
3. revert Phase 08 commits on the Phase 08 branch if required,
4. retain LEGACY_V1 and frozen datasets unchanged.

Runtime files under `data/realistic_v2_state/` are separate from legacy live-state storage and are gitignored.

Do not delete state/journal files while a position or unresolved WAL exists.

## HARD STOP

The next accounting/PLN implementation phase requires a new explicit HARD STOP approval before changing:

- PLN/accounting semantics,
- FX conversion semantics,
- realized/unrealized valuation rules,
- persisted accounting data model.

Phase 08 itself does not authorize those changes.

## ZAŁOŻENIA SPECYFIKACJI, KTÓRE OKAZAŁY SIĘ NIEPRAWDZIWE

No contradiction requiring a change to `docs/MASTER_SPEC.md` was identified.

One implementation assumption proved too weak: using the existing sequential market-data cycle for all nine REALISTIC_V2 assets consumed 11.1200591 s, or 55.60% of the 20 s cycle budget.

The Phase 08 implementation was therefore changed to a bounded parallel REALISTIC_V2 market-data service while leaving the original Phase 06 service untouched.

## ZARZUTY Z PROMPTU, KTÓRE NIE POTWIERDZIŁY SIĘ TESTEM

The concern that REALISTIC_V2 integration might alter frozen LEGACY_V1 behavior did not reproduce: the BTC golden remained unchanged throughout Phase 08.

The current Yahoo source did not provide evidence sufficient to treat GOLD_FUT_CONT, WTI_FUT_CONT, EURUSD or AAPL as realistically executable. These assets remained blocked rather than being upgraded through synthetic assumptions.

## DŁUG TECHNICZNY DODANY ŚWIADOMIE W TEJ FAZIE

Known deliberate debt after Phase 08:

- REALISTIC_V2 active-position persistence uses atomic JSON rather than SQLite.
- execution WAL uses JSONL rather than the future ledger database.
- production `run_realistic_paper --execute` remains blocked.
- the controlled smoke runner is a technical validation tool, not the production strategy runner.
- PLN portfolio accounting is not implemented.
- realized/unrealized FX valuation is not implemented.
- global portfolio risk / global HALT belongs to a later phase.
- Yahoo Finance remains unofficial and degraded by design.
- Yahoo-backed assets remain UNTRADEABLE for REALISTIC_V2 under the current evidence.
- GOLD_FUT_CONT and WTI_FUT_CONT remain continuous-futures proxies with rollover limitations.
- calendar coverage limitations identified in Phase 07 remain.
- the parallel market-data service uses bounded threads and hard deadlines but does not yet expose complete production observability metrics.

## WPŁYW NA CZAS TRWANIA CYKLU

Measured nine-asset live-data cycle:

Before bounded parallelization:

- 11.1200591 s
- 55.60% of 20 s budget

After bounded parallelization:

- 2.5214423 s
- 12.61% of 20 s budget

Measured reduction:

- approximately 77.33%
- approximately 4.41x faster for the observed live cycle

No timeout increase was used to obtain this improvement.

## ZMIANY W PAPER_READINESS PER ASSET

After Phase 08:

- BTCUSDT: remains NOT_READY; REALTIME_BOOK and REAL_BOOK now live-verified, FX unavailable.
- ETHUSDT: remains NOT_READY; REALTIME_BOOK and REAL_BOOK now live-verified, FX unavailable.
- SOLUSDT: remains NOT_READY; REALTIME_BOOK and REAL_BOOK now live-verified, FX unavailable.
- BNBUSDT: remains NOT_READY; REALTIME_BOOK and REAL_BOOK now live-verified, FX unavailable.
- XRPUSDT: remains NOT_READY; REALTIME_BOOK and REAL_BOOK now live-verified, FX unavailable.
- GOLD_FUT_CONT: remains NOT_READY; runtime feed observed STALE and execution UNTRADEABLE.
- WTI_FUT_CONT: remains NOT_READY; runtime feed observed STALE and execution UNTRADEABLE.
- EURUSD: remains NOT_READY; runtime data quality observed UNKNOWN and execution UNTRADEABLE.
- AAPL: remains NOT_READY; runtime data quality observed UNKNOWN and execution UNTRADEABLE.

The weakest required readiness dimension continues to determine overall PAPER_READINESS.

## CZY WYMAGANY JEST HARD STOP PRZED NASTĘPNĄ FAZĄ

**TAK.**

Before implementing Phase 09 PLN/FX/accounting semantics, explicit approval is required.

Phase 09 must not begin implementation until the user approves the accounting/FX HARD STOP.
