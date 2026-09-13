# CODEX HANDOFF — AL TRADING AGENT

## Repository

- Repository: `dariuszw5/AL_TRADING_AL`
- Default branch: `main`
- Current project commit after dashboard/API/OOS work: `b839f8c37456a82457d435502cdd8b00f7b2475d`
- Frozen release tag: `v1.0.0`
- Frozen release commit: `33c0a5a` — `Harden live state persistence against transient Windows locks`

## Important working rule

Do **not** change the frozen trading strategy, release `v1.0.0`, paper-live logic, or live-state persistence unless explicitly requested. Current work is primarily presentation/dashboard work.

Keep backend and paper-live behavior stable. Prefer one safe change at a time and run tests after changes.

## Environment

- Windows
- PowerShell
- VS Code
- Python 3.14.7
- Virtual environment: `.venv`
- Flutter dashboard project: `app/frontend/al_trading_dashboard`
- Flutter executable used locally: `C:\Users\ddare\develop\flutter\bin\flutter.bat`

## Frozen production strategy

- Symbol: `BTCUSDT`
- Interval: `1m`
- BUY RSI: `33.8`
- SELL RSI: `68.5`
- Max position candles: `241`
- Min difference: `1.0`
- RSI method: `classic`
- Trading fee: `0.0004`
- Initial balance: `1000`

Known backend test state before dashboard work: **320 passed**.

## Paper-live / API

FastAPI dashboard API lives in:

- `app/backend/main.py`

It is read-only and exposes endpoints including:

- `/api/health`
- `/api/status`
- `/api/trades`
- `/api/equity`
- `/api/daily`
- `/api/market`
- `/api/files`

The API reads paper-live runtime state from `data/live_state/`, which is intentionally ignored by Git and must not be committed.

`/api/market` fetches BTCUSDT 1m candles and caches them briefly so the dashboard does not request market data continuously.

## Flutter dashboard

Main UI file:

- `app/frontend/al_trading_dashboard/lib/main.dart`

Widget test:

- `app/frontend/al_trading_dashboard/test/widget_test.dart`

The dashboard currently shows:

- AL TRADING AGENT header
- PAPER LIVE status
- account card
- current position card
- performance card
- frozen strategy card
- BTCUSDT 1m candlestick chart
- equity curve
- trade history
- auto-refresh every 5 seconds

### Localization already fixed

Widget tests originally expected English labels `ACCOUNT` and `POSITION`, while UI was Polish. Tests were updated to:

- `KONTO`
- `POZYCJA`

After that, the widget test passed:

- `All tests passed!`

A malformed API error string in `main.dart` was also fixed.

## Current dashboard behavior observed

The dashboard is functional and receives live paper data.

Observed example state during development:

- account balance around `1001.38`
- net P/L around `+1.38`
- current position was `SELL OPEN`
- BTCUSDT market around `77080`
- position entry around `77192`
- stop loss around `81051`
- take profit around `69473`
- unrealized P/L was displayed correctly

These are runtime examples only and should not be hardcoded.

## Main chart problem to solve next

The market chart currently derives its Y-axis from candle highs/lows **plus Entry / Stop Loss / Take Profit**.

Because SL/TP can be thousands of dollars away from current price, the chart zooms out too far and the actual candles look almost flat.

### Root cause

In `buildMarketChart()`, current logic gathers candle low/high plus position levels into the same min/max range.

Conceptually it does this:

```dart
final levels = <double>[
  minY,
  maxY,
  ?entryPrice,
  ?stopLoss,
  ?takeProfit,
];

minY = levels.reduce((a, b) => a < b ? a : b);
maxY = levels.reduce((a, b) => a > b ? a : b);
```

### Desired behavior

Default Y-axis scaling should use **only visible candle highs and lows**, with a small padding.

Entry / SL / TP should be treated as visual overlays and must **not** force the chart autoscale.

If a level is outside the current candle viewport, acceptable later UX options include:

1. draw only levels currently inside the visible range and show off-screen indicators/badges,
2. provide an optional `Dopasuj do pozycji` / fit-position mode,
3. use a custom `Stack` / `CustomPaint` overlay.

Do not claim all Entry/SL/TP levels can always remain visible while also keeping tight candle scaling when the levels are far outside the market range.

## Important fl_chart rule

A previous attempt using `extraLinesData` was incompatible with the installed `fl_chart` API.

Before adding chart overlays, inspect the exact installed `fl_chart` version from `pubspec.lock` and inspect the corresponding package API/source if needed.

Do **not** guess chart properties from a different fl_chart version.

Useful command locally:

```powershell
Select-String -Path .\pubspec.lock -Pattern "fl_chart:" -Context 0,6
```

## Equity chart issue

The equity chart works, but its left Y-axis uses compact/default labels such as `1K`, which is not useful when balances are close together around ~1000.

Desired labels should show actual values, for example:

- `997.5`
- `1000.0`
- `1004.2`

Likely approach: custom `leftTitles` with `value.toStringAsFixed(1)` and enough reserved width. Verify compatibility with the installed fl_chart version.

## Remaining small UI cleanup

There is still a mixed-language auto-refresh string in `main.dart`:

```dart
lastUpdate == null
  ? 'Automatyczne odświeżanie: 5 s'
  : 'Auto-refresh: 5s  •  '
    'Aktualizacja ...'
```

Eventually make it consistently Polish, e.g.:

```text
Automatyczne odświeżanie: 5 s  •  Aktualizacja ...
```

This is lower priority than the chart scaling issue.

## Safe next steps

1. Inspect current `main.dart` before changing anything.
2. Inspect exact `fl_chart` version/API.
3. Change market chart autoscaling so Y-range is based only on candle highs/lows.
4. Do not change strategy/backend/paper-live behavior.
5. Fix equity left-axis formatting.
6. Run Flutter format/analyze/widget test.
7. Only after tests pass, run the Windows dashboard.
8. Add Entry/SL/TP overlays later, using the actual installed fl_chart API, without changing autoscale.

Suggested validation commands from the Flutter project directory:

```powershell
& "C:\Users\ddare\develop\flutter\bin\flutter.bat" format .\lib\main.dart
& "C:\Users\ddare\develop\flutter\bin\flutter.bat" analyze
& "C:\Users\ddare\develop\flutter\bin\flutter.bat" test test\widget_test.dart --reporter expanded
```

Expected successful state:

- `No issues found!`
- widget test passes

## Git / security notes

The repository is public.

The root `.gitignore` intentionally excludes:

- `.venv/`
- Python caches
- IDE files
- `data/live_state/`
- Flutter generated build/cache paths
- `.env`
- `.env.*`
- temporary backup files

Do not commit local secrets or live paper-state files.

## Data and diagnostics included

The repository includes forward/OOS datasets and many analysis, robustness, stress, audit, comparison, and paper-live helper scripts. They are useful historical context, but the frozen strategy above remains the currently approved configuration unless the user explicitly decides otherwise.
