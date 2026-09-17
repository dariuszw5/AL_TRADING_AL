# Phase 10 A.10 - Journal-backed Entry Execution Recovery

Hard-stop approval:

The existing append-only `execution_journal.jsonl` may be used as a
durable, read-only source of the complete entry `Execution` for realized
PLN accounting after restart.

The approval explicitly excludes changes to:

- execution-journal format,
- PaperBroker,
- execution semantics,
- frozen strategy parameters,
- existing assertions,
- existing live_state,
- SQLite.

## Why this is possible without a new database

`RealisticExecutionJournal` already persists the complete committed
`BrokerResult`.

A committed filled ENTRY result therefore already contains the original
full `Execution`, including the information that must not be reconstructed
from `Position.entry_price`:

- execution id,
- execution price,
- bid / ask,
- spread,
- slippage,
- fee,
- provider timestamp,
- execution timestamp,
- execution quality,
- paper mode,
- execution config hash.

A.10 reads that already-existing evidence.

It does not alter the journal schema and does not append accounting data
to the journal.

## Exact-match recovery

`JournalEntryExecutionResolver` returns an execution only when all of the
following are true:

- `Position.entry_execution_id` exactly matches the requested execution id,
- the committed result is `FILLED`,
- the order intent is `ENTRY`,
- order asset, execution asset and Position asset all match,
- exactly one matching execution exists.

Missing evidence returns `None`.

Contradictory or duplicate matching evidence raises and therefore leaves
accounting fail-closed.

## Runtime behavior

`JournalBackedPhase09AccountingRuntime` preserves the Phase 09 behavior:

1. use the in-memory entry Execution cache first,
2. consult the journal only when that exact cache entry is absent,
3. inject the recovered execution only for the realized booking call,
4. remove the temporary in-memory recovered value afterwards.

If the journal cannot provide an exact entry execution, the existing
`ENTRY_EXECUTION_REQUIRED` behavior remains.

## Production wiring

Phase 10 production startup uses the journal-backed runtime only when the
PaperBroker already exposes an execution journal.

If no execution journal exists, the runtime remains fail-closed exactly as
before.

## Persistence boundary

A.10 does not implement accounting-record persistence.

`ACCOUNTING_PERSISTENCE_NOT_IMPLEMENTED` therefore remains a known
limitation after a successful recovered realized booking.

Startup metadata persistence also remains unresolved.

## Tests

A.10 includes deterministic tests proving:

- exact resolver matching,
- fail-closed handling of invalid evidence,
- duplicate rejection,
- runtime realized booking from a recovered entry execution,
- fail-closed behavior when the entry is absent,
- complete entry Execution recovery from a newly instantiated
  `RealisticExecutionJournal` reading the same append-only file.

A later live smoke may verify:

`OPEN -> process exit -> restart -> CLOSE -> realized PLN success`

using only temporary state and PaperBroker.
