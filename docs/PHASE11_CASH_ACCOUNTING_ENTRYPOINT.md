# Phase 11 A.6 - Controlled Cash Accounting Entrypoint

Hard-stop approval 11A authorizes a controlled REALISTIC_V2 accounting
entrypoint that uses `phase11_cash_ledger.jsonl` as the authoritative source of
settled cash PLN.

The entrypoint is:

`scripts/run_phase11_cash_accounting_smoke.py`

It is BTCUSDT-only and PaperBroker-only.

## First start

A first start requires:

`--initial-cash-pln`

The value is persisted as the INITIAL record of
`phase11_cash_ledger.jsonl`.

## Restart

When a cash ledger already exists, `--initial-cash-pln` may be omitted.

If it is supplied on restart, it must equal the persisted initial cash.
A conflict fails closed.

If Phase 10/REALISTIC_V2 state evidence already exists in the selected
`--state-dir` but the Phase 11 cash ledger is missing, the entrypoint refuses
to create a new cash history and fails closed with:

`CASH_LEDGER_REQUIRED_FOR_EXISTING_STATE`

## Startup order

The controlled startup order is:

1. validate feature flags and explicit runtime policy;
2. construct the existing PaperBroker runtime;
3. initialize or verify the Phase 11 cash ledger;
4. create the Phase 10 realized-accounting journal view;
5. reconcile any persisted realized bookings missing cash settlement;
6. wire Phase 10 accounting with
   `cash_ledger.current_cash_pln` as the only cash resolver;
7. persist and verify Phase 10 startup metadata;
8. only then, if explicitly confirmed, allow one paper cycle.

Construction-only mode performs no market-data/FX prefetch and no paper cycle.

## OPEN semantics

On OPEN:

- settled cash is unchanged;
- no notional, margin or collateral is reserved;
- entry fee is not separately deducted;
- the cash ledger remains at the INITIAL record count;
- the returned portfolio snapshot uses the authoritative settled cash plus
  the already-defined unrealized MTM semantics.

Limitation:

`ENTRY_FEE_SETTLED_AT_REALIZATION`

## CLOSE semantics

On a successful CLOSE:

1. realized PLN accounting is calculated;
2. Phase 10 realized booking is persisted;
3. Phase 11 settled cash is changed exactly once by persisted
   `net_realized_pnl_pln`;
4. the portfolio snapshot is rebuilt from authoritative post-settlement cash.

## Crash-gap recovery

At startup, all persisted Phase 10 realized bookings are reconciled
idempotently into the cash ledger.

This recovers the case where a process terminated after realized booking
persistence but before cash settlement persistence.

## Safety

The entrypoint requires:

- explicit `--state-dir`,
- all four REALISTIC_V2 / FX / PLN feature flags,
- explicit Phase 10 runtime-policy values,
- explicit confirmation before `--run-cycle`.

It sends zero real exchange orders.

It does not modify:

- `state.json` format,
- `execution_journal.jsonl` format,
- Phase 10 startup metadata format,
- Phase 10 realized-accounting format,
- PaperBroker,
- execution semantics,
- frozen strategy,
- existing assertions,
- `data/live_state`,
- public all-asset runner,
- SQLite.
