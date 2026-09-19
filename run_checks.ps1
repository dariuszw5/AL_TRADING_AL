$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "Brak .venv. Uruchom .\setup_project.ps1" -ForegroundColor Red
    exit 1
}

Set-Location $ProjectRoot

Write-Host "=== CORE / MULTI-ASSET / PLN ===" -ForegroundColor Cyan
& $PythonExe -m pytest -q `
    tests/test_backend_multi_asset_api.py `
    tests/test_multi_asset.py `
    tests/test_pln_reporting.py `
    tests/test_data_provider_storage.py `
    tests/test_agent_loop.py `
    tests/test_agent_loop_live.py `
    tests/test_ai_manager.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=== BACKTEST REGRESSION ===" -ForegroundColor Cyan
& $PythonExe -m pytest -q `
    tests/test_backtest_agent_integration.py `
    tests/test_backtest_auto_close.py `
    tests/test_backtest_close.py `
    tests/test_backtest_engine.py `
    tests/test_backtest_engine_fee.py `
    tests/test_backtest_metrics.py `
    tests/test_backtest_report.py `
    tests/test_backtest_report_metrics.py `
    tests/test_backtest_report_trades.py `
    tests/test_backtest_result.py `
    tests/test_backtest_runner.py `
    tests/test_backtest_runner_data_source.py `
    tests/test_backtest_runner_fee.py `
    tests/test_backtest_runner_metrics.py `
    tests/test_backtest_runner_real_file.py `
    tests/test_backtest_runner_strategy_config.py `
    tests/test_backtest_runner_trades.py `
    tests/test_backtest_trade_history.py `
    tests/test_backtester.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=== BTC LEGACY GOLDEN ===" -ForegroundColor Cyan
& $PythonExe -m scripts.run_benchmark
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "READY REGRESSION: PASS" -ForegroundColor Green
Write-Host "Sieciowy smoke uruchom osobno: python -m scripts.network_smoke" -ForegroundColor Yellow
