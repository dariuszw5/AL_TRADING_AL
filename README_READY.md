# AL Trading Agent — gotowy wariant bez przebudowy architektury

Ten wariant zachowuje istniejący rdzeń aplikacji:

- `AgentLoop`
- `AgentEngine`
- `TradingEngine`
- `RiskGuard`
- `LiveStateStore` / JSON
- FastAPI dashboard API
- Flutter dashboard

Nie przeniesiono eksperymentalnego stosu SQLite/runtime/cutover z późniejszych faz.

## Co poprawiono

1. Multi-market paper-live na istniejącym `AgentLoop`:
   - BTCUSDT
   - ETHUSDT
   - SOLUSDT
   - BNBUSDT
   - XRPUSDT
   - GOLD_FUT_CONT (`GC=F`, futures proxy)
   - WTI_FUT_CONT (`CL=F`, futures proxy)
   - EURUSD
   - AAPL

2. Realne źródła danych:
   - Binance dla crypto
   - Yahoo chart dla pozostałych instrumentów

3. GOLD/WTI nie udają spotu:
   - aliasy `XAUUSD` i `WTIUSD` nadal działają dla kompatybilności,
   - w aplikacji są oznaczone jako continuous futures proxy.

4. PLN jako warstwa raportowa, bez zmiany paper cash:
   - USD -> PLN: oficjalny kurs referencyjny NBP tabela A,
   - USDT -> USD: realny ticker Coinbase Exchange,
   - USDT -> USD -> PLN: bez założenia `USDT = USD`,
   - przy braku realnej ścieżki FX PLN jest niedostępne zamiast sztucznego kursu.

5. Backend zwraca wartości native i PLN:
   - balance / balance_pln,
   - net_profit / net_profit_pln,
   - unrealized_profit / unrealized_profit_pln,
   - market_price / market_price_pln,
   - trade profit / profit_pln,
   - equity native / PLN.

6. `/api/market` zwraca także provider, provider symbol, wiek ostatniej świecy,
   status stale oraz informacje o ścieżce PLN.

7. Dashboard:
   - aktywny jest istniejący `DashboardPage`,
   - lista rynków jest zgodna z backendem,
   - pokazuje realne przeliczenie PLN, gdy FX jest dostępny,
   - pokazuje źródło i aktualność danych,
   - wykres rynku skaluje się tylko po high/low świec,
   - Entry / Stop Loss / Take Profit nie rozciągają osi Y,
   - oś equity pokazuje pełne wartości z jednym miejscem po przecinku.

8. Core paper-live nie uruchamia automatycznie eksperymentalnego AI.
   AI można włączyć jawnie:

   ```powershell
   $env:AL_TRADING_ENABLE_AI = "1"
   ```

## Bezpieczeństwo

- tylko paper trading,
- zero prawdziwych zleceń,
- wirtualne środki,
- PLN jest przeliczeniem raportowym,
- frozen BTC strategy nie została zmieniona.

BTC golden po poprawkach:

- final balance: `1014.8392976799995`
- trades: `13`
- total profit: `14.839297679999504`
- profit factor: `1.692128777090018`

## Pierwsze uruchomienie — Windows PowerShell

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup_project.ps1
```

Następnie w osobnych terminalach:

```powershell
.\start_paper_live.ps1
```

```powershell
.\start_api.ps1
```

```powershell
.\start_dashboard.ps1
```

## Testy

```powershell
.\run_checks.ps1
```

Realny, tylko-odczytowy smoke providerów i FX:

```powershell
python -m scripts.network_smoke
```

Flutter:

```powershell
cd .\app\frontend\al_trading_dashboard
flutter analyze
flutter test
```

## Ważne ograniczenia

- Yahoo chart nie jest oficjalnym broker API.
- `GC=F` i `CL=F` to continuous futures proxy, nie spot GOLD/WTI.
- jedna zamrożona strategia nie została osobno zoptymalizowana dla każdego rynku.
- przeliczenie PLN służy raportowaniu; nie przebudowuje paper cash.
- prawdziwe zlecenia giełdowe nie są obsługiwane.
