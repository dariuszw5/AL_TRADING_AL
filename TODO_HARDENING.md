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
