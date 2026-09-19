# AL Trading Agent — autonomous paper research

## What runs automatically

- discovers active Binance USDT markets from real provider data,
- filters low-liquidity markets,
- preselects strongest market movers/liquidity candidates,
- fetches 600 closed 1m candles for model candidates,
- evaluates trend / mean-reversion / breakout strategies,
- uses temporally separated training/validation,
- compares current features and macro tags with resolved historical experiences,
- ranks the top 10 opportunities,
- runs an isolated long-only AI paper account,
- polls official FED and ECB release feeds,
- stores market-universe, selected-candle, macro, system and experience logs,
- exposes research state through FastAPI,
- never places real exchange orders.

## Cloud process

Railway/Docker starts one process:

python -m scripts.run_cloud

That process starts:
1. FastAPI on the platform PORT.
2. A background AutonomousResearchAgent.

Use a persistent volume mounted at /data. Docker sets:
AL_TRADING_DATA_DIR=/data

## Recommended Railway settings

- source: GitHub repository
- builder: Dockerfile
- health check: /api/health
- volume mount: /data
- replicas: 1
- restart policy: on failure

Do not run multiple replicas against the same paper state because this build is a
single-writer paper research worker.

## Tunable environment variables

AL_TRADING_TOP_N=10
AL_TRADING_PRESELECT=30
AL_TRADING_SCAN_SECONDS=300
AL_TRADING_MACRO_SECONDS=600
AL_TRADING_PAPER_SECONDS=60
AL_TRADING_MIN_QUOTE_VOLUME_USDT=10000000
AL_TRADING_DATA_DIR=/data

Optional extra official/public RSS/Atom feeds:
AL_TRADING_MACRO_FEEDS=SOURCE=https://example/feed.xml,SOURCE2=https://example/feed.xml

## Data retention

- full Binance USDT universe snapshots: 14 days
- selected closed candles: 30 days
- macro events: 90 days
- resolved learning experiences: 120 days
- system events: 30 days

## Important limitation

"Top 10" means top 10 according to the implemented transparent research score
and historical validation. It is not a guarantee of future profit.

The automatic universe is all liquid Binance USDT pairs returned by the provider
plus the configured Yahoo reference markets (EURUSD, AAPL, GOLD/WTI futures
proxies). Expanding to every listed stock/FX/futures instrument requires a
licensed/supported instrument universe provider.
