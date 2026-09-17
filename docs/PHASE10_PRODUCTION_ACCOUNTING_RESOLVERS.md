# Phase 10 A.2 - Production Accounting Resolvers

## Scope

A.2 adds the production resolver layer needed by the Phase 09
REALISTIC_V2 accounting wrapper.

It does not enable the public paper-execution entrypoint.

It does not change execution semantics, PaperBroker, persistence,
LEGACY_V1, frozen strategy parameters, existing assertions or live_state.

## FX prefetch model

`ProductionFxResolver` prefetches only the FX paths needed by the assets
in the requested cycle.

For a USDT-native asset:

- MTM evidence: Coinbase USDT/USD + Yahoo USD/PLN,
- realized evidence: Coinbase USDT/USD + NBP USD/PLN.

For a USD-native asset:

- MTM evidence: Yahoo USD/PLN,
- realized evidence: NBP USD/PLN.

For an EUR-native asset:

- MTM evidence: Yahoo EUR/PLN,
- realized evidence: NBP EUR/PLN.

No implicit USDT = USD conversion is introduced.

FX requests are deduplicated per cycle.

## Why realized evidence is prefetched before execution

The Phase 09 realized-selection policy permits a same-day NBP reference
only when the system actually observed it no later than the trade close.

Therefore A.2 prefetches NBP reference evidence before the execution
cycle. It never fabricates a publication timestamp.

A provider failure is recorded in accounting state. Missing FX legs then
fail closed in the existing converter/bridge. Accounting provider failure
does not alter PaperBroker execution semantics.

## Exit fee estimate

`BrokerExitFeeEstimator` uses the same configured fee rate exposed by the
existing PaperBroker.

The estimate uses the liquidation-side mark:

- LONG -> bid,
- SHORT -> ask.

It does not predict exit slippage. The Phase 09 limitation that exit
slippage is not modelled remains explicit.

## Realized policy thresholds

A.2 deliberately does not invent a production
`daily_reference_max_age_days` value.

The wiring function requires both realized-source thresholds from the
caller:

- `realized_market_max_age_seconds`,
- `realized_daily_reference_max_age_days`.

The already accepted MTM freshness policy continues to come from
`production_fx_freshness_policy()`.

## Cash PLN

A.2 does not invent a cash ledger.

`cash_pln_resolver` remains optional and defaults to `None`.

Without an explicit resolver the portfolio snapshot is not fabricated.

## Futures

Blocked continuous-futures accounting contracts remain blocked.

A.2 does not activate the documented reference multipliers for
`GOLD_FUT_CONT` or `WTI_FUT_CONT`.

## Next boundary

A later Phase 10 step may gate this wiring behind the existing Phase 09
runtime flags and connect it to a controlled REALISTIC_V2 construction
path.

That step must also address reproducibility metadata/global config hash
for the resolved accounting policy values before readiness can advance.
