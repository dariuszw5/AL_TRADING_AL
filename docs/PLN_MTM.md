# PLN Unrealized PnL / MTM Policy

## Status

Phase 09 A.8 introduces an isolated deterministic MTM kernel.

It does not integrate with the paper runtime yet.

It does not modify:

- LEGACY_V1,
- PaperBroker execution semantics,
- live_state,
- JSON persistence,
- SQLite,
- frozen strategy parameters.

## Mark price

A.8 uses liquidation-side book prices:

```text
LONG  -> bid
SHORT -> ask
```

It does not substitute midpoint.

This keeps current spread impact inside the mark.

## Exit slippage

A.8 does not apply predicted exit slippage.

It records:

```text
MTM_EXIT_SLIPPAGE_NOT_MODELLED
```

as an explicit limitation.

A later integration layer may supply an execution-model estimate, but
A.8 does not invent one.

## Unrealized PnL vs estimated liquidation PnL

The preflight did not establish a MASTER_SPEC rule saying that estimated
future exit fees must be silently deducted from the displayed unrealized
PnL.

Therefore A.8 exposes two separate values.

Price MTM:

```text
unrealized_pnl_native
```

Explicit estimated liquidation value:

```text
estimated_net_liquidation_pnl_native
    = unrealized_pnl_native
    - estimated_exit_fee_native
```

The exit fee is caller-supplied and mandatory, even when it is zero.

A.8 does not choose which of these future portfolio equity aggregation
must use. That choice must be explicit in the later cash/equity policy.

## LONG formula

```text
(bid - entry_price)
* quantity
* pnl_multiplier
```

## SHORT formula

```text
(entry_price - ask)
* quantity
* pnl_multiplier
```

## Decimal boundary

All financial values cross into accounting through:

```text
Decimal(str(value))
```

No implicit rounding or quantization occurs in the core.

## FX freshness

A.8 follows the existing Phase 09 freshness contract.

```text
FX_FRESH
    PLN available normally

FX_STALE
    PLN available
    state remains FX_STALE
    quote age must be explicit

FX_UNAVAILABLE
    native MTM remains available
    PLN fields are None
    unavailable reason is required
```

For a native PLN instrument:

```text
fx_rate = 1
fx_path = PLN
fx_freshness = FX_FRESH
```

No external FX quote is required.

## FX source selection

A.8 does not choose FX providers.

It consumes already resolved FX state/rate/path supplied by the future
integration layer.

Provider selection and temporal freshness remain responsibilities of the
existing Phase 09 FX components.

## Instrument multiplier

A.8 requires an explicit positive `pnl_multiplier`.

The Phase 09 A.8 preflight found no `contract_multiplier` or equivalent
verified multiplier in the current asset registry.

Therefore runtime integration across all assets remains blocked until a
verified multiplier contract is introduced.

In particular, A.8 does not invent contract multipliers for:

```text
GOLD_FUT_CONT
WTI_FUT_CONT
```

These remain continuous-futures proxies with the existing contract and
rollover limitations.

## Runtime integration boundary

A.8 intentionally does not depend on the concrete market-snapshot class.

The preflight search did not establish its public contract in the scoped
market module.

The kernel receives explicit:

```text
bid
ask
```

and can later be wired to a verified snapshot adapter without changing
its accounting semantics.

## Phase boundary

A.8 does not:

- mutate cash,
- mutate equity,
- mutate exposure,
- persist a financial ledger,
- change execution prices,
- change fee calculation,
- update live_state,
- add dependencies,
- alter existing test assertions,
- integrate FX flags into config_hash.

Those remain separate Phase 09 steps.