import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:al_trading_dashboard/main.dart';
import 'package:al_trading_dashboard/pro_dashboard.dart';

void main() {
  testWidgets('professional paper dashboard starts', (
    WidgetTester tester,
  ) async {
    Future<Map<String, dynamic>> loader() async {
      return <String, dynamic>{
        'assets': <Map<String, dynamic>>[
          <String, dynamic>{
            'symbol': 'BTCUSDT',
            'name': 'Bitcoin',
            'asset_type': 'crypto',
            'state_available': true,
            'market_price': 60000.0,
            'quote': 'USDT',
            'net_profit': 0.0,
            'net_profit_pln': 0.0,
            'position': 'FLAT',
            'pln': <String, dynamic>{'available': true, 'path': 'TEST→PLN'},
          },
        ],
        'research': <String, dynamic>{
          'available': true,
          'stale': false,
          'opportunities': <dynamic>[],
          'selected_by_class': <String, dynamic>{},
          'available_by_class': <String, dynamic>{},
          'macro_events': <dynamic>[],
          'errors': <String, dynamic>{},
        },
        'ai': <String, dynamic>{
          'available': true,
          'stale': false,
          'initial_balance': 1000.0,
          'balance': 1000.0,
          'equity': 1000.0,
          'realized_pnl': 0.0,
          'unrealized_pnl': 0.0,
          'position': null,
          'trades': <dynamic>[],
          'decisions': <dynamic>[],
        },
        'user_portfolio': <String, dynamic>{
          'available': true,
          'balance': 0.0,
          'total_deposited': 0.0,
          'total_withdrawn': 0.0,
        },
      };
    }

    await tester.pumpWidget(
      MaterialApp(
        home: ProDashboard(
          baseUrl: 'http://test.invalid',
          loader: loader,
          legacyBuilder: (_) => const DashboardPage(liveMode: false),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.byType(ProDashboard), findsOneWidget);
    expect(find.text('Przegląd portfela'), findsOneWidget);
    expect(find.textContaining('PAPER ONLY'), findsOneWidget);
    expect(find.textContaining('TOP 10:'), findsOneWidget);

    expect(tester.takeException(), isNull);
  });

  testWidgets('legacy market details dashboard still starts', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: DashboardPage(liveMode: false)),
    );

    await tester.pump();

    expect(find.byType(DashboardPage), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
