# PHASE 05 — ASSET REGISTRY AND CENTRAL CONFIG

Date: 2026-09-16

Branch: `phase-05-asset-registry-config`

Baseline:
- Phase 04 commit: `a50fb3c`
- MASTER_SPEC commit: `98f6b7d`

## SUMMARY

Phase 05 introduced one central asset/config model without changing
LEGACY_V1 execution semantics.

Implemented:
- AssetClass
- ValidationStatus
- AssetConfig
- StrategyConfig
- RiskConfig
- ExecutionConfig
- ProviderConfig metadata reference
- startup/fail-fast validation
- canonical asset identities
- compatibility aliases for legacy state keys

Canonical assets:
- BTCUSDT
- ETHUSDT
- SOLUSDT
- BNBUSDT
- XRPUSDT
- GOLD_FUT_CONT
- WTI_FUT_CONT
- EURUSD
- AAPL

`GC=F` and `CL=F` are represented explicitly as
`continuous_future_proxy`.

BTC remains FROZEN.

Every non-BTC asset remains EXPERIMENTAL.

REALISTIC_V2 was not implemented.

## BUGS / ISSUES VERIFIED

Confirmed configuration drift existed between the asset registry,
multi-asset runner and API status representation.

The backend contained duplicated frozen strategy constants instead of
reading them from one central asset configuration.

The project also used XAUUSD / WTIUSD as application-facing identities
even though the actual Yahoo provider instruments are GC=F / CL=F.

## BUGS FIXED

- central AssetConfig registry established
- nested strategy/risk/execution configs centralized
- backend strategy values now come from AssetRegistry
- provider metadata reference centralized
- canonical GOLD_FUT_CONT and WTI_FUT_CONT identities introduced
- continuous futures proxy limitation encoded explicitly
- registry validation is fail-fast
- VALIDATED/FROZEN require validation_reference
- continuous futures proxy cannot be promoted above EXPERIMENTAL
- short mechanism consistency validated
- legacy XAUUSD / WTIUSD persisted state paths preserved through state_key
- no live-state migration performed

## CLAIMS THAT DID NOT REPRODUCE

None in this phase.

Phase 05 was a configuration consolidation task rather than a
reproduce-before-fix bug investigation phase.

## CHANGED FILES

- `src/data/assets.py`
- `src/agent/multi_asset_runner.py`
- `app/backend/main.py`
- `scripts/run_paper_live.py`

## NEW FILES

- `tests/test_asset_registry_config.py`
- `docs/PHASE_05_ASSET_REGISTRY_CONFIG_REPORT.md`

`docs/PAPER_READINESS.md` is created or updated as required by the
master contract.

## TESTS ADDED

Coverage includes:
- all required assets exist
- no shared nested config objects
- invalid config fails fast
- short mechanism matches allow_short
- VALIDATED requires validation reference
- BTC frozen config unchanged
- GOLD/WTI canonical futures proxy identity
- legacy aliases remain compatibility-only
- non-BTC assets remain EXPERIMENTAL
- provider metadata is centralized
- continuous futures proxy cannot be promoted above EXPERIMENTAL
- backend keeps legacy state path while exposing canonical identity
- backend strategy data comes from AssetRegistry

Existing multi-asset assertions were preserved.

## TEST RESULT

Phase 05 targeted tests:
PASS

Full offline regression:
`353 passed in 147.84s`

No network-dependent test was required for Phase 05 validation.

## LEGACY BTC REGRESSION RESULT

Execution profile:
LEGACY_V1

Dataset:
BTCUSDT 1m, 5000 frozen candles

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

Benchmark exit code:
0

The frozen BTC LEGACY_V1 result is unchanged.

## REALISTIC RESULT

Not applicable in Phase 05.

REALISTIC_V2 was intentionally not implemented or executed.

## PAPER_READINESS CHANGES

No asset was promoted to a higher PAPER_READINESS level in this phase.

This phase established truthful instrument identity and validation
status only.

Validation status:
- BTCUSDT: FROZEN
- ETHUSDT: EXPERIMENTAL
- SOLUSDT: EXPERIMENTAL
- BNBUSDT: EXPERIMENTAL
- XRPUSDT: EXPERIMENTAL
- GOLD_FUT_CONT: EXPERIMENTAL
- WTI_FUT_CONT: EXPERIMENTAL
- EURUSD: EXPERIMENTAL
- AAPL: EXPERIMENTAL

GOLD_FUT_CONT and WTI_FUT_CONT are explicitly PROXY instruments.

Data quality, execution quality, FX quality and session quality are not
promoted by Phase 05 and remain subject to later phases.

## SPEC ASSUMPTIONS THAT WERE FALSE

No new contradiction requiring a MASTER_SPEC change was discovered.

The pre-existing XAUUSD / WTIUSD naming was not an accurate canonical
description of the provider instruments. The master specification
already anticipated and resolved this by requiring futures-proxy
identities.

## NEW TECHNICAL DEBT

Intentional compatibility debt:
- legacy state filenames XAUUSD / WTIUSD remain supported through
  `state_key`
- no live-state migration was performed
- tick size, quantity step, minimum quantity and minimum notional remain
  unset when they have not yet been sourced reliably from provider
  metadata
- REALISTIC_V2 remains outside this phase

## CYCLE DURATION IMPACT

No dedicated performance benchmark was required.

Phase 05 adds in-memory config lookups only and introduces no new
external dependency or provider call.

## ROLLBACK PLAN

Rollback the Phase 05 implementation commit.

The separate MASTER_SPEC commit may remain because it is project
documentation and does not alter trading execution.

No database migration or live-state migration is involved.

## HARD STOP REQUIRED BEFORE NEXT PHASE

No new HARD STOP is required to begin Prompt 06.

Any later change to execution semantics, PLN booking, SQLite migration,
existing assertions, frozen BTC parameters, dependencies or live-state
migration remains subject to the MASTER_SPEC HARD STOP rules.
