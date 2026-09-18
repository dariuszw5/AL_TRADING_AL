# Phase 11 A.4 - Authoritative Settled Cash PLN Ledger

Hard-stop approval 11A authorizes an append-only
`phase11_cash_ledger.jsonl` for the controlled REALISTIC_V2 accounting path.

A.4 implements the persistence kernel only. Runtime/entrypoint wiring follows
in a later Phase 11 step under the same approved hard-stop scope.

## Authoritative cash semantics

The ledger represents **settled cash PLN** only.

It is not:

- buying power,
- free margin,
- collateral,
- reserved notional,
- leverage capacity,
- permission to open a new position.

Negative settled cash is allowed as an accounting state.

## Initialization

The first start requires explicit `initial_cash_pln`.

If the ledger already exists, restart reads and verifies it. A caller may omit
`initial_cash_pln` on restart. If a value is supplied, it must equal the
persisted initial cash exactly as a Decimal value.

Conflicting initial cash fails closed.

## OPEN semantics

OPEN does not mutate this ledger.

OPEN does not:

- reserve or subtract notional,
- reserve margin or collateral,
- subtract entry fee separately.

This is deliberate and is recorded with the limitation:

`ENTRY_FEE_SETTLED_AT_REALIZATION`

The limitation means the entry fee is economically settled into this
accounting cash balance only when the position is realized.

## CLOSE semantics

CLOSE settlement uses the already-persisted, integrity-verified Phase 10
realized accounting booking.

The cash delta is exactly:

`net_realized_pnl_pln`

from that persisted booking.

Because the Phase 09 realized kernel already deducts entry fee plus exit fee
exactly once inside `net_realized_pnl_pln`, the cash ledger does not deduct
either fee again.

Spread and slippage remain attribution/reporting and are not deducted again.

## Integrity

Every cash record contains:

- schema,
- record type,
- zero-based sequence,
- UTC recorded timestamp,
- previous record hash,
- initial cash or settlement cash-before,
- cash delta,
- cash-after,
- realized booking key when applicable,
- exit execution ID when applicable,
- source realized record hash,
- source execution config hash,
- source global config hash,
- explicit limitations,
- canonical SHA256 record hash.

The previous-record hash makes the ledger a hash chain.

Every read verifies sequence, chain, hashes, balance invariants, unique
realized booking keys and unique exit execution IDs.

Append uses OS append mode plus `fsync`, then re-reads and verifies the complete
ledger.

## Idempotency

The same persisted realized booking can be settled repeatedly across restart
without appending a second record.

A conflicting reuse of a booking identity or exit execution fails closed.

## Missing ledger

After a `Phase11CashLedger` instance has initialized successfully, deletion of
its file fails closed.

The Phase 11 controlled entrypoint will additionally distinguish first start
from restart using state-directory evidence so a missing ledger is not silently
re-created after prior runtime state already exists.

## Explicit non-goals

A.4 does not modify:

- PaperBroker,
- execution semantics,
- state.json,
- execution_journal.jsonl,
- Phase 10 startup metadata,
- Phase 10 realized accounting journal,
- frozen strategy,
- existing assertions,
- data/live_state,
- all-asset public runner,
- SQLite.

A.4 does not implement buying power, margin, collateral, short financing,
capital reservation or persistent unrealized MTM.
