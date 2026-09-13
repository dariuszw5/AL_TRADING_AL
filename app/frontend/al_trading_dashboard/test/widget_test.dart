import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:al_trading_dashboard/main.dart';

void main() {
  testWidgets(
    'AL Trading Agent dashboard starts',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: DashboardPage(liveMode: false),
        ),
      );

      await tester.pump();

      expect(find.text('AL TRADING AGENT'), findsOneWidget);
      expect(find.text('FLAT'), findsOneWidget);
      expect(find.text('KONTO'), findsOneWidget);
      expect(find.text('POZYCJA'), findsOneWidget);
    },
  );
}

