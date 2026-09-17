# PLN Accounting Policy

## Status

Phase 09 A.7 introduces a deterministic, isolated accounting kernel.

It does not modify REALISTIC_V2 execution semantics and it does not
modify LEGACY_V1.

It does not persist a ledger and it does not introduce SQLite.

## Decimal boundary

Financial accounting values are converted with:

```text
Decimal(str(value))```

The kernel does not use:

```text
Decimal(float_value)
```

No implicit PLN rounding or quantization is performed in A.7.

Presentation rounding is a separate concern.

## Realized execution-price PnL

REALISTIC_V2 PaperBroker selects:

- ask for BUY,
- bid for SELL,

and then applies the configured slippage model to that side-specific
reference price.

Therefore the resulting execution price already contains the
economic effect of:

- spread,
- slippage.

The accounting kernel calculates price PnL from the actual entry and
exit execution prices.

LONG:

```text
(exit_execution_price - entry_execution_price)
* quantity
* pnl_multiplier
```

SHORT:

```text
(entry_execution_price - exit_execution_price)
* quantity
* pnl_multiplier
```

## Fees

Execution.fee is a separate monetary amount.

For a completed round trip:

```text
fees_native = entry_fee + exit_fee
```

and:

```text
net_realized_pnl_native
    = price_pnl_native
    - fees_native
```

Fees are deducted exactly once.

## Spread and slippage attribution

`spread_cost_native` and `slippage_cost_native` are reporting and
cost-attribution values.

They are not additional deductions from realized PnL because their
price effect is already embedded in the actual execution prices.

Critical invariant:

```text
net_realized_pnl_native
    = price_pnl_native
    - fees_native
```

Not:

```text
price_pnl_native
- fees_native
- spread_cost_native
- slippage_cost_native
```

## PLN conversion

A.7 receives an explicit FX rate and FX path.

Each native accounting value is translated to PLN with the same
explicit FX rate:

```text
value_pln = value_native * fx_rate
```

A.7 does not choose FX providers.

FX source selection remains the responsibility of the Phase 09 FX
policy and realized FX selection components.

## Instrument multiplier

`pnl_multiplier` is mandatory.

The kernel intentionally has no universal default multiplier.

This prevents an implicit assumption that:

```text
quantity * price_delta
```

has identical monetary meaning for crypto, stocks, FX and futures
proxies.

A verified instrument contract must supply the appropriate multiplier
before runtime accounting integration.

GOLD_FUT_CONT and WTI_FUT_CONT remain subject to their existing proxy
and contract-semantics limitations.

## Fail-closed rules

The kernel rejects:

- mismatched assets,
- mismatched entry/exit quantities,
- invalid LONG/SHORT execution directions,
- non-positive quantity,
- non-positive pnl multiplier,
- non-positive FX rate,
- invalid bid/ask,
- negative fee,
- negative slippage,
- missing required execution fields.

## Phase boundary

A.7 does not:

- modify PaperBroker,
- update paper cash,
- update equity,
- update exposure,
- persist financial events,
- migrate JSON state,
- modify live_state,
- introduce SQLite,
- change frozen strategy parameters,
- change existing test assertions,
- add a dependency,
- integrate FX feature flags into config_hash.

The `AL_TRADING_FX_ENABLED` / config_hash metadata requirement remains
open and must be resolved before Phase 09 closure.
