# Dashboard changes integrated

Zintegrowano poprawki z historycznych notatek dashboard/Codex bez zmiany
strategii, paper-live ani persistence.

## Reguły wykresów

1. Y-axis candlestick chart jest liczona wyłącznie z widocznych wartości
   `low` i `high` świec.
2. Entry, Stop Loss i Take Profit nie mogą rozszerzać skali świec.
3. Nie dodano nowych price overlays ani nowej zależności.
4. Projekt nadal używa istniejącego `fl_chart 1.2.0`.
5. Equity Y-axis i tooltip pokazują pełną wartość z jednym miejscem po
   przecinku, np. `1000.0`, a nie skrót `1K`.
6. Dodano `test/chart_regression_test.dart`, który blokuje regresję obu reguł.

## Walidacja wykonana przed przeniesieniem do GitHub

- Python compileall: PASS
- targeted Python regression: 22 passed
- BTC LEGACY_V1 golden: MATCH
- Flutter SDK nie był dostępny w środowisku pakowania, dlatego pełny Flutter
  test należy uruchomić lokalnie:

```powershell
cd .\app\frontend\al_trading_dashboard
flutter analyze
flutter test
```
