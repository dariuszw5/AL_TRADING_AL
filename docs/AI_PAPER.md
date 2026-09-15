# AI paper manager (experimental)

This local module manages a separate **simulated** account. It cannot submit
exchange orders and has no keys or broker integration. It does not guarantee
profits or a maximum loss. The nine existing per-asset paper agents remain
comparison accounts; their balances are not added to the AI account.

## PLN simulation and risk boundary

The multi-market research account is denominated in PLN. Indicative FX rates
are fetched at the time of each research cycle, so a result includes both the
market move and the currency move. It is an accounting simulation, never a
bank balance or a broker account.

Every virtual long position receives a 1% stop loss and a 2% take profit. The
simulator applies 0.04% fee and 0.05% slippage on each side. Before a new
entry it enforces all of the following persistent safeguards:

- maximum estimated loss of the current entry is limited by the remaining
  daily loss budget;
- maximum position cost is 200 PLN, with at most five open positions;
- at most 400 PLN can be allocated to one asset class, reducing concentration
  in correlated markets such as crypto;
- a 20 PLN realized loss halts new entries for the current UTC day;
- a 5% marked equity drawdown latches a halt across restarts.

Open positions still receive stop/take management after a halt. Gaps, stale
data and unavailable markets can exceed modeled costs or stop levels, which is
why these are safeguards for a simulation, not a claim of capped losses.

`virtual_broker.decision_log` preserves the latest 300 decisions with the
symbol, category, strategy, score, candle close, action and reason. It is the
machine-readable trading journal for review and backtesting; it deliberately
does not record human "emotions" for an automated system.

`virtual_broker.daily_equity` retains the final complete valuation for each
UTC day. It is the source for a precise dashboard comparison against the prior
day; a missing valuation is displayed as unavailable rather than invented.

## Geopolitical historical-analogue research

`src/agent/geopolitical_analyst.py` maps public-news headlines to event tags
(for example conflict, sanctions, energy supply and financial stress) and
compares them with dated historical scenarios. It calculates an explainable
stress score by asset class, retaining the nearest historical analogues in the
API response. `src/data/geopolitical_feed.py` obtains public GDELT article
metadata at most once every 15 minutes; it uses no account, secret or broker
endpoint.

Only `ELEVATED` or `CRITICAL` historical stress blocks **new simulated
entries** for the affected class. Existing simulated positions still receive
their stop/take handling. A news-source failure is displayed as unavailable
data and never creates a synthetic geopolitical signal. The model does not
predict prices, validate facts in news articles or make real orders.

## Model and selection

The research runner scores every configured asset on each closed-candle cycle
and publishes `top_10`: the ten highest conservative historical probabilities
of a positive net result, with deterministic tie handling. The probability is
the 95% Wilson lower bound of positive outcomes in chronological validation,
not the raw percentage of wins and not a promise of profit. Only a current
technical signal inside this selected group may open a new simulated position.
It must also have at least 20 independent validation examples, positive net
score after costs and a lower-bound probability of at least 55%. A held
position leaving Top 10 is closed at the current simulated close with the
explicit `ROTATED_OUT` reason, then the next selected candidate may use its
released virtual capital. The remaining assets continue to be fetched,
analysed and ranked; they are not ignored.

## Professional validation and broker-demo boundary

Each closed virtual trade retains the historical probability used for its
entry. `probability_calibration` compares these forecasts with later paper
results, reports a Brier score and does not draw conclusions until at least 30
closed forecasts exist. It never changes parameters automatically.

The recommended broad multi-asset demo is Interactive Brokers Paper Trading.
The project exposes only a readiness status through `paper_broker`; no API
credential is read, stored or used to submit orders. `execution_enabled` is
forced to `false`, including if an environment variable asks for execution.
This boundary remains until a separately reviewed demo adapter is requested.

`src/agent/ai_manager.py` implements a small k-nearest-neighbor return regressor
in Python without another service, paid API or a heavy ML dependency. It uses
20 neighbors, past 1/5/20-minute returns and deviation from a rolling mean,
normalized by past volatility. The targets are ten-bar long-only simulated
returns, including stops, take profit, fees and slippage.

Every scan requests up to 1000 one-minute bars for each configured asset.
It removes forming bars and rejects malformed OHLC. At least 500 bars and
200 valid training examples are required. The first 70% of data forms the
training period; target windows must finish strictly before validation starts.
The remaining data is chronological validation. No random shuffle is used.
Windows spanning missing bars or session gaps are excluded from training.

Three entry rules are evaluated: trend, mean reversion and breakout. Each needs
at least five non-overlapping validation trades with positive mean net return.
Only entries whose model mean minus neighbor standard deviation is positive
are tested/selected. This spread is a conservative heuristic, not a confidence
interval or calibrated probability. The ranking uses the lower of the current
model score and validation mean. The highest eligible active signal is selected;
otherwise the manager holds cash. Parameters are fixed experiments, not tuned
or proven profitable settings. Reusing rolling validation for selection does not
constitute an independent final performance test: a longer forward paper trial
is required before drawing conclusions about predictive value.

If no full-validation strategy is eligible, paper-only exploration may test the
best current signal above a small score floor using 5% exposure. Exploration is
marked in the decision history and uses the same stops, costs and loss limits;
it cannot submit a real order.

The old frozen BTC parameters and release tag are not rewritten by this module.
The AI compares the three named strategies; it does not invent arbitrary code,
change its own risk limits, or control unrelated application functionality.

## Account, execution and safeguards

- Initial account: 1000 **simulation units**, not PLN. Assets are fractional
  price-return indices. USD and USDT are treated as equivalent for this exercise;
  FX conversion and USDT depegging are not modeled.
- Gold `XAUUSD` uses the existing `GC=F` futures price proxy; WTI uses `CL=F`.
  These are not spot gold, executable futures contracts or broker fills.
  Futures multipliers, rolls, financing, stock splits and dividends are not
  modeled. The registry currently contains one FX pair and one stock (AAPL).
- At most one long position, 20% of current balance committed, no leverage.
- Stop 1%, take profit 2%, maximum ten one-minute bars. The symbol/strategy is
  fixed until the position closes; afterwards the selector may choose another.
- Each side assumes a fee of 0.04% and slippage of 0.05%. These are test
  assumptions, not verified instrument-specific trading costs.
- A decision schedules the next not-yet-started bar's open. It is simulated
  only after that bar closes. Gap stops use the worse open; when both stop and
  take-profit occur in one bar the stop is assumed first.
- A stale/closed market (last closed bar over two minutes old) cannot receive
  new allocation. Delayed feeds may therefore be excluded. The current position
  is retained when its data is unavailable, with the problem shown in the panel.
- A cumulative realized loss of 20 units blocks new allocations for the UTC day.
  A 5% equity drawdown latches a halt across restarts. Outstanding positions
  continue receiving exit management when data becomes available. Stops and
  limits may be exceeded by gaps, latency and unavailable data.

State is atomically saved to ignored `data/live_state/ai_paper.json`. The last
300 decisions and trades are retained; failures roll back the in-memory cycle.
The model is rebuilt deterministically from fetched history, not serialized.
Only one `run_paper_live.py` process may write this account at a time.

## Running and dashboard

The existing `scripts/run_paper_live.py` runs an AI cycle after each baseline
multi-asset cycle, followed by the existing 60-second delay. Fetches use at most
three workers, each failure is reported per asset. Actual period includes
network/model time; a cycle older than 180 seconds is marked stale by `/api/ai`.

The read-only `GET /api/ai` endpoint returns decisions, rankings, per-market data
issues, account limits and trades. There are no order-execution HTTP endpoints.
The separate `user_portfolio.json` ledger accepts only manual paper deposits and
withdrawals. Realized AI profit above the 1000-unit base is swept into that
ledger as a PLN exercise result; the AI keeps its base for continued training.
This is accounting for the game and does not transfer real money.
The Flutter **AI · PORTFEL TRENINGOWY** panel is below the market chart. It shows
the separate AI account, rationale and audit history. Enable **Śledź wybór AI na
wykresie** to follow its selected symbol; manually selecting an asset disables
following. This controls the viewed chart, not the model's execution logic.
Missing or stale AI state is displayed explicitly; baseline API data remains
usable without the new endpoint.

## Verification and deployment

Run `python -m pytest tests/test_ai_manager.py` in the repository's virtual
environment. Tests cover leakage boundaries, costs, stale feeds, selection,
next-open execution, single allocation, gaps, switching, state restore and
persistence failure. Synthetic data verifies behavior, not expected profits.

In the Flutter directory run:

```text
dart format lib/main.dart lib/ai_panel.dart test/widget_test.dart
flutter analyze
flutter test test/widget_test.dart --reporter expanded
```

After verification and pushing an approved commit, update the repository **on
the VM**, restart `al-api` and `al-paper-live`, and check `/api/ai` after a full
cycle. Copying only the Flutter code does not deploy the AI on the VM.

Algorithm references (the project implements its own small Python version):
- https://sklearn.org/stable/modules/generated/sklearn.neighbors.KNeighborsRegressor.html
- https://sklearn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
