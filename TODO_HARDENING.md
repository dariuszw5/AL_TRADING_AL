# TODO HARDENING

## Provider hardening

- [ ] Evaluate an official provider for Yahoo-backed FX, metals,
  energy and equities so `query1.finance.yahoo.com/v8/finance/chart`
  can be replaced without changing trading core.
- [ ] Establish reliable delay metadata for GOLD_FUT_CONT,
  WTI_FUT_CONT, EURUSD and AAPL.
- [ ] Establish provider-sourced tick-size and quantity/trading rules
  for non-Binance instruments.
- [ ] Evaluate streaming capability separately; Phase 06 intentionally
  did not add a WebSocket dependency.

## Phase 09 follow-up hardening

- [ ] Wire production FX resolvers into an approved REALISTIC_V2 runtime
  construction path before promoting FX_QUALITY.
- [ ] Wire explicit estimated-exit-fee and cash-PLN resolvers for the
  Phase 09 accounting runtime; do not infer either value.
- [ ] Persist immutable accounting records only after a separately
  approved persistence design. JSON-to-SQLite remains a HARD STOP item.
- [ ] Add durable lookup of the complete entry Execution before claiming
  restart-safe realized accounting. Do not reconstruct it from
  Position.entry_price.
- [ ] Resolve the runtime contract multipliers for GOLD_FUT_CONT and
  WTI_FUT_CONT before unblocking their accounting contracts.
- [ ] Model or explicitly quantify FX conversion cost if it becomes
  material to PLN performance reporting.
- [ ] Keep Yahoo FX / market-data use labelled UNOFFICIAL /
  DEGRADED_BY_DESIGN until an approved official source replaces it.
- [ ] Re-run PAPER_READINESS only after production wiring is verified;
  component-level tests alone must not promote runtime readiness.
<!-- PHASE10_CLOSURE_START -->
## After Phase 10 closure

- [ ] Define and approve cash / balance ledger semantics.
- [ ] Decide whether unrealized MTM snapshots require persistence.
- [ ] Decide whether realized-accounting JSONL needs multi-process locking or a
      strict single-writer contract.
- [ ] Refine the generic `ACCOUNTING_PERSISTENCE_NOT_IMPLEMENTED` limitation
      taxonomy without weakening protected contracts.
- [ ] Formally approve permanent production FX/runtime policy values.
- [ ] Measure persisted accounting timing for the all-asset set before
      enabling an all-asset persisted runner.
- [ ] Keep Yahoo FX unofficial / degraded by design.
- [ ] Keep FX conversion-cost modelling as explicit debt.
- [ ] Keep GOLD_FUT_CONT and WTI_FUT_CONT blocked until multiplier/rollover
      semantics receive a separate HARD STOP.
- [ ] Do not start SQLite migration without its dedicated HARD STOP.
- [ ] Do not silently replace the existing public/preflight entrypoint with
      the controlled Phase 10 smoke entrypoint.
<!-- PHASE10_CLOSURE_END -->
