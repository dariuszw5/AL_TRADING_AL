# AL Trading Agent — autonomous cross-market paper research

## Connected market classes

The autonomous TOP 10 is no longer selected from a Binance-dominated pool.

It compares fresh candidates from:

- CRYPTO — dynamically discovered liquid Binance USDT markets,
- EQUITIES — liquid US shares from the connected Yahoo research universe,
- ETFs — broad-market and sector ETFs,
- FOREX — major FX references,
- INDICES — major US index references,
- COMMODITIES — continuous futures references for gold, WTI, silver, copper, gas and Brent.

Only markets with sufficiently fresh data are considered. Closed/stale classes are
not artificially forced into the ranking.

## Anti-dominance selection

The scanner:
1. scores candidates inside each market class,
2. normalizes ranking inside that class,
3. takes the strongest fresh candidate from every active class,
4. fills remaining TOP-10 slots by cross-market score,
5. normally allows at most 3 candidates from one class.

If too few classes are currently open/fresh, the cap can be exceeded to avoid
returning an artificially short list. On a weekend, for example, crypto may
legitimately dominate because other markets are closed.

## What runs automatically

- discovers active Binance USDT markets from real provider data,
- evaluates a curated connected universe of equities/ETFs/FX/indices/commodities,
- fetches 600 closed 1m candles for model candidates,
- rejects stale market data,
- evaluates trend / mean-reversion / breakout strategies,
- uses temporally separated training/validation,
- compares current features and macro tags with resolved historical experiences,
- ranks the class-balanced top 10,
- runs an isolated long-only AI paper account,
- polls official FED and ECB release feeds,
- stores market-universe, selected-candle, macro, system and experience logs,
- exposes research state through FastAPI,
- never places real exchange orders.

## Cloud process

Railway/Docker starts:

python -m scripts.run_cloud

That process starts FastAPI and a background AutonomousResearchAgent.
Use a persistent volume mounted at /data.

## Environment

AL_TRADING_TOP_N=10
AL_TRADING_CLASS_CAP=3
AL_TRADING_CRYPTO_PRESELECT=18
AL_TRADING_SCAN_SECONDS=600
AL_TRADING_MACRO_SECONDS=600
AL_TRADING_PAPER_SECONDS=60
AL_TRADING_MIN_QUOTE_VOLUME_USDT=10000000
AL_TRADING_DATA_DIR=/data

## Data retention

- market-universe snapshots: 14 days
- selected closed candles: 30 days
- macro events: 90 days
- resolved learning experiences: 120 days
- system events: 30 days

## Important limitation

TOP 10 means the strongest candidates according to the implemented research
model and validation; it is not a guarantee of profit.

The connected non-crypto universe is intentionally a liquid research basket,
not every listed instrument in the world. Full exchange-wide equities/futures/FX
coverage requires an additional instrument-universe provider. The selection
architecture is now class-balanced so such providers can be added without
letting one class dominate.
