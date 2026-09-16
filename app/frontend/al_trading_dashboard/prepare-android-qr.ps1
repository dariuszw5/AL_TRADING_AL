$ErrorActionPreference = 'Stop'
$api = 'http://100.77.193.89:8000'
$apkName = 'AL-Trading-1.1.0.apk'
$apkDir = Join-Path $PSScriptRoot 'build\app\outputs\flutter-apk'
$apk = Join-Path $apkDir $apkName

flutter build apk --release "--dart-define=AL_TRADING_API_BASE_URL=$api"
if ($LASTEXITCODE -ne 0) {
  throw 'APK build failed. Server and QR were not started.'
}
Copy-Item (Join-Path $apkDir 'app-release.apk') $apk -Force

$tailscaleIp = (tailscale ip -4 | Select-Object -First 1).Trim()
if (-not $tailscaleIp) {
  throw 'Tailscale IP address was not found.'
}
$url = "http://${tailscaleIp}:8765/$apkName"
$qr = Join-Path $apkDir 'AL-Trading-1.1.0-QR.png'
Invoke-WebRequest -Uri ("https://api.qrserver.com/v1/create-qr-code/?size=600x600&data=" + [uri]::EscapeDataString($url)) -OutFile $qr
Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location -LiteralPath '$apkDir'; python -m http.server 8765 --bind $tailscaleIp"
Start-Process $qr
Write-Host ''
Write-Host 'Done. Scan the opened QR from a phone on the same Tailscale network.' -ForegroundColor Green
Write-Host "APK link: $url"
Write-Host 'Keep the server window open until the phone finishes downloading.' -ForegroundColor Yellow
