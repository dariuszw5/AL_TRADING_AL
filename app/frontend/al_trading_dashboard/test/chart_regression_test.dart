import 'package:flutter_test/flutter_test.dart';

import 'package:al_trading_dashboard/main.dart';

void main() {
  test('market chart scale uses candle high/low only', () {
    final bounds = marketChartAxisBounds([
      {
        'open': 102.0,
        'high': 110.0,
        'low': 90.0,
        'close': 105.0,
        // Deliberately far outside the candle range.
        'entry_price': 1000.0,
        'stop_loss': 1.0,
        'take_profit': 2000.0,
      },
      {
        'open': 105.0,
        'high': 120.0,
        'low': 95.0,
        'close': 115.0,
      },
    ]);

    // Candle range is 90..120; 8% padding = 2.4.
    expect(bounds.minY, closeTo(87.6, 1e-9));
    expect(bounds.maxY, closeTo(122.4, 1e-9));
  });

  test('equity labels keep the real value with one decimal', () {
    expect(equityAxisLabel(1000), '1000.0');
    expect(equityAxisLabel(1014.839), '1014.8');
    expect(equityAxisLabel(-12.34), '-12.3');
  });
}
