# Phase 11 Closure Report — Authoritative Settled Cash PLN

Phase 11 branch:

`phase-11-accounting-readiness-preflight`

Closure base:

`bfe928f Phase 11: add controlled cash accounting entrypoint`

Phase 11 introduced an authoritative append-only settled-cash PLN ledger for
the controlled REALISTIC_V2 accounting path, wired it into the Phase 10
accounting runtime, added restart reconciliation for the realized-booking /
cash-settlement crash gap, and verified the complete flow with controlled live
PaperBroker tests.

No real exchange order path was enabled.

## VERIFIED

- `phase11_cash_ledger.jsonl` is append-only, canonical-JSON hashed, fsynced,
  hash-chained and integrity-verified.
- First start requires explicit `initial_cash_pln`.
- Restart reads the existing cash ledger and can omit `initial_cash_pln`.
- Conflicting restart initial cash fails closed.
- Existing runtime state without a Phase 11 cash ledger fails closed instead
  of silently creating a new cash history.
- OPEN does not reserve or subtract notional, margin or collateral.
- OPEN does not subtract entry fee separately from settled cash.
- Settled cash changes on CLOSE exactly once by persisted
  `net_realized_pnl_pln`.
- Entry and exit fees remain deducted exactly once through the Phase 09
  realized accounting kernel.
- Spread and slippage remain attribution/reporting and are not deducted again.
- Negative settled cash is permitted as an accounting state.
- The cash ledger is not buying power, margin, collateral or permission to
  enter a trade.
- Phase 11 uses only `cash_ledger.current_cash_pln` as the accounting cash
  resolver.
- A returned portfolio snapshot is rebuilt after CLOSE settlement so returned
  cash/equity is not stale.
- Persisted Phase 10 realized bookings are reconciled idempotently into the
  cash ledger at startup.
- A live crash gap was intentionally reproduced: realized booking persisted,
  cash settlement absent, paper position already closed.
- The next Phase 11 construction-only restart appended exactly one missing cash
  settlement without starting a new paper cycle.
- Cross-journal linkage between execution, realized booking and cash settlement
  was verified.
- Temporary live-smoke state was deleted after controlled tests.
- Real exchange orders sent in controlled Phase 11 smokes: `0`.

## FIXED

1. No authoritative settled-cash source existed for REALISTIC_V2 accounting.
2. Portfolio snapshots depended on optional caller-supplied cash.
3. Restart had no durable cash history.
4. Realized PnL persistence and settled cash persistence had a crash window
   with no recovery contract.
5. CLOSE could return a portfolio snapshot calculated before a future cash
   settlement layer; Phase 11 rebuilds it after authoritative cash settlement.
6. A controlled Phase 11 cash-accounting entrypoint did not exist.

## NOT REPRODUCED / NOT OBSERVED

No cycle-budget violation was reproduced in the controlled BTCUSDT Phase 11
live smokes.

A.7:
- OPEN wall time: `3.1896969 s`
- restart CLOSE wall time: `3.2430303 s`

A.8:
- OPEN wall time: `5.3163488 s`
- Phase 10 CLOSE that created the intentional cash gap: `3.1841992 s`
- construction-only startup reconciliation: `0.2912694 s`

All measured values were below the 10-second warning threshold and below the
20-second cycle budget.

This evidence is BTCUSDT-only and must not be generalized to an all-asset
production cycle.

## FILES / MAJOR PHASE 11 IMPLEMENTATION

Key Phase 11 implementation files:

- `src/accounting/cash_ledger.py`
- `src/accounting/cash_runtime.py`
- `scripts/run_phase11_cash_accounting_smoke.py`
- `tests/test_phase11_cash_ledger.py`
- `tests/test_phase11_cash_runtime.py`
- `tests/test_phase11_cash_accounting_entrypoint.py`
- `docs/PHASE11_CASH_LEDGER.md`
- `docs/PHASE11_CASH_RUNTIME_WIRING.md`
- `docs/PHASE11_CASH_ACCOUNTING_ENTRYPOINT.md`

The public all-asset runner was not changed.

`state.json`, `execution_journal.jsonl`,
`phase10_startup_metadata.jsonl`, and
`phase10_realized_accounting.jsonl` formats were not changed.

## TESTS

Latest implementation result before closure:

- A.4 new cash-ledger tests: `10 passed`
- A.4 targeted cash/realized/portfolio tests: `93 passed`
- A.5 new cash-runtime tests: `6 passed`
- A.5 targeted cash/realized/runtime tests: `68 passed`
- A.6 new entrypoint tests: `10 passed`
- A.6 targeted entrypoint/runtime/persistence tests: `49 passed`
- A.6 full offline regression: `826 passed`
- restored user `tests/test_agent_config.py`: `8 passed`
- A.7 offline live-smoke precheck: `34 passed`
- A.8 offline live-smoke precheck: `42 passed`

A.7 and A.8 modified no repository files.

## BTC LEGACY_V1 REGRESSION

The exact frozen benchmark after A.6 remained:

- final balance: `1014.8392976799995`
- trades: `13`
- wins: `7`
- losses: `6`
- win rate: `53.84615384615385`
- total profit: `14.839297679999504`
- max drawdown: `18.485012400000187`
- profit factor: `1.692128777090018`
- expectancy: `1.1414844369230388`

No frozen strategy parameter changed.

## REALISTIC_V2 LIVE RESULT

### A.7 normal persisted cash roundtrip

Initial settled cash:

`1000 PLN`

OPEN:
- cash mutation: none
- separate entry-fee cash deduction: none
- one open BTCUSDT paper position
- cash ledger records: `1`

Restart CLOSE:
- realized PLN persistence: PASS
- cash settlement persistence: PASS
- cash delta:
  `-0.02466552915011231497149716816 PLN`
- final settled cash:
  `999.9753344708498876850285028 PLN`
- cash ledger records: `2`
- realized records: `1`
- startup metadata records: `2`
- final positions: `0`
- unresolved execution-journal records: `0`
- cross-journal linkage: PASS
- real exchange orders: `0`

### A.8 live crash-gap recovery

A deliberate intermediate state was produced:

- realized booking records: `1`
- cash records: `1` (INITIAL only)
- settled cash remained `1000 PLN`
- paper position already closed

Persisted realized PLN:

`-0.01088051268808911495720737501 PLN`

Construction-only Phase 11 restart:

- paper cycle: NOT RUN
- network accounting prefetch: NOT RUN
- startup reconciliation inspected one realized booking
- exactly one missing cash settlement was appended
- final cash:
  `999.9891194873119108850427926 PLN`
- final cash records: `2`
- final realized records: `1`
- final startup metadata records: `3`
- final positions: `0`
- final unresolved journal records: `0`
- real exchange orders: `0`

## PAPER_READINESS

No formal asset readiness upgrade is claimed at Phase 11 closure.

BTCUSDT now has a verified controlled persisted settled-cash PLN path with:

- restart-safe initial cash,
- realized settlement,
- post-settlement portfolio cash refresh,
- crash-gap reconciliation.

However this remains a controlled BTCUSDT-only path.

The following production semantics remain unresolved:

- buying power,
- capital reservation,
- margin,
- collateral,
- short financing,
- persistent unrealized MTM,
- all-asset persisted cash orchestration.

Therefore all assets remain `NOT_READY` in the phase-level readiness table.

## ROLLBACK

Phase 11 is additive.

Rollback can be performed by reverting the Phase 11 commits. It does not
require migration of existing:

- `state.json`,
- `execution_journal.jsonl`,
- Phase 10 startup metadata,
- Phase 10 realized accounting records.

`phase11_cash_ledger.jsonl` is Phase 11-specific persistent state and must not
be silently deleted in a real persistent state directory. Any future rollback
against non-temporary Phase 11 state must preserve or explicitly archive that
ledger.

No existing `data/live_state` content was modified.

## ZAŁOŻENIA SPECYFIKACJI, KTÓRE OKAZAŁY SIĘ NIEPRAWDZIWE

1. A cash ledger did not require SQLite for the verified Phase 11 scope.
   Append-only JSONL with hash chaining, fsync and idempotency was sufficient.
2. Settled cash did not require reconstruction from execution state or
   position notional; the persisted realized PLN booking is sufficient for
   realized settlement.
3. A crash between realized persistence and cash persistence does not require
   replaying the broker CLOSE. Startup reconciliation can recover from the
   already-persisted realized booking.

## ZARZUTY Z PROMPTU, KTÓRE NIE POTWIERDZIŁY SIĘ TESTEM

The concern that restart reconciliation might require a new paper execution
was not confirmed. A.8 recovered the missing cash settlement in
construction-only mode with no paper cycle and no network accounting prefetch.

No controlled BTC Phase 11 cycle-budget overrun was reproduced.

## DŁUG TECHNICZNY DODANY ŚWIADOMIE W TEJ FAZIE

1. `ENTRY_FEE_SETTLED_AT_REALIZATION` is an explicit accounting limitation.
   Entry fee does not reduce settled cash until position realization.
2. The cash ledger is not buying power and does not reserve capital.
3. Margin, collateral, leverage and short-financing semantics are not
   implemented.
4. Persistent unrealized MTM is not implemented.
5. The controlled Phase 11 entrypoint is BTCUSDT-only.
6. Multi-process concurrent append arbitration for the cash ledger is not
   implemented; the verified contract is sequential single-writer/restart.
7. Phase 10's generic `ACCOUNTING_PERSISTENCE_NOT_IMPLEMENTED` limitation may
   still appear in in-memory accounting results even though realized and cash
   persistence now exist externally.
8. The verification values `7200 / 7 / 4 / 3 / 20` are not automatically
   permanent production policy defaults.
9. Yahoo FX remains unofficial / degraded by design.
10. FX conversion cost remains unmodelled.
11. GOLD_FUT_CONT and WTI_FUT_CONT remain accounting-blocked.

## WPŁYW NA CZAS TRWANIA CYKLU

Controlled Phase 11 BTC live timings:

- A.7 OPEN: `3.1896969 s`
- A.7 CLOSE: `3.2430303 s`
- A.8 OPEN: `5.3163488 s`
- A.8 gap-producing CLOSE: `3.1841992 s`
- A.8 construction-only reconciliation: `0.2912694 s`

All observed values remained below the 10-second warning threshold and the
20-second budget.

All-asset persisted cash timing remains unmeasured.

## ZMIANY W PAPER_READINESS PER ASSET

- BTCUSDT: no formal readiness upgrade; controlled persistent cash and restart
  recovery verified.
- ETHUSDT: no formal readiness change.
- SOLUSDT: no formal readiness change.
- BNBUSDT: no formal readiness change.
- XRPUSDT: no formal readiness change.
- EURUSD: no formal readiness change.
- AAPL: no formal readiness change.
- GOLD_FUT_CONT: no formal readiness change; accounting remains blocked.
- WTI_FUT_CONT: no formal readiness change; accounting remains blocked.

Phase-level status remains `NOT_READY` for every asset.

## CZY WYMAGANY JEST HARD STOP PRZED NASTĘPNĄ FAZĄ

**YES** before any next phase that changes capital or production semantics,
including:

- buying power,
- capital reservation,
- margin,
- collateral,
- leverage,
- short financing,
- persistent unrealized MTM,
- enabling the Phase 11 cash path as the normal all-asset production runner,
- multi-process persistence locking,
- SQLite migration,
- GOLD/WTI multiplier or rollover activation.

A documentation-only push/merge of the completed Phase 11 branch does not
require another accounting HARD STOP.
