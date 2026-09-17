# PHASE 09 - PLN / FX / ACCOUNTING REPORT

Date: 2026-09-17

Branch: `phase-09-pln-fx-accounting`

Phase start base: `be4b9c4`

Final implementation commit before closure: `ccfd10c`

## SCOPE

Phase 09 implemented deterministic PLN / FX / accounting foundations
without changing LEGACY_V1, frozen strategy parameters, existing
execution semantics, existing assertions, existing live_state data or
starting a SQLite migration.

The Phase 09 hard-stop approval covered PLN / FX / accounting semantics.
It did not authorize JSON-to-SQLite migration, frozen-strategy changes,
dependency additions, assertion changes, live_state rewrites or deletion
of protected evidence files.

## VERIFIED

- deterministic FX conversion kernel,
- deterministic FX provider adapters,
- realized FX source-selection policy,
- immutable realized FX booking evidence,
- Decimal realized PLN accounting,
- Decimal unrealized PLN MTM,
- instrument accounting contracts,
- PLN portfolio snapshot kernel,
- global normalized configuration fingerprint,
- exact production FX freshness policy,
- runtime resolution of Phase 09 feature flags,
- fail-closed runtime accounting bridge,
- additive REALISTIC_V2 accounting integration,
- per-asset accounting-failure isolation,
- restart fail-closed behavior when complete entry Execution evidence is
  unavailable,
- continuous-futures accounting remains blocked,
- LEGACY_V1 BTC regression remains unchanged.

## FIXED

- ambiguous FX freshness boundaries were frozen to exact behavior,
- Yahoo canonical USD/PLN runtime symbol was documented as `PLN=X`,
- realized FX booking no longer needs a fabricated intraday timestamp for
  a daily source that does not provide one,
- PLN arithmetic uses Decimal kernels,
- accounting integration no longer needs to modify execution runtime
  semantics,
- the A.15 test mismatch between Decimal and float was corrected in the
  new A.15 test only; production accounting output was already correct.

## NOT REPRODUCED

No Phase 09 evidence reproduced a need to change:

- LEGACY_V1 strategy semantics,
- PaperBroker execution pricing semantics,
- frozen BTC strategy parameters,
- existing live_state data,
- existing test assertions.

No evidence justified enabling futures multipliers or treating Yahoo as a
reliable official realtime source.

## FILES

Major Phase 09 implementation surfaces include:

- `src/fx/`
- `src/accounting/feature_flags.py`
- `src/accounting/pln_kernel.py`
- `src/accounting/mtm_kernel.py`
- `src/accounting/instrument_contracts.py`
- `src/accounting/portfolio_snapshot.py`
- `src/accounting/runtime_bridge.py`
- `src/accounting/runtime_integration.py`
- `src/config_fingerprint.py`
- `src/runtime_feature_flags.py`
- `scripts/run_realistic_paper.py`
- Phase 09 tests, ADRs, evidence and policy documentation.

Phase 09 closure modifies documentation/evidence only.

## TESTS

Final pre-closure implementation evidence:

- A.15 corrected previously failing Decimal assertion: `1 passed`,
- A.15 targeted suite: `263 passed`,
- full offline regression: `715 passed`,
- restored user `tests/test_agent_config.py`: `8 passed`,
- BTC LEGACY_V1 golden: exact match.

The Phase 09 closure reruns the full offline regression and BTC golden and
stores the output in `docs/evidence/PHASE09_A16_FINAL_VALIDATION.txt`.

## BTC REGRESSION

Expected and verified BTC LEGACY_V1 golden:

- final capital: `1014.8392976799995`
- trades: `13`
- win rate: `53.84615384615385`
- total profit: `14.839297679999504`
- max drawdown: `18.485012400000187`
- profit factor: `1.692128777090018`
- expectancy: `1.1414844369230388`

Phase 09 does not alter this behavior.

## REALISTIC_V2 RESULT

Phase 09 adds an accounting integration wrapper around the already
existing REALISTIC_V2 runtime. The wrapper is additive and post-cycle:
execution runs first, then accounting is calculated.

The public `scripts/run_realistic_paper.py` remains PRE-FLIGHT ONLY and
does not submit paper or real orders.

No market-performance claim is made from deterministic accounting tests.

No new real-exchange order capability is enabled.

## READINESS

Phase 09 does not promote any asset out of NOT_READY.

Reason: the production REALISTIC_V2 entrypoint does not yet construct the
verified accounting integration with production FX, exit-fee and cash
resolvers.

This is intentionally more conservative than promoting FX_QUALITY based
only on component tests.

The current per-asset table is recorded in `docs/PAPER_READINESS.md`.

## ROLLBACK

Phase 09 is split across additive commits and feature-flagged components.

Rollback can be performed by reverting Phase 09 commits in reverse order
while preserving:

- the Phase 08 base,
- frozen LEGACY_V1 behavior,
- user-owned uncommitted work,
- protected evidence files,
- existing live_state data.

No database or live_state data migration needs rollback because Phase 09
did not perform one.

## ZAŁOŻENIA SPECYFIKACJI, KTÓRE OKAZAŁY SIĘ NIEPRAWDZIWE

1. It could not be assumed that a daily-reference FX source exposes a
   reliable intraday publication timestamp. NBP evidence therefore keeps
   `fx_timestamp=null` when such a timestamp is not supplied and stores
   source/table/effective-date evidence instead.

2. It could not be assumed that `USDPLN=X` had to be the sole Yahoo symbol
   for USD/PLN. The empirical probe showed alias-like behavior; `PLN=X`
   was selected as the canonical runtime symbol.

3. It could not be assumed that a persisted Position contains enough
   evidence for exact realized accounting after restart. The complete
   entry Execution includes fee/bid/ask/slippage data not recoverable from
   Position.entry_price alone.

4. It could not be assumed that adding accounting kernels automatically
   makes production FX/accounting available. Production runtime
   construction still needs explicit resolver wiring.

## ZARZUTY Z PROMPTU, KTÓRE NIE POTWIERDZIŁY SIĘ TESTEM

- No test evidence showed a regression in frozen BTC LEGACY_V1 caused by
  Phase 09.
- No evidence required a change to PaperBroker execution-price semantics.
- No evidence justified changing existing assertions.
- No evidence justified activating GOLD_FUT_CONT or WTI_FUT_CONT
  accounting multipliers.
- No evidence justified treating an unavailable or future-dated FX quote
  as usable.
- No evidence justified silently treating USDT as USD.

## DŁUG TECHNICZNY DODANY ŚWIADOMIE W TEJ FAZIE

- accounting records are not persisted,
- full entry Execution evidence in the additive wrapper is in-memory only,
- production FX resolver construction is not wired to the public
  REALISTIC_V2 entrypoint,
- estimated exit fee and cash PLN remain injected caller responsibilities,
- continuous-futures accounting remains blocked,
- FX conversion cost is not modelled,
- Yahoo remains unofficial / degraded by design.

This debt is explicit and fail-closed rather than hidden.

## WPŁYW NA CZAS TRWANIA CYKLU

Phase 09 did not replace or modify the Phase 08 market-data scheduler.

The previously measured nine-asset market-data cycle remains the latest
live cycle measurement: `2.5214423 s`, which was `12.61%` of the `20 s`
budget.

Phase 09 accounting tests are deterministic and do not establish a new
live-cycle latency measurement. Production accounting resolver wiring
must be benchmarked before readiness promotion.

## ZMIANY W PAPER_READINESS PER ASSET

No asset is promoted in Phase 09.

- BTCUSDT: remains NOT_READY.
- ETHUSDT: remains NOT_READY.
- SOLUSDT: remains NOT_READY.
- BNBUSDT: remains NOT_READY.
- XRPUSDT: remains NOT_READY.
- GOLD_FUT_CONT: remains NOT_READY and accounting-blocked.
- WTI_FUT_CONT: remains NOT_READY and accounting-blocked.
- EURUSD: remains NOT_READY.
- AAPL: remains NOT_READY.

The decisive reason is production-wiring readiness, not lack of tested
accounting kernels.

## CZY WYMAGANY JEST HARD STOP PRZED NASTĘPNĄ FAZĄ

No additional HARD STOP is required merely to close Phase 09.

A new explicit HARD STOP is required before any future work that changes
a protected semantic/storage boundary, including:

- JSON-to-SQLite or another persistence migration,
- execution semantics,
- frozen strategy parameters,
- existing assertions,
- existing live_state data,
- deletion of protected files,
- dependency additions when approval is required.

Production wiring that remains strictly additive and preserves the
already-approved semantics should first be scoped against the next phase
contract. If that wiring requires any protected boundary above, stop for
approval before implementation.
