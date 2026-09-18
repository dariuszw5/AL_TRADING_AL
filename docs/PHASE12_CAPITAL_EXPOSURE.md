# Phase 12 A.4 — BTCUSDT Proposed Exposure Calculator

HARD STOP 12A requires capital admission for controlled REALISTIC_V2 LONG
entries to use gross exposure in PLN, not legacy balance and not an implicit
USDT/USD equivalence.

A.4 adds a pure BTCUSDT proposed-exposure calculator. It is not wired into the
runtime yet and therefore does not change execution behavior.

## Controlled scope

A.4 supports only:

- asset: `BTCUSDT`,
- direction: proposed LONG entry,
- execution quality: `REAL_BOOK`.

Other assets and simulated/derived execution-quality paths fail closed in this
step.

## Proposed execution price

For a LONG entry the calculator mirrors the existing REAL_BOOK BUY path:

1. reference price = market `ASK`,
2. apply the existing injected slippage model with `OrderSide.BUY`,
3. gross native notional =
   `proposed_execution_price * quantity`.

No entry fee is added to proposed exposure. The accepted Phase 12 semantics
retain:

`ENTRY_FEE_SETTLED_AT_REALIZATION`

and OPEN does not mutate settled cash.

## Explicit FX path

BTCUSDT native notional is in `USDT`.

PLN exposure is calculated only through the existing converter path:

`USDT -> USD -> PLN`

The calculator never assumes `USDT = USD`.

A missing `USDTUSD` leg therefore fails closed.

## Capital-admission FX reliability

The existing converter distinguishes:

- `FX_FRESH`,
- `FX_STALE`,
- `FX_UNAVAILABLE`.

For a new capital-admission decision, A.4 accepts only `FX_FRESH`.

`FX_STALE` is deliberately fail-closed and carries:

`CAPITAL_EXPOSURE_FX_FRESH_REQUIRED`

This does not change Phase 09 MTM semantics, where stale FX may still be
reported as available. It is a narrower rule for admitting a new position.

## Numeric boundary

The existing FX converter has a float-based public amount boundary. A.4 does
not silently replace or fork that converter.

The proposed execution price, quantity and returned PLN amount are captured as
`Decimal(str(value))` at the Phase 12 boundary. A future precision migration
would require separate scope.

## Not implemented in A.4

A.4 does not:

- read the Phase 11 cash ledger,
- enforce the capital limit inside the runtime,
- modify `PaperBroker`,
- modify REALISTIC_V2 orchestration,
- add the Phase 12 feature flag,
- create Phase 12 startup metadata,
- reserve or debit capital,
- implement margin/collateral/leverage,
- implement short financing,
- change synthetic-short behavior,
- modify persistence formats,
- change LEGACY_V1 or the frozen strategy.

The next step may wire the A.3 admission core and A.4 exposure calculator into
a controlled, feature-flagged REALISTIC_V2 admission wrapper.
