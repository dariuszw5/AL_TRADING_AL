# Instrument Accounting Contract

## Status

Phase 09 A.9 defines the accounting contract for every canonical asset
currently targeted by the application.

This is an accounting contract, not an execution-readiness or
PAPER_READINESS declaration.

The contract is isolated from LEGACY_V1.

## Why this layer exists

The current generic risk/exposure implementation uses unit-based sizing.

Current exposure logic effectively uses:

```text
max_position_size
    = max_exposure_value / entry_price
```

and the current risk sizing uses price distance without an instrument
contract multiplier.

That is internally compatible with unit-based instruments whose native
PnL is:

```text
price_delta * quantity
```

but it is not sufficient for standard futures contracts.

A.9 therefore refuses to apply one universal multiplier to every asset.

## Runtime-accounting-ready instruments

The following accounting contracts use `pnl_multiplier = 1`.

| Asset | Instrument type | Quantity semantics | Native PnL currency |
| --- | --- | --- | --- |
| BTCUSDT | spot_reference | BASE_UNITS | USDT |
| ETHUSDT | spot_reference | BASE_UNITS | USDT |
| SOLUSDT | spot_reference | BASE_UNITS | USDT |
| BNBUSDT | spot_reference | BASE_UNITS | USDT |
| XRPUSDT | spot_reference | BASE_UNITS | USDT |
| EURUSD | fx_spot_reference | BASE_UNITS | USD |
| AAPL | equity_reference | SHARES | USD |

For these instruments:

```text
native_notional
    = quantity
    * price
    * pnl_multiplier
```

and currently:

```text
pnl_multiplier = 1
```

The contract uses `Decimal(str(value))` at the financial boundary.

## Accounting readiness is not PAPER_READINESS

`runtime_accounting_ready = True` means only that the quantity / price /
native-currency accounting formula is structurally defined.

It does not mean:

- the market data is realtime,
- the execution source is tradeable,
- the FX path is currently available,
- the session calendar is complete,
- shorting is supported,
- overall PAPER_READINESS is FULL.

Those remain separate contracts.

## GOLD_FUT_CONT

Canonical app instrument:

```text
GOLD_FUT_CONT
```

Provider reference:

```text
Yahoo GC=F
```

Instrument type:

```text
continuous_future_proxy
```

Official CME reference for the standard GC contract:

```text
product code: GC
contract unit: 100 troy ounces
price quotation: USD per troy ounce
```

The `100` value is stored only as:

```text
reference_contract_multiplier
```

It is not activated as runtime `pnl_multiplier`.

## WTI_FUT_CONT

Canonical app instrument:

```text
WTI_FUT_CONT
```

Provider reference:

```text
Yahoo CL=F
```

Instrument type:

```text
continuous_future_proxy
```

Official CME reference for the standard CL contract:

```text
product code: CL
contract unit: 1000 barrels
price quotation: USD per barrel
```

The `1000` value is stored only as:

```text
reference_contract_multiplier
```

It is not activated as runtime `pnl_multiplier`.

## Why futures remain blocked

Activating GC=100 or CL=1000 directly in accounting would be unsafe
because the current runtime does not yet establish that `quantity`
means standard whole futures contracts.

The current generic sizing layer is multiplier-unaware.

The current PaperBroker fee model is also generic:

```text
execution_price * quantity * trading_fee_rate
```

and is not a verified exchange-style per-contract futures fee model.

The continuous series additionally retains the existing rollover
limitation.

Therefore both futures proxies fail closed with:

```text
CONTINUOUS_FUTURE_PROXY
FUTURES_RUNTIME_QUANTITY_SEMANTICS_UNVERIFIED
FUTURES_FEE_MODEL_NOT_CONTRACT_AWARE
CONTINUOUS_FUTURE_ROLLOVER_UNRESOLVED
```

Their runtime `pnl_multiplier` remains:

```text
None
```

This is intentional.

## External reference

CME Group documents the standard contract units used as reference facts:

Gold futures GC:

```text
100 troy ounces
```

WTI crude oil futures CL:

```text
1000 barrels
```

These external reference facts do not by themselves make the app's
continuous futures proxy runtime-accounting-ready.

## Fail closed

A.9 rejects:

- unknown asset IDs,
- asset registry instrument-type drift,
- asset registry quote-currency drift,
- non-positive quantity,
- non-positive price,
- use of `native_notional()` for a blocked contract,
- request for a runtime accounting contract for a blocked instrument.

## Phase boundary

A.9 does not:

- modify risk sizing,
- modify StrategyEngine,
- modify PaperBroker,
- modify execution prices,
- modify fee calculation,
- modify the existing asset registry,
- enable futures accounting in runtime,
- change LEGACY_V1,
- modify live_state,
- introduce SQLite,
- add dependencies,
- modify existing assertions,
- integrate accounting into cash/equity/exposure yet.

Changing futures position sizing, fee semantics, or execution quantity
semantics would be an execution-semantics change and requires a separate
explicit HARD STOP before implementation.