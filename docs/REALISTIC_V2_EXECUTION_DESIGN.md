# REALISTIC_V2 EXECUTION DESIGN

Date: 2026-09-16
Status: DESIGN ONLY — IMPLEMENTATION REQUIRES HARD STOP APPROVAL

## 1. Scope

This document defines the intended architecture for REALISTIC_V2.

No execution semantics are changed by this document.

The implementation must preserve:

`ExecutionProfile.LEGACY_V1`

as the frozen historical profile used only for backtest/regression.

It must introduce:

`ExecutionProfile.REALISTIC_V2`

as a separate profile for future paper execution and realistic
benchmarking.

Strategy thresholds are not changed.

Strategy parameters are not optimized in Phase 08.

## 2. Core flow

The execution pipeline is explicitly separated:

SIGNAL
  -> ORDER
  -> EXECUTION
  -> POSITION

A strategy signal is not itself a fill.

### SIGNAL

Contains only strategy intent:
- BUY
- SELL
- HOLD

The strategy must not know bid/ask fill mechanics.

### ORDER

Represents an execution request.

Minimum fields:

- order_id
- client_order_id
- asset_id
- requested_side
- quantity
- intent
- created_at
- execution_profile
- paper_mode
- signal_reference
- requested_exit_reason if applicable
- status
- rejection_reason

Initial implementation requires MARKET-style paper orders only.

No matching engine.
No OMS.
No partial-fill simulation in the initial REALISTIC_V2.

### EXECUTION

Represents what actually happened.

Minimum fields:

- execution_id
- order_id
- asset_id
- side
- quantity
- reference_price
- execution_price
- bid
- ask
- spread
- slippage
- fee
- provider_timestamp
- execution_timestamp
- data_quality
- execution_quality
- session_quality
- paper_mode
- short_label
- trigger_reason
- pending_reason
- execution_reason

### POSITION

Represents the resulting open position.

Minimum fields:

- position_id
- asset_id
- side LONG / SHORT
- quantity
- entry_execution_id
- entry_price
- stop_loss
- take_profit
- opened_at
- short_mechanism
- short_financing_model
- execution_profile
- execution_quality_at_entry
- status

Position lifecycle:

OPEN
-> EXIT_PENDING when an exit is required but execution is unavailable
-> CLOSED after an actual exit execution

## 3. Broker boundary

Introduce:

`BrokerInterface`

Responsibilities:
- accept Order
- validate whether execution is allowed
- resolve executable quote
- apply execution-quality policy
- apply slippage
- create Execution
- create/update Position
- reject invalid orders with explicit reason

Introduce:

`PaperBroker`

REALISTIC_V2 implementation of BrokerInterface.

PaperBroker must consume:
- AssetRegistry
- MarketSnapshot
- MarketSessionService
- execution policy
- slippage model
- Clock

PaperBroker must not:
- calculate strategy signals
- change RSI thresholds
- modify LEGACY_V1 behavior
- invent market data silently

## 4. Execution profiles

### LEGACY_V1

Unchanged.

Properties:
- historical fill semantics remain frozen
- spread = 0
- slippage = 0
- existing legacy fee behavior remains frozen
- available only for backtest/regression
- never allowed in paper-live

No existing LEGACY_V1 assertion is modified.

### REALISTIC_V2

Separate execution path.

Properties:
- executable side of quote is used
- spread is explicit
- slippage is explicit
- market/session state is respected
- stale feed is rejected
- delayed feed policy depends on paper_mode
- short capability is checked
- STOP_GAP exists
- EXIT_PENDING exists

## 5. Entry price rules

LONG entry:

BUY -> ASK

If a real ask exists:
reference_price = ask

SHORT entry:

SELL -> BID

If a real bid exists:
reference_price = bid

Slippage is then applied adversely to the trader.

BUY:
execution_price >= reference_price

SELL:
execution_price <= reference_price

## 6. Exit price rules

LONG exit:

SELL -> BID

SHORT exit:

BUY -> ASK

This applies to:
- STOP_LOSS
- TAKE_PROFIT
- TIME_EXIT
- pending exits after reopen

## 7. Stop and take-profit triggers

For LONG:

STOP_LOSS trigger:
executable BID <= stop_loss

TAKE_PROFIT trigger:
executable BID >= take_profit

For SHORT:

STOP_LOSS trigger:
executable ASK >= stop_loss

TAKE_PROFIT trigger:
executable ASK <= take_profit

Trigger evaluation therefore uses the side at which the position could
actually be closed.

## 8. STOP_GAP

A stop price is not guaranteed as an execution price.

If a market reopens or the next executable quote is already beyond the
stop threshold:

LONG:
bid < stop_loss

SHORT:
ask > stop_loss

then:

exit_reason = STOP_GAP

and the fill occurs at the currently executable quote plus adverse
slippage.

Do not fill magically at the stop price.

## 9. TIME_EXIT and EXIT_PENDING

If TIME_EXIT becomes due while execution is possible:
close using the executable bid/ask.

If TIME_EXIT becomes due while:
- market is closed
- session quality prevents execution
- no executable quote is available

then position becomes:

EXIT_PENDING

The pending record must preserve:
- requested exit reason
- timestamp when exit became due

On the first eligible reopening snapshot:

1. check risk exits first
2. if price crossed stop -> STOP_GAP
3. otherwise execute the pending exit at current executable price

Do not fabricate an execution during the closed interval.

## 10. Market closed

New entries while the market/session is closed:

REJECTED / MARKET_CLOSED

Existing open position requiring an exit:

EXIT_PENDING

Crypto 24/7 remains governed separately by provider/data health.

## 11. Data freshness

STALE data:
reject new entry in all paper modes.

A stale quote must not be used to manufacture a fill.

DELAYED data:

`realistic_paper`
-> reject new entry

`research_paper`
-> may execute only when policy permits
-> transaction must carry DELAYED_DATA label
-> benchmark/report/dashboard must expose the label

Exit handling must fail safely and preserve EXIT_PENDING rather than
inventing a fresh price.

## 12. ExecutionQuality policy

Runtime values:

REAL_BOOK
DERIVED_SPREAD
SIMULATED_SPREAD
UNTRADEABLE

### REAL_BOOK

Use provider bid/ask.

Eligible for:
- realistic_paper
- research_paper

### DERIVED_SPREAD

Requires:
- real last
- separately measured/documented spread model

The spread must be evidence-based.

Eligible for:
- realistic_paper only after spread model validation
- research_paper

Until such validation exists, treat it as unavailable.

### SIMULATED_SPREAD

Spread comes from explicit simulation configuration.

Initial policy:

`realistic_paper`
-> reject

`research_paper`
-> allowed with mandatory SIMULATED_SPREAD label

Result must never be presented as equivalent to REAL_BOOK.

### UNTRADEABLE

Always reject new entry.

No synthetic execution price may be created.

## 13. Derived/simulated quote construction

When a permitted model uses last price:

bid = last - spread / 2
ask = last + spread / 2

The spread source and model version must be recorded.

A derived/simulated spread is never silently presented as a real book.

## 14. Slippage

REALISTIC_V2 uses an explicit SlippageModel interface.

Initial implementation design:

`FixedBpsSlippage`

Properties:
- deterministic
- adverse only
- configured explicitly
- value included in config_hash
- no randomness
- no hidden default calibrated from strategy profitability

For BUY:

execution_price =
reference_price * (1 + slippage_bps / 10000)

For SELL:

execution_price =
reference_price * (1 - slippage_bps / 10000)

The first benchmark may choose an explicit research value, but the
value is not frozen by this design document.

No strategy optimization may be performed to compensate for slippage.

## 15. Fees

REALISTIC_V2 records fees explicitly on Execution.

Existing frozen LEGACY_V1 fee behavior remains untouched.

Any new REALISTIC_V2 fee implementation must use configuration and be
included in benchmark metadata/config_hash.

## 16. Paper modes

### realistic_paper

Purpose:
highest practical paper realism supported by currently validated data.

Rules:
- LEGACY_V1 forbidden
- stale new entries rejected
- delayed new entries rejected
- SIMULATED_SPREAD rejected
- UNTRADEABLE rejected
- session restrictions active
- short capability active

### research_paper

Purpose:
research when market-data quality is below realistic-paper standard.

Rules:
- may allow delayed feed with label
- may allow SIMULATED_SPREAD with label
- stale data still rejected
- UNTRADEABLE still rejected
- synthetic short may be permitted only with explicit labels

Results from research_paper must not be merged with realistic_paper
results without quality annotations.

## 17. Short selling

Before opening SHORT:

1. AssetConfig.allow_short must be True.
2. short_mechanism must not be NONE.
3. paper mode must allow that mechanism.

If short is unsupported:

REJECTED / SHORT_NOT_SUPPORTED

### Synthetic short

If short_mechanism == SYNTHETIC:

realistic_paper:
- reject

research_paper:
- may allow
- mandatory labels:
  SYNTHETIC_SHORT
  FINANCING_NOT_MODELLED

Synthetic-short PnL must not be described as directly attainable on the
underlying spot market.

### Borrow / margin / futures / CFD

The mechanism must be explicit.

If required financing/borrow behavior is not modelled, the execution
record must expose that limitation.

No hidden synthetic short fallback exists.

## 18. BTC spot consequence

BTCUSDT market data is Binance spot reference data.

A SELL signal with no LONG position is therefore not automatically a
real BTC spot short.

REALISTIC_V2 must consult AssetConfig.

LEGACY_V1 historical SELL behavior is not changed.

## 19. Continuous futures proxies

GOLD_FUT_CONT and WTI_FUT_CONT remain continuous-futures proxies.

The existence of a Yahoo last price does not imply a directly
tradeable contract.

If ExecutionQuality is UNTRADEABLE:
reject.

Do not invent execution capability because the strategy produced a
signal.

## 20. Idempotency

Order submission uses `client_order_id`.

A repeated client_order_id must not create a second execution or
position.

The result must be safely recoverable/replayable.

No database migration is performed in Phase 08.

## 21. Feature boundary

REALISTIC_V2 is introduced behind an explicit execution-profile
selection.

Required metadata:
- execution_profile
- paper_mode
- config_hash

No silent automatic selection of LEGACY_V1 is allowed for paper-live.

## 22. Planned code surface after approval

New files expected:

- `src/execution/__init__.py`
- `src/execution/models.py`
- `src/execution/broker_interface.py`
- `src/execution/paper_broker.py`
- `src/execution/slippage.py`
- `src/execution/execution_policy.py`
- `tests/test_realistic_v2_execution.py`
- `scripts/run_realistic_v2_benchmark.py`

Potential integration files requiring careful minimal changes:

- `src/agent/agent_config.py`
- `src/agent/agent_engine.py`
- `src/backtest/backtest_runner.py`
- paper-live orchestration entry point

Files that must retain LEGACY_V1 semantics:
- legacy trading/backtest path
- frozen strategy modules
- frozen strategy parameters

The exact integration surface must be re-audited immediately before
implementation.

## 23. Test matrix after approval

Required RED-before-code contract tests:

1. BUY entry uses ASK.
2. SHORT entry uses BID.
3. LONG exit uses BID.
4. SHORT exit uses ASK.
5. allow_short=False -> SHORT_NOT_SUPPORTED.
6. SYNTHETIC short rejected in realistic_paper.
7. synthetic short in research_paper carries both mandatory labels.
8. stale entry rejected.
9. delayed entry rejected in realistic_paper.
10. delayed entry may run in research_paper only with label.
11. REAL_BOOK uses real bid/ask.
12. SIMULATED_SPREAD rejected in realistic_paper.
13. SIMULATED_SPREAD result labelled in research_paper.
14. UNTRADEABLE rejected.
15. MARKET_CLOSED rejects entry.
16. TIME_EXIT while closed -> EXIT_PENDING.
17. reopen executes pending exit.
18. LONG gap through stop -> STOP_GAP at executable BID.
19. SHORT gap through stop -> STOP_GAP at executable ASK.
20. duplicate client_order_id is idempotent.
21. LEGACY_V1 cannot be selected for paper-live.
22. LEGACY_V1 BTC golden remains unchanged.
23. REALISTIC_V2 benchmark is reported separately.
24. execution quality appears in benchmark metadata.
25. config_hash includes execution profile/slippage/paper mode.

Existing assertions are not changed to make new tests pass.

## 24. Benchmark design

LEGACY_V1 benchmark:

remains exactly the existing frozen BTC benchmark.

Expected:
no numerical change.

REALISTIC_V2 benchmark:

reported separately.

The historical frozen OHLC dataset does not contain a real order book,
therefore a historical V2 benchmark cannot honestly be labelled
REAL_BOOK.

If run on the frozen candle dataset it must use an explicitly labelled
derived/simulated execution source and record:

- EXECUTION_QUALITY
- spread configuration/model
- slippage configuration
- fee configuration
- execution_profile
- paper_mode
- config_hash

No target profitability is defined.

A lower REALISTIC_V2 PnL is not a regression by itself.

## 25. Expected benchmark impact

LEGACY_V1:
expected impact = ZERO.

REALISTIC_V2:
entry/exit prices will generally differ from legacy close/SL/TP fills.

Therefore:
- total PnL may decrease or increase
- win rate may change
- stop/take-profit ordering may change
- STOP_GAP can increase realized loss
- spread/slippage/fees can reduce expectancy

No direction or magnitude is assumed before measurement.

The strategy thresholds remain frozen during this evaluation.

## 26. Rollback

REALISTIC_V2 must be separable by execution profile.

Rollback after implementation:

1. disable REALISTIC_V2 selection
2. return benchmark/regression to LEGACY_V1
3. revert Phase 08 implementation commits if required

No migration of:
- data/live_state
- database
- frozen backtest datasets

is planned for Phase 08.

## 27. HARD STOP

This document is Part A only.

Implementation changes execution semantics.

Do not implement PaperBroker, REALISTIC_V2 fills or execution
integration until the user explicitly approves the Phase 08 HARD STOP.
