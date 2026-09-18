# Phase 10 Closure Report — REALISTIC_V2 PLN / FX Accounting Wiring

Phase 10 branch:

`phase-10-realistic-v2-accounting-wiring`

Closure base:

`e7522f5 Phase 10: persist realized accounting bookings`

This report closes the Phase 10 implementation scope. Phase 10 wired the
Phase 09 PLN / FX accounting kernel into a controlled REALISTIC_V2
PaperBroker path, added bounded production FX prefetch, persisted startup
fingerprints, recovered full entry Execution evidence after restart, and
persisted completed realized PLN bookings.

No real exchange order path was enabled.

## VERIFIED

- Production FX adapters and conversion paths are explicit and fail closed.
- BTCUSDT MTM uses `USDT -> USD -> PLN`; no silent `USDT = USD`.
- FX prefetch is parallel, bounded, and prevents overlap with a still-running
  previous FX generation.
- Phase 10 startup metadata fingerprints execution config, asset registry,
  paper mode, feature flags, and the explicit runtime policy.
- All four runtime feature flags are required before accounting wiring.
- Live BTCUSDT PaperBroker OPEN -> CLOSE works with MTM and realized PLN.
- The pre-A.10 restart gap was reproduced as `ENTRY_EXECUTION_REQUIRED`.
- The existing append-only execution journal already contained the complete
  committed entry Execution required for restart recovery.
- Journal-backed recovery succeeds across a real process restart.
- Startup metadata is persisted before paper execution, fsynced, hashed,
  and verified.
- Two process starts create two valid startup metadata records.
- Completed realized PLN accounting is persisted to
  `phase10_realized_accounting.jsonl`.
- OPEN creates zero realized booking records.
- Restart CLOSE creates exactly one realized booking record.
- Persisted entry and exit execution IDs match the actual PaperBroker fills.
- Realized persistence stores native PnL, PLN PnL, FX rate/path/evidence,
  execution config hash, global config hash, booking key, and record hash.
- Sequential retry/restart persistence is idempotent for identical bookings.
- Conflicting semantic evidence under the same booking identity fails closed.
- Tampered records fail integrity verification.
- Temporary live-smoke state was removed after every controlled live test.
- Real exchange orders sent by the controlled Phase 10 smokes: `0`.

## FIXED

1. Missing production accounting resolvers.
2. Unbounded/sequential FX-prefetch risk at the Phase 10 accounting layer.
3. Missing Phase 10 accounting runtime policy in startup fingerprinting.
4. Missing controlled accounting smoke entrypoint.
5. Missing durable recovery of full entry Execution after restart.
6. Missing startup metadata persistence.
7. Missing durable persistence of completed realized PLN bookings.

## NOT REPRODUCED / NOT OBSERVED

The feared 20-second cycle-budget overrun was not reproduced in controlled
BTCUSDT live smokes.

Observed end-to-end wall times:

- A.8 OPEN: `4.198421599925496 s`
- A.8 CLOSE: `4.312310199951753 s`
- A.11 OPEN: `3.3025825 s`
- A.11 CLOSE: `3.3376116 s`
- A.14 OPEN: `3.4737006 s`
- A.14 CLOSE: `4.5939363 s`
- A.16 OPEN: `4.1651842 s`
- A.16 CLOSE: `4.2139755 s`

Every measured controlled BTC cycle stayed below the 10-second warning
threshold and below the 20-second cycle budget.

This does not prove all-asset production timing.

## FILES / MAJOR PHASE 10 IMPLEMENTATION

Key files:

- `src/accounting/production_resolvers.py`
- `src/accounting/production_fx_scheduler.py`
- `src/accounting/production_startup.py`
- `src/accounting/journal_entry_recovery.py`
- `src/accounting/startup_metadata_store.py`
- `src/accounting/realized_persistence.py`
- `scripts/run_phase10_accounting_smoke.py`
- `scripts/run_phase10_persisted_accounting_smoke.py`

The pre-existing public `scripts/run_realistic_paper.py` remains a preflight
path. `scripts/run_paper_live.py` was not modified.

## TESTS

Latest A.15 implementation result:

- new A.15 tests: `8 passed`;
- targeted A.15 tests: `82 passed`;
- full offline regression: `800 passed`;
- restored user `tests/test_agent_config.py`: `8 passed`.

A.16 then ran a controlled live persisted restart smoke from HEAD `e7522f5`
without modifying the repository.

## BTC LEGACY_V1 REGRESSION

Exact frozen benchmark after A.15:

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

A.16 BTCUSDT persisted restart smoke:

- startup metadata records: `2`
- realized accounting records after OPEN: `0`
- realized accounting records after restart CLOSE: `1`
- entry execution ID:
  `exec-ord-rv2-BTCUSDT-020cb08ae2ce289cde8817af`
- exit execution ID:
  `exec-ord-rv2-BTCUSDT-2d30ce9a40dd342d707dd258`
- realized native PnL:
  `-0.0076996554954000013 USDT`
- realized FX rate:
  `3.7963231829999997`
- realized FX path:
  `USDT -> USD -> PLN`
- realized PLN PnL:
  `-0.02923038065830037248352348928`
- execution config hash:
  `a8c84046f4919a1c39bcaef86e926a287240b14359b9b60b7f626252f7c5e781`
- Phase 10 global config hash:
  `017d9e3ef4fba21bc17102519cf6b4994dd50ae3f53a4f05b178b5913fd9127d`
- final positions: `0`
- unresolved execution journal records: `0`
- real exchange orders: `0`

## PAPER_READINESS

No formal asset readiness upgrade is claimed at Phase 10 closure.

BTCUSDT now has a verified controlled persisted REALISTIC_V2 accounting path,
including restart recovery and realized PLN persistence, but it is still a
controlled BTC-only path rather than the normal all-asset production
orchestrator.

ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, EURUSD, and AAPL do not yet have an
equivalent persisted Phase 10 live restart verification.

GOLD_FUT_CONT and WTI_FUT_CONT remain accounting-blocked because multiplier
and rollover semantics are not activated.

Therefore all assets remain `NOT_READY` in the phase-level readiness table.

## ROLLBACK

Phase 10 persistence changes are additive. Rollback does not require migration
of the existing execution journal or state store. Reverting the Phase 10
commits removes the added accounting persistence layers while preserving the
pre-existing journal/state formats. Existing `data/live_state` was not
migrated or rewritten.

## ZAŁOŻENIA SPECYFIKACJI, KTÓRE OKAZAŁY SIĘ NIEPRAWDZIWE

1. A new database was not required to recover full entry Execution after
   restart; the existing append-only execution journal already persisted it.
2. SQLite was not required for the verified Phase 10 startup metadata and
   realized-booking persistence scope.
3. Controlled BTC accounting plus FX did not exceed the cycle budget in the
   observed smokes.

## ZARZUTY Z PROMPTU, KTÓRE NIE POTWIERDZIŁY SIĘ TESTEM

The concern that Phase 10 accounting plus FX would necessarily exceed the
20-second cycle budget was not confirmed by controlled BTC live smokes.

Other major concerns were either reproduced (`ENTRY_EXECUTION_REQUIRED`
before A.10) or verified as real implementation gaps.

## DŁUG TECHNICZNY DODANY ŚWIADOMIE W TEJ FAZIE

1. Realized-accounting JSONL idempotency is verified for sequential
   retry/restart only; multi-process append arbitration is not implemented.
2. No cash / balance ledger exists.
3. Unrealized MTM snapshots are not persisted.
4. The Phase 09 limitation `ACCOUNTING_PERSISTENCE_NOT_IMPLEMENTED` can still
   appear in in-memory accounting results even though Phase 10 persists
   completed realized bookings externally.
5. A.5 remains a non-persistent diagnostic entrypoint.
6. The values `7200 / 7 / 4 / 3 / 20` used in controlled smokes remain
   verification values / policy candidates, not automatically accepted
   permanent production defaults.
7. The controlled persisted entrypoint is BTCUSDT-only.
8. GOLD/WTI multiplier and rollover semantics remain blocked.
9. Yahoo FX remains unofficial / degraded by design.
10. FX conversion cost remains unmodelled.

## WPŁYW NA CZAS TRWANIA CYKLU

Controlled BTC persisted-accounting cycles measured about `3.30-4.59 s`.

A.16 measured:

- OPEN: `4.1651842 s`
- restart CLOSE: `4.2139755 s`

Both are below the 10-second warning threshold and the 20-second budget.

This is BTC-only evidence and must not be generalized to an all-asset
production cycle.

## ZMIANY W PAPER_READINESS PER ASSET

- BTCUSDT: no formal readiness upgrade; controlled persisted accounting path
  verified.
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

**YES** before any next phase that changes accounting semantics or persistent
production state, including:

- cash / balance ledger semantics,
- persistent unrealized accounting,
- multi-process persistence locking,
- enabling the persisted accounting path as the normal all-asset runner,
- SQLite migration,
- activating GOLD/WTI multipliers or rollover semantics.

A documentation-only push/merge of the completed Phase 10 branch does not
require another accounting HARD STOP.
