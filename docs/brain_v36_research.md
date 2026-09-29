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
