param(
    [string]$Flutter = "C:\\Users\\ddare\\develop\\flutter\\bin\\flutter.bat",
    [string]$ApiBaseUrl = "http://34.45.151.160:8000"
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Project = Join-Path $RepoRoot "app\\frontend\\al_trading_dashboard"
$ReleaseDir = Join-Path $Project "build\\windows\\x64\\runner\\Release"
$InstallDir = Join-Path $env:LOCALAPPDATA "AL_Trading_Agent"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "AL Trading Agent.lnk"
$ExeName = "al_trading_dashboard.exe"
$ExePath = Join-Path $InstallDir $ExeName

Write-Host ""
Write-Host "=== AL TRADING AGENT | WINDOWS DESKTOP INSTALL ===" -ForegroundColor Cyan

if (-not (Test-Path $Flutter)) {
    throw "Nie znaleziono Fluttera: $Flutter"
}

if (-not (Test-Path $Project)) {
    throw "Nie znaleziono projektu Flutter: $Project"
}

Write-Host ""
Write-Host "=== 1. ZAMYKANIE STAREJ WERSJI ===" -ForegroundColor Yellow
Get-Process al_trading_dashboard -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue

Set-Location $Project

Write-Host ""
Write-Host "=== 2. ZALEZNOSCI ===" -ForegroundColor Yellow
& $Flutter pub get
if ($LASTEXITCODE -ne 0) {
    throw "flutter pub get failed"
}

Write-Host ""
Write-Host "=== 3. ANALIZA ===" -ForegroundColor Yellow
& $Flutter analyze
if ($LASTEXITCODE -ne 0) {
    throw "flutter analyze failed"
}

Write-Host ""
Write-Host "=== 4. BUILD WINDOWS RELEASE ===" -ForegroundColor Yellow
& $Flutter build windows --release `
    --dart-define="AL_TRADING_API_BASE_URL=$ApiBaseUrl"

if ($LASTEXITCODE -ne 0) {
    throw "flutter build windows failed"
}

$BuiltExe = Join-Path $ReleaseDir $ExeName
if (-not (Test-Path $BuiltExe)) {
    throw "Nie znaleziono zbudowanej aplikacji: $BuiltExe"
}

Write-Host ""
Write-Host "=== 5. INSTALACJA LOKALNA ===" -ForegroundColor Yellow
if (Test-Path $InstallDir) {
    Remove-Item $InstallDir -Recurse -Force
}
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

Copy-Item `
    -Path (Join-Path $ReleaseDir "*") `
    -Destination $InstallDir `
    -Recurse `
    -Force

if (-not (Test-Path $ExePath)) {
    throw "Nie znaleziono aplikacji po instalacji: $ExePath"
}

Write-Host ""
Write-Host "=== 6. SKROT NA PULPICIE ===" -ForegroundColor Yellow
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.IconLocation = "$ExePath,0"
$Shortcut.Description = "AL Trading Agent - paper trading"
$Shortcut.Save()

Write-Host ""
Write-Host "=== GOTOWE ===" -ForegroundColor Green
Write-Host "Aplikacja: $ExePath"
Write-Host "Skrot:     $ShortcutPath"
Write-Host "API:       $ApiBaseUrl"

Write-Host ""
Write-Host "Uruchamiam AL Trading Agent..." -ForegroundColor Cyan
Start-Process $ExePath
