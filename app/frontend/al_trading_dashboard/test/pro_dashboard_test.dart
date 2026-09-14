import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:al_trading_dashboard/pro_dashboard.dart';

Map<String, dynamic> sample(double reserve) => {
  'last_cycle': DateTime.now().toUtc().toIso8601String(),
  'assets': <String, dynamic>{},
  'fx': {'received_at': DateTime.now().millisecondsSinceEpoch},
  'virtual_broker': {
    'currency': 'PLN',
    'balance': 1000,
    'equity': 1000,
    'initial_balance': 1000,
    'free_cash': 1000,
    'realized_profit': reserve,
    'positions': <String, dynamic>{},
    'user_portfolio': {'balance': reserve},
  },
};

void main() {
  for (final width in [390.0, 1440.0]) {
    testWidgets('PLN wallet refreshes at width $width', (tester) async {
      tester.view.physicalSize = Size(width, 1800);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      var calls = 0;
      await tester.pumpWidget(
        MaterialApp(
          home: ProDashboard(
            baseUrl: '',
            loader: () async => sample(++calls * 25),
          ),
        ),
      );
      await tester.pump();
      expect(find.text('Mój portfel • zł'), findsOneWidget);
      expect(find.text('25.00'), findsOneWidget);
      await tester.pump(const Duration(seconds: 5));
      await tester.pump();
      expect(find.text('50.00'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    });
  }
  testWidgets('connection error preserves wallet and recovers', (tester) async {
    var fail = false;
    await tester.pumpWidget(
      MaterialApp(
        home: ProDashboard(
          baseUrl: '',
          loader: () async {
            if (fail) throw Exception('offline');
            return sample(75);
          },
        ),
      ),
    );
    await tester.pump();
    fail = true;
    await tester.pump(const Duration(seconds: 5));
    await tester.pump();
    expect(find.textContaining('offline'), findsOneWidget);
    expect(find.text('75.00'), findsOneWidget);
    fail = false;
    await tester.pump(const Duration(seconds: 5));
    await tester.pump();
    expect(find.textContaining('offline'), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });
}
