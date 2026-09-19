$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$DashboardRoot = Join-Path $ProjectRoot "app\frontend\al_trading_dashboard"

$Flutter = Get-Command flutter -ErrorAction SilentlyContinue
if ($null -eq $Flutter) {
    $KnownFlutter = "C:\Users\ddare\develop\flutter\bin\flutter.bat"
    if (Test-Path $KnownFlutter) {
        $FlutterExe = $KnownFlutter
    }
    else {
        Write-Host "Nie znaleziono Fluttera w PATH." -ForegroundColor Red
        Write-Host "Dodaj Flutter do PATH albo uruchom flutter run ręcznie w:" -ForegroundColor Yellow
        Write-Host $DashboardRoot
        exit 1
    }
}
else {
    $FlutterExe = $Flutter.Source
}

Set-Location $DashboardRoot
& $FlutterExe pub get
& $FlutterExe run -d windows --dart-define=AL_TRADING_API_BASE_URL=http://127.0.0.1:8000
