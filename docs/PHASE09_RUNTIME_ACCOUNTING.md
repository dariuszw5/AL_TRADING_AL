# Phase 09 A.14 - Fail-Closed Runtime Accounting Bridge

## Purpose

A.14 adds the integration boundary between verified REALISTIC_V2 runtime
objects and the already-tested Phase 09 FX / PLN accounting kernels.

The bridge is deliberately isolated. It performs no network I/O and no
state persistence.

## MTM path

The bridge accepts:

- a REALISTIC_V2 position,
- the market snapshot for the same asset,
- an already-resolved unit FX conversion result,
- an explicit estimated exit fee in native currency.

The FX conversion must represent exactly one native-currency unit to PLN.
This prevents an arbitrary converted amount from being mistaken for an
FX rate.

Canonical paths remain:

- USD -> PLN
- EUR -> PLN
- USDT -> USD -> PLN

No implicit USDT = USD shortcut is allowed.

The bridge delegates price MTM to `PlnUnrealizedMtmKernel`.

Therefore the existing rules remain unchanged:

- LONG marks to BID,
- SHORT marks to ASK,
- exit fee is explicit and separate,
- exit slippage is not predicted,
- FX_STALE remains visible with explicit age,
- FX_UNAVAILABLE keeps native MTM but suppresses PLN fields.

## Instrument contract

Every call first resolves the A.9 instrument accounting contract.

The following remain runtime-accounting-ready with multiplier 1:

- BTCUSDT
- ETHUSDT
- SOLUSDT
- BNBUSDT
- XRPUSDT
- EURUSD
- AAPL

`GOLD_FUT_CONT` and `WTI_FUT_CONT` remain fail-closed.

The documented CME reference multipliers 100 and 1000 are not activated.

## Realized path

Realized accounting requires the complete original entry execution and
the complete exit execution.

The persisted Position alone is not enough because the realized kernel
requires exact entry/exit:

- execution price,
- bid/ask,
- slippage,
- fee.

A.14 never reconstructs a synthetic entry execution from `entry_price`.

The bridge therefore fails closed with:

`ENTRY_EXECUTION_REQUIRED`

when the original execution is unavailable.

When full executions are available, the bridge:

1. delegates native realized arithmetic to the A.7 kernel,
2. uses the injected A.6 realized-FX selection policy,
3. uses the injected A.5 immutable FX booker,
4. recalculates the final A.7 record with the selected immutable FX rate
   and path,
5. returns both the PLN accounting record and the immutable FX booking.

This preserves realized FX provider/table/effective-date evidence.

## Persistence boundary

A.14 does not persist accounting records.

Known limitation:

`ACCOUNTING_PERSISTENCE_NOT_IMPLEMENTED`

A later persistence phase requires its own approved storage design. A.14
does not start SQLite and does not modify `data/live_state`.

## Runtime boundary discovered by audit

The current REALISTIC_V2 cycle result does not provide a durable public
lookup of the complete historical entry Execution after restart.

Therefore A.14 does not pretend that realized accounting can be safely
reconstructed from Position state alone.

A.15 may wire the bridge into multi-asset orchestration where the exact
runtime objects and FX evidence are available, while retaining fail-closed
behavior where they are not.

## Preserved surfaces

A.14 does not modify:

- PaperBroker,
- RealisticPaperRuntime,
- execution journal,
- state store,
- scripts/run_paper_live.py,
- scripts/run_realistic_paper.py,
- scripts/run_realistic_smoke_fill.py,
- global config fingerprint,
- frozen strategy parameters,
- LEGACY_V1,
- existing test assertions,
- data/live_state,
- SQLite.