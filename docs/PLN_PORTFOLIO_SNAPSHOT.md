# PLN Portfolio Snapshot Policy

## Status

Phase 09 A.10 adds a pure deterministic portfolio-level PLN snapshot
kernel.

It aggregates the isolated accounting contracts introduced in A.7-A.9.

It is not yet wired into REALISTIC_V2 runtime state.

## Why cash is an input

The A.10 preflight confirmed that the new PLN accounting kernels are not
currently integrated into the runtime cash/equity state.

A.10 therefore does not invent a cash-ledger mutation policy.

The kernel receives:

```text
cash_pln
```

as already-settled PLN cash supplied by a future runtime/ledger adapter.

This avoids a serious double-booking risk.

A.7 realized PnL already contains entry and exit fees in:

```text
net_realized_pnl_pln
```

while A.8 separately exposes a future estimated exit fee for an open
position.

Until the runtime booking policy explicitly defines when execution fees
hit cash, A.10 must not replay realized records into cash automatically.

## Equity

Normal mark-to-market equity is:

```text
equity_pln
    = cash_pln
    + sum(unrealized_pnl_pln)
```

This does not pre-charge a future close fee.

The kernel also exposes:

```text
estimated_liquidation_equity_pln
    = cash_pln
    + sum(estimated_net_liquidation_pnl_pln)
```

This is a separate close-now estimate and includes the estimated exit fee
already supplied by A.8.

The two values must not be conflated.

## Exposure

A.10 defines gross mark-side exposure as:

```text
native_notional
    = quantity
    * mark_price
    * verified pnl_multiplier

exposure_pln
    = native_notional
    * fx_rate
```

The mark price is the A.8 liquidation-side mark:

```text
LONG  -> bid
SHORT -> ask
```

`exposure_pln` is:

- gross market notional,
- not PnL,
- not margin requirement,
- not free cash,
- not risk-at-stop.

## Instrument contract enforcement

Every open position must match the A.9 instrument accounting contract.

A.10 rejects:

- unknown instruments,
- blocked instrument accounting contracts,
- native-currency mismatch,
- PnL-multiplier mismatch.

Therefore the two continuous futures proxies remain fail-closed:

```text
GOLD_FUT_CONT
WTI_FUT_CONT
```

A.10 does not activate their CME reference multipliers.

## FX aggregation

Portfolio FX quality is weakest-position-wins.

```text
all FRESH
    -> FX_FRESH

at least one STALE, none unavailable
    -> FX_STALE

at least one UNAVAILABLE
    -> FX_UNAVAILABLE
```

For `FX_STALE`, PLN totals remain available and the maximum observed FX
quote age is preserved.

For `FX_UNAVAILABLE`, settled PLN cash remains known, but:

```text
unrealized_pnl_pln = None
equity_pln = None
estimated_liquidation_equity_pln = None
exposure_pln = None
```

The kernel never silently drops the unavailable position and reports a
partial portfolio total as if it were complete.

## Duplicate positions

A portfolio snapshot must contain at most one MTM record for a given
`position_id`.

Duplicates fail closed.

## Decimal boundary

A.10 uses:

```text
Decimal(str(value))
```

for caller-supplied financial values.

No implicit PLN rounding or quantization is performed.

## Known limitations

A.10 intentionally retains:

```text
PORTFOLIO_CASH_IS_CALLER_SUPPLIED
```

because runtime cash booking is not yet integrated.

A.8 limitations, including:

```text
MTM_EXIT_SLIPPAGE_NOT_MODELLED
```

are propagated into the portfolio snapshot.

When any position has unavailable PLN conversion, A.10 adds:

```text
PORTFOLIO_PLN_INCOMPLETE_DUE_TO_FX
```

## Phase boundary

A.10 does not:

- modify AgentEngine,
- modify legacy PaperTrading,
- modify BacktestEngine,
- modify PaperBroker,
- modify StrategyEngine,
- mutate live_state,
- persist a ledger,
- introduce SQLite,
- add dependencies,
- modify frozen strategy parameters,
- change existing test assertions,
- enable FX/accounting runtime flags,
- change config_hash.

The next Phase 09 step must resolve feature flags/config_hash before
runtime PLN accounting is enabled.