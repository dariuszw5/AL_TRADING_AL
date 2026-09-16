# PROVIDER CAPABILITY MATRIX

Probe timestamp UTC: `2026-09-16T15:06:48.430608+00:00`

This document records empirical provider capability observations
for the current AL_TRADING_AL provider configuration.

It is a point-in-time capability probe, not a guarantee of future
availability. Missing information is recorded as UNKNOWN rather
than inferred.

No trading execution semantics are changed by this probe.

## Summary

| Asset | Provider | Symbol | Bid | Ask | Depth | Last | Volume | Feed delay | Metadata | Tick size | Qty rules | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | binance | BTCUSDT | YES | YES | YES | YES | YES | REALTIME | YES | YES | YES | CONNECTED |
| ETHUSDT | binance | ETHUSDT | YES | YES | YES | YES | YES | REALTIME | YES | YES | YES | CONNECTED |
| SOLUSDT | binance | SOLUSDT | YES | YES | YES | YES | YES | REALTIME | YES | YES | YES | CONNECTED |
| BNBUSDT | binance | BNBUSDT | YES | YES | YES | YES | YES | REALTIME | YES | YES | YES | CONNECTED |
| XRPUSDT | binance | XRPUSDT | YES | YES | YES | YES | YES | REALTIME | YES | YES | YES | CONNECTED |
| GOLD_FUT_CONT | yahoo | GC=F | NO | NO | NO | YES | YES | UNKNOWN | YES | NO | NO | CONNECTED |
| WTI_FUT_CONT | yahoo | CL=F | NO | NO | NO | YES | YES | UNKNOWN | YES | NO | NO | CONNECTED |
| EURUSD | yahoo | EURUSD=X | NO | NO | NO | YES | YES | UNKNOWN | YES | NO | NO | CONNECTED |
| AAPL | yahoo | AAPL | NO | NO | NO | YES | YES | UNKNOWN | YES | NO | NO | CONNECTED |

## Detailed observations

### BTCUSDT

- asset_id: `BTCUSDT`
- provider: `binance`
- provider_symbol: `BTCUSDT`
- probe_status: `CONNECTED`
- bid available: `YES`
- ask available: `YES`
- book depth available: `YES`
- last available: `YES`
- volume available: `YES`
- feed delay: `REALTIME`
- delay source: `/api/v3/ticker/24hr closeTime vs /api/v3/time serverTime`
- observed/latest timestamp age seconds: `0.0`
- streaming available: `UNKNOWN_NOT_PROBED`
- instrument metadata: `YES`
- tick size from source: `YES`
- quantity rules from source: `YES`
- tick_size: `0.01000000`
- step_size: `0.00001000`
- minimum_quantity: `0.00001000`
- minimum_notional: `5.00000000`
- rate limits: `REQUEST_WEIGHT:6000/1MINUTE; ORDERS:100/10SECOND; ORDERS:200000/1DAY; RAW_REQUESTS:300000/5MINUTE`
- API status: `OFFICIAL_PUBLIC_READ_ONLY_ENDPOINT`
- provider note: data-api.binance.vision public market-data endpoint

Endpoints used:
- `server_time`: status=`200`, latency_ms=`1256.47`, URL=`https://data-api.binance.vision/api/v3/time`
- `book_ticker`: status=`200`, latency_ms=`259.44`, URL=`https://data-api.binance.vision/api/v3/ticker/bookTicker?symbol=BTCUSDT`
- `depth`: status=`200`, latency_ms=`341.62`, URL=`https://data-api.binance.vision/api/v3/depth?symbol=BTCUSDT&limit=5`
- `ticker_24hr`: status=`200`, latency_ms=`317.86`, URL=`https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT`
- `exchange_info`: status=`200`, latency_ms=`258.75`, URL=`https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BTCUSDT`
- `klines`: status=`200`, latency_ms=`259.93`, URL=`https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=2`

### ETHUSDT

- asset_id: `ETHUSDT`
- provider: `binance`
- provider_symbol: `ETHUSDT`
- probe_status: `CONNECTED`
- bid available: `YES`
- ask available: `YES`
- book depth available: `YES`
- last available: `YES`
- volume available: `YES`
- feed delay: `REALTIME`
- delay source: `/api/v3/ticker/24hr closeTime vs /api/v3/time serverTime`
- observed/latest timestamp age seconds: `0.0`
- streaming available: `UNKNOWN_NOT_PROBED`
- instrument metadata: `YES`
- tick size from source: `YES`
- quantity rules from source: `YES`
- tick_size: `0.01000000`
- step_size: `0.00010000`
- minimum_quantity: `0.00010000`
- minimum_notional: `5.00000000`
- rate limits: `REQUEST_WEIGHT:6000/1MINUTE; ORDERS:100/10SECOND; ORDERS:200000/1DAY; RAW_REQUESTS:300000/5MINUTE`
- API status: `OFFICIAL_PUBLIC_READ_ONLY_ENDPOINT`
- provider note: data-api.binance.vision public market-data endpoint

Endpoints used:
- `server_time`: status=`200`, latency_ms=`260.13`, URL=`https://data-api.binance.vision/api/v3/time`
- `book_ticker`: status=`200`, latency_ms=`342.7`, URL=`https://data-api.binance.vision/api/v3/ticker/bookTicker?symbol=ETHUSDT`
- `depth`: status=`200`, latency_ms=`280.38`, URL=`https://data-api.binance.vision/api/v3/depth?symbol=ETHUSDT&limit=5`
- `ticker_24hr`: status=`200`, latency_ms=`343.72`, URL=`https://data-api.binance.vision/api/v3/ticker/24hr?symbol=ETHUSDT`
- `exchange_info`: status=`200`, latency_ms=`396.46`, URL=`https://data-api.binance.vision/api/v3/exchangeInfo?symbol=ETHUSDT`
- `klines`: status=`200`, latency_ms=`260.74`, URL=`https://data-api.binance.vision/api/v3/klines?symbol=ETHUSDT&interval=1m&limit=2`

### SOLUSDT

- asset_id: `SOLUSDT`
- provider: `binance`
- provider_symbol: `SOLUSDT`
- probe_status: `CONNECTED`
- bid available: `YES`
- ask available: `YES`
- book depth available: `YES`
- last available: `YES`
- volume available: `YES`
- feed delay: `REALTIME`
- delay source: `/api/v3/ticker/24hr closeTime vs /api/v3/time serverTime`
- observed/latest timestamp age seconds: `0.0`
- streaming available: `UNKNOWN_NOT_PROBED`
- instrument metadata: `YES`
- tick size from source: `YES`
- quantity rules from source: `YES`
- tick_size: `0.01000000`
- step_size: `0.00100000`
- minimum_quantity: `0.00100000`
- minimum_notional: `5.00000000`
- rate limits: `REQUEST_WEIGHT:6000/1MINUTE; ORDERS:100/10SECOND; ORDERS:200000/1DAY; RAW_REQUESTS:300000/5MINUTE`
- API status: `OFFICIAL_PUBLIC_READ_ONLY_ENDPOINT`
- provider note: data-api.binance.vision public market-data endpoint

Endpoints used:
- `server_time`: status=`200`, latency_ms=`357.84`, URL=`https://data-api.binance.vision/api/v3/time`
- `book_ticker`: status=`200`, latency_ms=`297.31`, URL=`https://data-api.binance.vision/api/v3/ticker/bookTicker?symbol=SOLUSDT`
- `depth`: status=`200`, latency_ms=`316.34`, URL=`https://data-api.binance.vision/api/v3/depth?symbol=SOLUSDT&limit=5`
- `ticker_24hr`: status=`200`, latency_ms=`310.25`, URL=`https://data-api.binance.vision/api/v3/ticker/24hr?symbol=SOLUSDT`
- `exchange_info`: status=`200`, latency_ms=`308.3`, URL=`https://data-api.binance.vision/api/v3/exchangeInfo?symbol=SOLUSDT`
- `klines`: status=`200`, latency_ms=`262.01`, URL=`https://data-api.binance.vision/api/v3/klines?symbol=SOLUSDT&interval=1m&limit=2`

### BNBUSDT

- asset_id: `BNBUSDT`
- provider: `binance`
- provider_symbol: `BNBUSDT`
- probe_status: `CONNECTED`
- bid available: `YES`
- ask available: `YES`
- book depth available: `YES`
- last available: `YES`
- volume available: `YES`
- feed delay: `REALTIME`
- delay source: `/api/v3/ticker/24hr closeTime vs /api/v3/time serverTime`
- observed/latest timestamp age seconds: `0.0`
- streaming available: `UNKNOWN_NOT_PROBED`
- instrument metadata: `YES`
- tick size from source: `YES`
- quantity rules from source: `YES`
- tick_size: `0.01000000`
- step_size: `0.00100000`
- minimum_quantity: `0.00100000`
- minimum_notional: `5.00000000`
- rate limits: `REQUEST_WEIGHT:6000/1MINUTE; ORDERS:100/10SECOND; ORDERS:200000/1DAY; RAW_REQUESTS:300000/5MINUTE`
- API status: `OFFICIAL_PUBLIC_READ_ONLY_ENDPOINT`
- provider note: data-api.binance.vision public market-data endpoint

Endpoints used:
- `server_time`: status=`200`, latency_ms=`347.75`, URL=`https://data-api.binance.vision/api/v3/time`
- `book_ticker`: status=`200`, latency_ms=`312.68`, URL=`https://data-api.binance.vision/api/v3/ticker/bookTicker?symbol=BNBUSDT`
- `depth`: status=`200`, latency_ms=`279.83`, URL=`https://data-api.binance.vision/api/v3/depth?symbol=BNBUSDT&limit=5`
- `ticker_24hr`: status=`200`, latency_ms=`272.39`, URL=`https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BNBUSDT`
- `exchange_info`: status=`200`, latency_ms=`262.96`, URL=`https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BNBUSDT`
- `klines`: status=`200`, latency_ms=`310.11`, URL=`https://data-api.binance.vision/api/v3/klines?symbol=BNBUSDT&interval=1m&limit=2`

### XRPUSDT

- asset_id: `XRPUSDT`
- provider: `binance`
- provider_symbol: `XRPUSDT`
- probe_status: `CONNECTED`
- bid available: `YES`
- ask available: `YES`
- book depth available: `YES`
- last available: `YES`
- volume available: `YES`
- feed delay: `REALTIME`
- delay source: `/api/v3/ticker/24hr closeTime vs /api/v3/time serverTime`
- observed/latest timestamp age seconds: `0.0`
- streaming available: `UNKNOWN_NOT_PROBED`
- instrument metadata: `YES`
- tick size from source: `YES`
- quantity rules from source: `YES`
- tick_size: `0.00010000`
- step_size: `0.10000000`
- minimum_quantity: `0.10000000`
- minimum_notional: `5.00000000`
- rate limits: `REQUEST_WEIGHT:6000/1MINUTE; ORDERS:100/10SECOND; ORDERS:200000/1DAY; RAW_REQUESTS:300000/5MINUTE`
- API status: `OFFICIAL_PUBLIC_READ_ONLY_ENDPOINT`
- provider note: data-api.binance.vision public market-data endpoint

Endpoints used:
- `server_time`: status=`200`, latency_ms=`295.57`, URL=`https://data-api.binance.vision/api/v3/time`
- `book_ticker`: status=`200`, latency_ms=`262.58`, URL=`https://data-api.binance.vision/api/v3/ticker/bookTicker?symbol=XRPUSDT`
- `depth`: status=`200`, latency_ms=`262.99`, URL=`https://data-api.binance.vision/api/v3/depth?symbol=XRPUSDT&limit=5`
- `ticker_24hr`: status=`200`, latency_ms=`411.76`, URL=`https://data-api.binance.vision/api/v3/ticker/24hr?symbol=XRPUSDT`
- `exchange_info`: status=`200`, latency_ms=`261.74`, URL=`https://data-api.binance.vision/api/v3/exchangeInfo?symbol=XRPUSDT`
- `klines`: status=`200`, latency_ms=`264.43`, URL=`https://data-api.binance.vision/api/v3/klines?symbol=XRPUSDT&interval=1m&limit=2`

### GOLD_FUT_CONT

- asset_id: `GOLD_FUT_CONT`
- provider: `yahoo`
- provider_symbol: `GC=F`
- probe_status: `CONNECTED`
- bid available: `NO`
- ask available: `NO`
- book depth available: `NO`
- last available: `YES`
- volume available: `YES`
- feed delay: `UNKNOWN`
- delay source: `UNKNOWN - metadata field absent`
- observed/latest timestamp age seconds: `602.785`
- streaming available: `UNKNOWN_NOT_PROBED`
- instrument metadata: `YES`
- tick size from source: `NO`
- quantity rules from source: `NO`
- tick_size: `UNKNOWN`
- step_size: `UNKNOWN`
- minimum_quantity: `UNKNOWN`
- minimum_notional: `UNKNOWN`
- rate limits: `UNKNOWN - no stable public API contract`
- API status: `UNOFFICIAL / DEGRADED_BY_DESIGN`
- provider note: Yahoo Finance v8 chart endpoint; research/display source, not a broker execution feed

Endpoints used:
- `chart`: status=`200`, latency_ms=`278.66`, URL=`https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?range=1d&interval=1m&includePrePost=false&events=div%2Csplits`

### WTI_FUT_CONT

- asset_id: `WTI_FUT_CONT`
- provider: `yahoo`
- provider_symbol: `CL=F`
- probe_status: `CONNECTED`
- bid available: `NO`
- ask available: `NO`
- book depth available: `NO`
- last available: `YES`
- volume available: `YES`
- feed delay: `UNKNOWN`
- delay source: `UNKNOWN - metadata field absent`
- observed/latest timestamp age seconds: `600.867`
- streaming available: `UNKNOWN_NOT_PROBED`
- instrument metadata: `YES`
- tick size from source: `NO`
- quantity rules from source: `NO`
- tick_size: `UNKNOWN`
- step_size: `UNKNOWN`
- minimum_quantity: `UNKNOWN`
- minimum_notional: `UNKNOWN`
- rate limits: `UNKNOWN - no stable public API contract`
- API status: `UNOFFICIAL / DEGRADED_BY_DESIGN`
- provider note: Yahoo Finance v8 chart endpoint; research/display source, not a broker execution feed

Endpoints used:
- `chart`: status=`200`, latency_ms=`79.25`, URL=`https://query1.finance.yahoo.com/v8/finance/chart/CL%3DF?range=1d&interval=1m&includePrePost=false&events=div%2Csplits`

### EURUSD

- asset_id: `EURUSD`
- provider: `yahoo`
- provider_symbol: `EURUSD=X`
- probe_status: `CONNECTED`
- bid available: `NO`
- ask available: `NO`
- book depth available: `NO`
- last available: `YES`
- volume available: `YES`
- feed delay: `UNKNOWN`
- delay source: `UNKNOWN - metadata field absent`
- observed/latest timestamp age seconds: `51.091`
- streaming available: `UNKNOWN_NOT_PROBED`
- instrument metadata: `YES`
- tick size from source: `NO`
- quantity rules from source: `NO`
- tick_size: `UNKNOWN`
- step_size: `UNKNOWN`
- minimum_quantity: `UNKNOWN`
- minimum_notional: `UNKNOWN`
- rate limits: `UNKNOWN - no stable public API contract`
- API status: `UNOFFICIAL / DEGRADED_BY_DESIGN`
- provider note: Yahoo Finance v8 chart endpoint; research/display source, not a broker execution feed

Endpoints used:
- `chart`: status=`200`, latency_ms=`221.49`, URL=`https://query1.finance.yahoo.com/v8/finance/chart/EURUSD%3DX?range=1d&interval=1m&includePrePost=false&events=div%2Csplits`

### AAPL

- asset_id: `AAPL`
- provider: `yahoo`
- provider_symbol: `AAPL`
- probe_status: `CONNECTED`
- bid available: `NO`
- ask available: `NO`
- book depth available: `NO`
- last available: `YES`
- volume available: `YES`
- feed delay: `UNKNOWN`
- delay source: `UNKNOWN - metadata field absent`
- observed/latest timestamp age seconds: `2.431`
- streaming available: `UNKNOWN_NOT_PROBED`
- instrument metadata: `YES`
- tick size from source: `NO`
- quantity rules from source: `NO`
- tick_size: `UNKNOWN`
- step_size: `UNKNOWN`
- minimum_quantity: `UNKNOWN`
- minimum_notional: `UNKNOWN`
- rate limits: `UNKNOWN - no stable public API contract`
- API status: `UNOFFICIAL / DEGRADED_BY_DESIGN`
- provider note: Yahoo Finance v8 chart endpoint; research/display source, not a broker execution feed

Endpoints used:
- `chart`: status=`200`, latency_ms=`339.52`, URL=`https://query1.finance.yahoo.com/v8/finance/chart/AAPL?range=1d&interval=1m&includePrePost=false&events=div%2Csplits`

## Provider notes

### Binance

`data-api.binance.vision` is used as the project's public read-only market-data source.
The probe checks bookTicker, depth, ticker/24hr, exchangeInfo, klines and server time.

### Yahoo

`query1.finance.yahoo.com/v8/finance/chart` is treated as `UNOFFICIAL / DEGRADED_BY_DESIGN`.
It is not treated as an execution-grade provider. Missing bid/ask, depth or trading rules are not fabricated.

`GOLD_FUT_CONT` (`GC=F`) and `WTI_FUT_CONT` (`CL=F`) are continuous-futures proxies, not spot instruments.

## Remaining unknowns

- Streaming capability is intentionally `UNKNOWN_NOT_PROBED` because this probe does not add a WebSocket dependency.
- Yahoo rate limits are UNKNOWN because the chart endpoint does not have a stable public API contract.
- Market/session-calendar correctness is not established by this probe; that belongs to the market-data/session phases.
- This matrix does not authorize REALISTIC_V2 fills.
