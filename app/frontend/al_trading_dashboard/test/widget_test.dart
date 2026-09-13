import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:al_trading_dashboard/main.dart';
import 'package:al_trading_dashboard/ai_panel.dart';

void main() {
  testWidgets('AL Trading Agent dashboard starts', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: DashboardPage(liveMode: false)),
    );

    await tester.pump();

    expect(find.text('AL TRADING AGENT'), findsOneWidget);
    expect(find.text('KONTO'), findsOneWidget);
    // On a narrow screen the account cards push the position below the viewport.
    await tester.scrollUntilVisible(
      find.text('FLAT'),
      200,
      scrollable: find
          .descendant(
            of: find.byType(ListView),
            matching: find.byType(Scrollable),
          )
          .first,
    );
    expect(find.text('FLAT'), findsOneWidget);
    expect(find.text('POZYCJA'), findsOneWidget);
  });

  testWidgets('asset selector changes the selected paper market', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: DashboardPage(liveMode: false)),
    );

    await tester.pump();

    expect(find.text('BTCUSDT'), findsWidgets);

    await tester.tap(find.byType(DropdownButton<String>));
    await tester.pumpAndSettle();

    expect(find.text('ETHUSDT'), findsWidgets);

    await tester.tap(find.text('ETHUSDT').last);
    await tester.pump();

    expect(find.text('ETHUSDT'), findsWidgets);
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('AI panel opens its selected asset and marks stale data', (
    tester,
  ) async {
    String? selected;
    final data = <String, dynamic>{
      'available': true,
      'stale': false,
      'equity': 999.5,
      'decision': {
        'action': 'SELECT',
        'symbol': 'ETHUSDT',
        'strategy': 'trend',
      },
    };
    Widget panel() => MaterialApp(
      home: Scaffold(
        body: SingleChildScrollView(
          child: AiPanel(
            data: data,
            onSelectAsset: (symbol) => selected = symbol,
          ),
        ),
      ),
    );
    await tester.pumpWidget(panel());
    await tester.tap(find.text('Pokaż aktywo AI'));
    expect(selected, 'ETHUSDT');
    expect(find.textContaining('999.50'), findsOneWidget);
    data['stale'] = true;
    await tester.pumpWidget(panel());
    expect(find.text('Pokaż aktywo AI'), findsNothing);
    expect(find.textContaining('nieaktualne'), findsOneWidget);
  });

  testWidgets('AI missing endpoint does not promise an active model', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: AiPanel(onSelectAsset: (_) {})),
      ),
    );
    expect(find.textContaining('pierwszy cykl'), findsOneWidget);
    expect(find.text('Pokaż aktywo AI'), findsNothing);
  });
}
