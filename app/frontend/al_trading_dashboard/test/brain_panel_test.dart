import 'package:al_trading_dashboard/brain_panel.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('Brain panel displays observation-only counters and adviser',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: BrainPanel(
              data: {
                'available': true,
                'stale': false,
                'mode': 'PAPER_ONLY',
                'equity': 970.83,
                'shadow': {
                  'summary': {
                    'pending': 2,
                    'open': 1,
                    'stored_trades': 1,
                    'completed_total': 5,
                    'expired_signals': 0,
                    'data_gaps': 0,
                  },
                  'learning': {
                    'trend|LONG': {
                      'trades': 5,
                      'wins': 3,
                      'total_return': 0.01,
                    },
                  },
                  'trades': [
                    {
                      'symbol': 'BTCUSDT',
                      'strategy': 'trend',
                      'side': 'LONG',
                      'counterfactual': true,
                      'reason': 'TIME_EXIT',
                      'return_fraction': 0.001,
                    },
                  ],
                },
                'shadow_advisor': {
                  'trend|LONG': {
                    'status': 'INSUFFICIENT_SAMPLES',
                    'samples': 5,
                    'distinct_symbols': 1,
                    'mean_after_costs': 0.002,
                    'profit_factor': 1.2,
                    'bonus': 0,
                  },
                },
              },
            ),
          ),
        ),
      ),
    );

    expect(find.text('BRAIN v3.5 · SHADOW'), findsOneWidget);
    expect(find.text('OBSERWACJE, NIE ZLECENIA'), findsOneWidget);
    expect(find.text('Zakończone'), findsOneWidget);
    expect(find.text('Shadow Advisor'), findsOneWidget);
    expect(find.text('trend · LONG'), findsOneWidget);
    expect(find.textContaining('Zbieranie próbek'), findsOneWidget);
  });

  testWidgets('Brain panel handles missing shadow state without inventing it',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: BrainPanel(data: {'available': true}),
        ),
      ),
    );
    expect(
      find.text('Oczekiwanie na pierwszy cykl Shadow Ledger w API.'),
      findsOneWidget,
    );
  });
}
