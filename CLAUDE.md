# CLAUDE.md — AL Trading Agent

## Read this first

This repository is a **real-market-data / virtual-money paper trading and research system**.

Hard rules:

- REAL market data: yes.
- REAL macro data: yes.
- REAL exchange/broker orders: **never**.
- REAL money: **never**.
- Paper/simulation balances only.
- PLN is reporting/conversion only unless explicitly documented otherwise.
- Do not add broker credentials, exchange API keys, order endpoints, or real execution code.
- Do not change the frozen BTC strategy unless the user explicitly requests it.
- Do not force-push or rewrite Git history.
- Keep changes small, testable, and compatible with Windows PowerShell + VS Code.

## Repository / environment

Repository:
- `dariuszw5/AL_TRADING_AL`
- default branch: `main`
- frozen release tag: `v1.0.0`
- frozen release commit: `33c0a5ad4d11efb4b8933c5f2e4d0d547b924fac`

Local working directory:
- `C:\Users\ddare\Desktop\Al_Trading_Al_Git`

Local tools:
- Windows PowerShell
- VS Code
- Python 3.14.x
- virtual environment: `.venv`
- Flutter: `C:\Users\ddare\develop\flutter\bin\flutter.bat`

Important: make sure Python comes from THIS repository:

```powershell
python -c "import sys; print(sys.executable)"
```

Expected path:

```text
C:\Users\ddare\Desktop\Al_Trading_Al_Git\.venv\Scripts\python.exe
```

Do not accidentally use the old:
`Al_Trading_Al_READY_DASHBOARD\.venv`.

## Current runtime model

The preferred local/cloud runtime is:

```powershell
python -m scripts.run_cloud
```

It starts:

1. FastAPI
2. the autonomous research worker

Do not start `start_api.ps1` and `python -m scripts.run_cloud` at the same time because both bind port 8000.

API:
- `http://127.0.0.1:8000`

Main health/research endpoints:
- `/api/health`
- `/api/research`
- `/api/research/opportunities`
- `/api/research/macro`
- `/api/status`
- `/api/trades`
- `/api/equity`
- `/api/market`
- `/api/assets`
- `/api/ai`

## Frozen BTC strategy

Do not modify without explicit user approval:

- symbol: BTCUSDT
- interval: 1m
- BUY RSI: 33.8
- SELL RSI: 68.5
- max position candles: 241
- RSI method: classic
- min difference: 1.0
- trading fee: 0.0004
- risk: 5%
- stop loss: 5%
- max daily loss: 10%
- max exposure: 100%
- RR: 2.0
- initial balance: 1000

Known golden benchmark:

- final balance: 1014.8392976799995
- trades: 13
- total profit: 14.839297679999504
- profit factor: 1.692128777090018

If a change touches core/backtest/persistence, this benchmark must remain unchanged unless the user explicitly requests strategy changes.

## Cross-market autonomous research

The autonomous TOP-10 scanner must NOT be dominated by Binance/crypto.

Connected classes:

- CRYPTO
- EQUITIES
- ETFs
- FOREX
- INDICES
- COMMODITIES

Selection policy:

1. discover liquid Binance USDT pairs dynamically,
2. evaluate connected non-crypto research assets,
3. reject stale/closed data,
4. rank inside each asset class,
5. normalize within each class,
6. include the strongest candidate from each active/fresh class,
7. fill remaining TOP-10 slots by cross-market score,
8. normally cap one class at 3 positions,
9. allow the cap to be exceeded only when too few other classes are currently open/fresh.

This anti-dominance behavior is intentional and must not be removed accidentally.

Current connected non-crypto research basket includes examples such as:

Equities:
- AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA, JPM, XOM

ETFs:
- SPY, QQQ, IWM, DIA, XLK, XLF

Forex:
- EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD

Indices:
- S&P 500, Nasdaq 100, Dow Jones, Russell 2000, VIX references

Commodities:
- Gold, WTI, Silver, Copper, Natural Gas, Brent continuous futures references

Crypto:
- dynamically discovered liquid Binance `*USDT` pairs

## Providers

Current real/reference data sources:

- Binance: crypto market data
- Yahoo Finance chart endpoint: equities / ETF / FX / index / commodity references
- Coinbase Exchange: USDT/USD conversion reference
- NBP: USD/PLN reference
- FED: macro releases/feed
- ECB: macro releases/feed

Important semantics:

- Gold/WTI/etc are continuous futures references/proxies where documented.
- Do not present those proxies as true spot instruments.
- Yahoo is a market-data/reference source, not a broker execution API.

## Research / learning logic

Key modules:

- `src/research/market_scanner.py`
- `src/research/autonomous_agent.py`
- `src/research/experience.py`
- `src/research/macro_events.py`
- `src/research/event_store.py`
- `src/agent/ai_manager.py`

The model currently evaluates:
- trend
- mean reversion
- breakout

It uses:
- real historical candles,
- temporal train/validation separation,
- costs,
- bounded k-NN return model,
- bounded memory adjustment based on resolved historical experiences,
- macro tags.

Do not turn historical similarity into an unbounded score override.
The memory layer is intentionally a bounded correction/tie-breaker.

TOP-10 means top candidates according to the research model.
It is NOT a guarantee of profit.

## Logging / retention

Research logs are stored under the live-state data directory.

Typical retention:
- market-universe snapshots: 14 days
- selected closed candles: 30 days
- system events: 30 days
- macro events: 90 days
- resolved learning experiences: 120 days

Cloud uses:
- `AL_TRADING_DATA_DIR=/data`

Do not commit live runtime state.

## Cloud

Cloud-ready files:

- `Dockerfile`
- `railway.json`
- `scripts/run_cloud.py`
- `AUTONOMOUS_CLOUD.md`

Recommended single-replica runtime:
- one FastAPI + autonomous worker process
- one persistent volume mounted at `/data`

Important:
- this build is single-writer for its paper/research state
- do not casually scale multiple replicas against the same state volume

Relevant environment variables:

```text
AL_TRADING_TOP_N=10
AL_TRADING_CLASS_CAP=3
AL_TRADING_CRYPTO_PRESELECT=18
AL_TRADING_SCAN_SECONDS=600
AL_TRADING_MACRO_SECONDS=600
AL_TRADING_PAPER_SECONDS=60
AL_TRADING_MIN_QUOTE_VOLUME_USDT=10000000
AL_TRADING_DATA_DIR=/data
```

## Flutter dashboard

Project:
- `app/frontend/al_trading_dashboard`

Main files:
- `lib/main.dart`
- `lib/ai_panel.dart`
- `lib/research_panel.dart`

The research panel should show:
- TOP 10
- asset class
- strategy
- cross-market score
- expected net return
- validation count
- memory sample count
- LIVE/STALE status
- class composition
- macro events
- provider/research errors

The panel should make class balance visible so Binance dominance is obvious if it ever regresses.

Market chart rule:
- Y-axis autoscale is based on visible candle high/low only.
- Entry / SL / TP overlays must not stretch the visible candle range.

## Tests

Before claiming success:

```powershell
.\run_checks.ps1
```

Known healthy state:
- `READY REGRESSION: PASS`

Network smoke is separate and uses real providers:

```powershell
python -m scripts.network_smoke
```

Research/AI regression includes:
- `tests/test_ai_manager.py`
- `tests/test_research_automation.py`

The cross-market regression must continue to verify that one asset class cannot normally take more than 3 positions when multiple fresh classes are available.

Flutter checks:

```powershell
cd .\app\frontend\al_trading_dashboard
& "C:\Users\ddare\develop\flutter\bin\flutter.bat" analyze
& "C:\Users\ddare\develop\flutter\bin\flutter.bat" test
```

## Current startup workflow

Terminal 1:

```powershell
cd "$env:USERPROFILE\Desktop\Al_Trading_Al_Git"
.\.venv\Scripts\Activate.ps1
python -m scripts.run_cloud
```

Leave it running.

Terminal 2:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/research
```

Terminal 3 — Flutter:

```powershell
cd "$env:USERPROFILE\Desktop\Al_Trading_Al_Git\app\frontend\al_trading_dashboard"
& "C:\Users\ddare\develop\flutter\bin\flutter.bat" run -d windows --dart-define=AL_TRADING_API_BASE_URL=http://127.0.0.1:8000
```

## Port 8000

If startup fails with WinError 10048, another process is already listening on port 8000.

Inspect first:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen |
    Select-Object LocalAddress,LocalPort,OwningProcess
```

Do not blindly kill unrelated processes.

## Git workflow

Before edits:
1. inspect current files,
2. inspect `git status`,
3. verify current branch,
4. do not assume docs are current unless checked.

After edits:
1. run targeted tests,
2. run `run_checks.ps1`,
3. preserve BTC golden benchmark,
4. use normal commits,
5. never force-push without explicit user instruction.

## Security / exclusions

Repository is public.

Never commit:
- `.venv/`
- `.env`
- secrets
- API keys
- passwords/tokens
- `data/live_state/`
- generated Flutter build/cache files
- local machine state

## User working style

The user prefers:
- Windows PowerShell commands ready to copy,
- VS Code,
- complete commands instead of partial fragments,
- continuous troubleshooting without stopping after every micro-step,
- no architecture rewrite unless necessary,
- preserving working benchmark/regression state.

When modifying files, favor minimal, reversible changes and verify the full chain:
code -> tests -> API -> autonomous worker -> dashboard.
