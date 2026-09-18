# Phase 12 A.3 — Cash-backed Capital Admission Core

HARD STOP 12A authorizes cash-backed capital admission for new LONG ENTRY in
the controlled REALISTIC_V2 path.

A.3 implements only the pure admission policy. It does not wire the policy to
the runtime and therefore changes no execution behavior yet.

## Authoritative capital source

The core accepts only:

`settled_cash_pln`

as capital input.

It has no `initial_balance`, `balance`, `simulation_units`, margin, collateral
or leverage input.

The later controlled runtime wiring must source `settled_cash_pln` only from
the verified Phase 11 cash ledger.

## Capital limit

The exact rule is:

`capital_limit_pln = max(0, settled_cash_pln) * max_exposure_percent / 100`

`max_exposure_percent` must be finite and in `(0, 100]`.

No implicit rounding or quantization is applied.

## LONG entry rule

A LONG entry is admitted only when:

- authoritative settled cash is available,
- settled cash is positive,
- proposed gross exposure PLN is available,
- proposed gross exposure PLN is positive and finite,
- proposed gross exposure PLN is less than or equal to the capital limit.

Equality with the limit is allowed.

## Fail-closed outcomes

The pure policy exposes explicit reasons:

- `CAPITAL_SOURCE_UNAVAILABLE`
- `SETTLED_CASH_NONPOSITIVE`
- `EXPOSURE_UNAVAILABLE`
- `EXPOSURE_INVALID`
- `CAPITAL_LIMIT_EXCEEDED`

A valid admitted decision uses:

- `ALLOWED`

Invalid `max_exposure_percent` is treated as configuration corruption and
raises `CapitalAdmissionPolicyError`.

## Fee timing

The policy does not reserve or deduct entry fee.

The existing explicit limitation remains:

`ENTRY_FEE_SETTLED_AT_REALIZATION`

OPEN still does not mutate settled cash.

## Not implemented in A.3

A.3 does not:

- calculate proposed execution price,
- calculate slippage,
- calculate FX,
- assume `USDT = USD`,
- read the Phase 11 ledger directly,
- modify PaperBroker,
- modify REALISTIC_V2 runtime,
- add a feature flag,
- create Phase 12 startup metadata,
- persist reservations,
- implement margin,
- implement collateral,
- implement leverage,
- implement short financing,
- modify synthetic-short handling,
- modify state.json,
- modify execution_journal.jsonl,
- modify Phase 10 or Phase 11 persistence formats,
- modify LEGACY_V1,
- modify frozen strategy.

The next Phase 12 step will build the BTCUSDT proposed-exposure calculator from
the existing execution/slippage model and explicit `USDT -> USD -> PLN` FX
path before any runtime admission hook is enabled.
