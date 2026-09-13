import 'package:flutter/material.dart';

class AiPanel extends StatelessWidget {
  final Map<String, dynamic>? data;
  final String? error;
  final ValueChanged<String> onSelectAsset;
  final bool followSelection;
  final ValueChanged<bool>? onFollowChanged;

  const AiPanel({
    super.key,
    this.data,
    this.error,
    required this.onSelectAsset,
    this.followSelection = false,
    this.onFollowChanged,
  });

  @override
  Widget build(BuildContext context) {
    final available = data?['available'] == true;
    final stale = data?['stale'] == true || error != null;
    final decision = data?['decision'] as Map? ?? {};
    final position = data?['position'] as Map?;
    final symbol = (position?['symbol'] ?? decision['symbol']) as String?;
    final strategies = {
      'trend': 'Podążanie za trendem',
      'mean_reversion': 'Powrót do średniej',
      'breakout': 'Wybicie',
    };
    final actions = {
      'SELECT': 'Wybrano aktywo — oczekiwanie na wejście',
      'HOLD': 'Utrzymywanie pozycji',
      'WAIT': 'Oczekiwanie na świecę',
      'CASH': 'Pozostaje w gotówce',
      'HALT': 'Handel wstrzymany: limit ryzyka',
    };
    final ranking = data?['ranking'] as List? ?? [];
    final issues = data?['data_issues'] as Map? ?? {};
    final trades = data?['trades'] as List? ?? [];
    final decisions = data?['decisions'] as List? ?? [];
    final equity = (data?['equity'] as num?)?.toDouble() ?? 1000;
    final realized = (data?['realized_pnl'] as num?)?.toDouble() ?? equity - 1000;
    final unrealized =
        (data?['unrealized_pnl'] as num?)?.toDouble() ?? 0;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'AI · PORTFEL TRENINGOWY',
              style: TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              !available
                  ? 'AI oczekuje na pierwszy cykl lub aktualizację serwera.'
                  : stale
                  ? 'Dane AI są nieaktualne — sprawdź usługę na serwerze.'
                  : actions[decision['action']] ?? 'Oczekiwanie na decyzję',
            ),
            if (available) ...[
              const SizedBox(height: 8),
              Text(
                'Kapitał: ${equity.toStringAsFixed(2)} jedn. symulacji '
                '• Wynik: ${(equity - 1000).toStringAsFixed(2)}',
              ),
              Text(
                'Zrealizowany: ${realized.toStringAsFixed(2)} '
                '• Otwarta pozycja: ${unrealized.toStringAsFixed(2)}',
              ),
              Text(decision['reason']?.toString() ?? ''),
              if (symbol != null)
                Text(
                  '$symbol · ${strategies[position?['strategy'] ?? decision['strategy']] ?? ''}',
                ),
              if (symbol != null && !stale)
                TextButton(
                  onPressed: () => onSelectAsset(symbol),
                  child: const Text('Pokaż aktywo AI'),
                ),
              Text(
                'Ocenione pary aktywo/strategia: ${ranking.length} '
                '• Pominięte rynki: ${issues.length}',
              ),
              if (issues.isNotEmpty)
                Text(
                  issues.entries.map((e) => '${e.key}: ${e.value}').join('\n'),
                ),
              if (ranking.isNotEmpty)
                ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  title: const Text('Ranking i walidacja'),
                  children: ranking.take(9).map((raw) {
                    final row = raw as Map;
                    final score = (row['score'] as num).toDouble() * 100;
                    return ListTile(
                      dense: true,
                      title: Text(
                        '${row['symbol']} · ${strategies[row['strategy']]}',
                      ),
                      subtitle: Text(
                        'Ocena netto: ${score.toStringAsFixed(3)}% '
                        '• Próby walidacyjne: ${row['validation_trades']} '
                        '• ${row['eligible'] == true ? 'spełnia warunki' : 'pominięto'}',
                      ),
                    );
                  }).toList(),
                ),
            ],
            if (onFollowChanged != null)
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Śledź wybór AI na wykresie'),
                value: followSelection,
                onChanged: onFollowChanged,
              ),
            if (trades.isNotEmpty)
              ExpansionTile(
                title: const Text('Transakcje portfela AI'),
                children: trades.reversed.take(10).map((raw) {
                  final trade = raw as Map;
                  return ListTile(
                    title: Text(
                      '${trade['symbol']} · ${strategies[trade['strategy']]}',
                    ),
                    subtitle: Text(
                      'Wynik po kosztach: '
                      '${(trade['profit'] as num).toStringAsFixed(2)} jedn. '
                      '· ${trade['reason']}',
                    ),
                  );
                }).toList(),
              ),
            if (decisions.isNotEmpty)
              ExpansionTile(
                title: const Text('Ostatnie decyzje AI'),
                children: decisions.reversed.take(10).map((raw) {
                  final item = raw as Map;
                  final at = DateTime.fromMillisecondsSinceEpoch(
                    (item['timestamp'] as num).toInt(),
                    isUtc: true,
                  ).toLocal();
                  return ListTile(
                    title: Text(
                      '${at.toString().substring(0, 19)} · '
                      '${item['symbol'] ?? 'Gotówka'}',
                    ),
                    subtitle: Text(item['reason']?.toString() ?? ''),
                  );
                }).toList(),
              ),
            const SizedBox(height: 8),
            const Text(
              'Model k-NN • 3 strategie • tylko symulacja kupna. '
              'Osobny portfel 1000 jednostek, pozycja do 20%, stop 1%, '
              'limit dzienny 20 jednostek, limit obsunięcia 5%. '
              'Limity nie gwarantują maksymalnej straty. '
              'USD/USDT i ceny złota/ropy są indeksami do ćwiczeń, nie saldem PLN. '
              'Wyniki historyczne nie gwarantują przyszłych zysków.',
              style: TextStyle(color: Colors.white60, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}
