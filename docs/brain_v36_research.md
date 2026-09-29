# Brain v3.6 — independent, RESEARCH_ONLY challenger (milestone 1)

New code lives only under src/research/brain_v36/, with a separate
scripts/run_brain_v36_research.py entry point. It does **not** touch
AIPaperManager, risk controls, real orders, state stores or Flutter.

For each symbol, direction and strategy, fit a nearest-neighbor model
**only on past completed signals of that same strategy/direction**.
Expanding chronological folds are TRAIN → embargo → VALIDATION →
embargo → TEST. Each target label exits before its own block ends.
Admission is decided on VALIDATION alone and frozen before TEST.
The TEST block is not used for parameter choice. The sample strategy
definitions initially match v3.5; testing new signals is a later milestone.

The entry proxy is next consecutive minute's OPEN after signal CLOSE.
Stop-loss is first if OHLC stop and take are both touched. If a session
gap occurs while a position is open, its result is censored, not filled
at a fictional price. Candles with old or missing minutes are not
forward-filled; last forming candle can be excluded with as_of_ms.

Cost is calculated as 2 × commission per side + full round-trip spread
+ 2 × per-side slippage, applied to midpoint/reference outcomes.
Provide calibrated cost profiles **per asset type or symbol**.
The example config is ONLY the old v3.5 crypto assumption (0.18%
round trip), with zero spread explicitly labeled as not measured. It is
not evidence of an executable crypto, FX, ETF or stock cost.
No profile for another asset class is silently substituted.
Indices and FX spot references/continuous futures are tagged reference_only.

Data must be historical, frozen 1m JSON/CSV from real providers. The
script never downloads data or changes live files. Reports are written
only under diagnostics/.

Run with Windows PowerShell in the project root:

    python -m pytest -q tests/test_brain_v36_research.py
    python -m scripts.run_brain_v36_research --input BTCUSDT=data/backtest/BTCUSDT_1m_5000.json --costs config/brain_v36_costs.example.json --horizons 15 30 60

The first report is a research baseline, NOT a production candidate or
evidence of profitability. Compare frozen v3.5 on the *same* candles,
costs, horizon, execution semantics and non-overlapping folds before
interpreting any advantage. Do not repeatedly tune on TEST.


## Milestone 3: unfiltered validation diagnostics

Both filtered and unfiltered observations use the exact same risk plan,
closed-candle signal rules, next-open entry, conservative OHLC exits and
cost profile. The unfiltered series accepts raw strategy signals whenever
the previous counterfactual position has closed; the model-filtered
series separately applies k-NN prediction and uncertainty rejection.

The CSV adds raw_validation_signals, raw_validation_trades,
raw_validation_expectancy, raw_validation_profit_factor and
raw_validation_max_drawdown alongside the original model-filtered funnel.
Raw observations are **VALIDATION ONLY**: they are never input to the
admission decision or a means to open TEST for an unadmitted variant.
Their independent non-overlap schedule means trade counts/expectancies
are descriptive rather than a matched-pairs uplift estimate. Across
expanding folds, validation windows overlap and summed raw signals are
not independent. Count unique windows/dates before inferring sample size.

No v3.5 production deployment, live-state migration, API or real orders
are performed by these modules. Performance is research counterfactual
and does not imply a realizable trading edge.


### Safe iterative invocation (keeps TEST unopened)

    python -m scripts.run_brain_v36_research --input BTCUSDT=data/backtest/BTCUSDT_1m_5000.json --costs config/brain_v36_costs.example.json --initial-train 1500 --validation-size 1200 --test-size 400 --horizons 15 30 60 --validation-only

This adds evaluate_test=false to the JSON and test_status=SEALED_VALIDATION_ONLY
for any admitted variant. The script does not call the TEST evaluator at all,
even if the model passes VALIDATION. Run a separate, pre-registered final
holdout ONLY after fixing the protocol/model without consulting TEST outcomes.


## Milestone 5: interval-aware offline research

The original v3.5-style 1m baseline is preserved as the default.
For 5m candle files, explicitly set `--bar-minutes 5`. All risk plan
horizons remain **wall-clock minutes**: 15m -> 3 bars, 30m -> 6
bars, 60m -> 12 bars. Next-open execution, intra-bar stops, forming
candle detection, gap checks, chronological embargoes, split guards and
label closure use the declared candle duration.

Example using an independently frozen 5m dataset (only when such a
file actually exists):

    python -m scripts.run_brain_v36_research --input BTCUSDT=data/research/BTCUSDT_5m.json --costs config/brain_v36_costs.example.json --bar-minutes 5 --initial-train 600 --validation-size 400 --test-size 200 --horizons 15 30 60 --validation-only

The feature lookback remains 20 **bars**, not 20 minutes: 1m and 5m
signals are distinct model specifications and results must not be
treated as matched signals. A user-supplied 1m series incorrectly
declared as 5m raises an explicit error instead of silently yielding
zero signals. Actual discontinuities across market sessions/weekends
are never filled; open outcomes crossing a missing bar are censored
rather than pretending there was an executable quote. This implies
limited evidence from datasets with many discontinuities. Do not
confuse OHLC references with executable bid/ask spreads.

A validated dataset and an explicit per-instrument cost profile are
required before an instrument can join multi-asset experiments.
Existing 5,000-candle BTC benchmark data were not rewritten.


## Stage 6: ALL supported markets + dynamic current scanner universe

The former BTCUSDT 1m benchmark is a regression reference only. The PRIMARY
catalog-wide pipeline dynamically builds a deduplicated universe from the
project's SUPPORTED_ASSETS, RESEARCH_ASSETS, the fixed cross-market project
catalog (compatibility with older local source trees), plus symbols appearing
in the current read-only /api/ai ranking and /api/research opportunities.
Dynamic crypto membership is a frozen snapshot of the CURRENT scanner output,
not a claim to cover every USDT product on Binance or symbols not discovered
at capture time. A failed live-universe read explicitly marks the manifest
as DYNAMIC_DISCOVERY_FAILED_PARTIAL_UNIVERSE.

Instrument coverage includes crypto, equity, ETF, FX reference, index
reference and continuous commodity futures proxy. The executable instrument
is NOT assumed to be identical to a Yahoo index or synthetic reference.

Fetch each asset's real OHLC from its provider (Binance history 1m/5m,
Yahoo chart 1m/5m, respecting Yahoo's limited history), timestamp all
downloads against a single capture cutoff, discard forming candles and save
immutable JSON files with SHA256 and a manifest. No data are invented,
forward-filled or downloaded into data/live. A missing feed, inadequate
history, checksum failure, misclassified instrument or unsupported time
interval is an explicit coverage status, never a successful backtest.

Use the SAME bar interval (typically 5m), wall-clock horizons 15/30/60m,
and fixed split sizes per asset. The final 160 bars (configurable) are
reserved as a NEW OUTER holdout that is NEVER passed into walk_forward.
Internal rolling TEST placeholders inside the development window are also
not evaluated; expanding training/validation may later traverse those
historical development placeholders, but cannot encounter outer holdout.
No across-asset shared k-NN fit occurs at this stage. Model results stay
grouped per symbol/strategy/side/fold/horizon.

For first-run PIPELINE testing only, the sample config
config/brain_v36_costs.multiasset_SCENARIO.json explicitly supplies a
DIFFERENT unverified assumed commission/spread/slippage profile for every
asset class. These are NOT measured execution costs and the resulting
net metrics are hypothetical. Calibrate against actual executable
bid/ask/provider/broker/venue quotes before making profitability claims.
The runner fails closed with a visible status when an instrument has no
explicit cost profile.

### Single-command READ-ONLY full catalog run

    python -m pytest -q tests/test_brain_v36_research.py tests/test_brain_v36_cost_audit.py tests/test_brain_v36_interval.py tests/test_brain_v36_all_assets.py
    python -m scripts.run_brain_v36_all_assets --api-base-url https://34-45-151-160.sslip.io --costs config/brain_v36_costs.multiasset_SCENARIO.json --bar-minutes 5 --limit 3000 --horizons 15 30 60
    python -m pytest -q --ignore=diagnostics

All real screenshots/quotes/data are evaluated only on the user's machine
when the explicit read-only command runs; unit tests use synthetic candles
ONLY to test code behavior for every static/dynamic asset symbol at 1m/5m,
every direction and every horizon. These unit tests are NOT real-data
performance outcomes.

Inspect multiasset_coverage_*.csv before interpreting multiasset_v36_*.csv:
VALIDATION_ONLY_COMPLETED, PARTIAL_HORIZON_COVERAGE, DATA_UNAVAILABLE,
SKIPPED_INSUFFICIENT_OR_INVALID_HISTORY, SKIPPED_COST_OR_DATA_ERROR.
The manifest records every instrument, including failures.
Do NOT pool overlapping fold rows as independent trades or claim a
class-wide edge from a single asset. The current virtual PLN production
account, v3.5 Brain, Supervisor and cloud VM are not accessed or changed.
