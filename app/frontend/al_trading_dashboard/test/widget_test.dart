import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:al_trading_dashboard/main.dart';
import 'package:al_trading_dashboard/pro_dashboard.dart';

Future<Map<String, dynamic>> multiMarketLoader() async {
  return <String, dynamic>{
    'assets': <Map<String, dynamic>>[
      {
        'symbol': 'BTCUSDT',
        'name': 'Bitcoin',
        'asset_type': 'crypto',
        'market_price': 60000.0,
        'quote': 'USDT',
        'market_stale': false,
        'position': 'FLAT',
      },
      {
        'symbol': 'ETHUSDT',
        'name': 'Ethereum',
        'asset_type': 'crypto',
        'market_price': 3000.0,
        'quote': 'USDT',
        'market_stale': false,
        'position': 'LONG',
      },
    ],
    'research': <String, dynamic>{
      'available': true,
      'stale': false,
      'opportunities': <Map<String, dynamic>>[
        {
          'symbol': 'CUSDT',
          'name': 'C',
          'asset_class': 'CRYPTO',
          'strategy': 'breakout',
        },
      ],
      'selected_by_class': <String, dynamic>{'CRYPTO': 1},
      'available_by_class': <String, dynamic>{'CRYPTO': 1},
      'macro_events': <dynamic>[],
      'errors': <String, dynamic>{},
    },
    'ai': <String, dynamic>{
      'available': true,
      'stale': false,
      'model': 'cross-market multi-position k-NN v3.4',
      'initial_balance': 1000.0,
      'funded_capital': 1000.0,
      'balance': 950.0,
      'equity': 1001.25,
      'realized_pnl': 0.0,
      'unrealized_pnl': 1.25,
      'positions': <String, dynamic>{
        'ETHUSDT': {
          'symbol': 'ETHUSDT',
          'side': 'LONG',
          'strategy': 'trend',
          'entry': 2990.0,
          'allocation_pln': 50.0,
          'unrealized_pnl': 1.25,
        },
      },
      'pending': <dynamic>[],
      'ranking': <Map<String, dynamic>>[
        {
          'symbol': 'CUSDT',
          'strategy': 'breakout',
          'side': 'LONG',
          'expected_net_return': 0.0035,
          'eligible': true,
        },
      ],
      'market_marks': <String, dynamic>{
        'CUSDT': {'price': 0.084},
      },
      'trades': <Map<String, dynamic>>[
        {
          'symbol': 'CUSDT',
          'strategy': 'breakout',
          'side': 'LONG',
          'profit': 3.5,
          'reason': 'TAKE_PROFIT',
        },
      ],
      'decisions': <dynamic>[],
      'decision': {'action': 'HOLD_MULTI', 'reason': 'Manage positions'},
    },
    'user_portfolio': <String, dynamic>{
      'available': true,
      'balance': 0.0,
      'total_deposited': 1000.0,
      'total_withdrawn': 0.0,
    },
  };
}

void main() {
  testWidgets('production application uses the autonomous ProDashboard', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const AlTradingApp());
    expect(find.byType(ProDashboard), findsOneWidget);
    expect(find.text('Przegląd portfela'), findsOneWidget);
  });

  testWidgets('market details include dynamic markets and AI-only results', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 940);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(
        home: ProDashboard(
          baseUrl: 'http://test.invalid',
          loader: multiMarketLoader,
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Przegląd portfela'), findsOneWidget);
    expect(find.textContaining('PAPER ONLY'), findsOneWidget);

    await tester.tap(find.widgetWithText(OutlinedButton, 'Szczegóły rynku'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 700));

    // CUSDT is not in the configured quote cards: it comes from AI/research.
    expect(find.byKey(const ValueKey('market_BTCUSDT')), findsOneWidget);
    expect(find.byKey(const ValueKey('market_ETHUSDT')), findsOneWidget);
    expect(find.byKey(const ValueKey('market_CUSDT')), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('market_CUSDT')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 700));

    expect(find.textContaining('Jeden autonomiczny rachunek AI'), findsOneWidget);
    expect(find.textContaining('HISTORIA TEGO RYNKU'), findsOneWidget);
    expect(find.textContaining('Zrealizowany PnL: +3.50 PLN'), findsOneWidget);
    expect(find.textContaining('LEGACY'), findsNothing);
  });
}
