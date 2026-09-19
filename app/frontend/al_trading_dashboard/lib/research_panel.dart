import 'package:flutter/material.dart';

class ResearchPanel extends StatelessWidget {
  final Map<String, dynamic>? data;
  final String? error;

  const ResearchPanel({super.key, this.data, this.error});

  String pct(dynamic value) {
    if (value is! num) return '—';
    return '${(value.toDouble() * 100).toStringAsFixed(3)}%';
  }

  String score(dynamic value) {
    if (value is! num) return '—';
    return value.toDouble().toStringAsFixed(4);
  }

  @override
  Widget build(BuildContext context) {
    final available = data?['available'] == true;
    final stale = data?['stale'] == true;
    final opportunities = data?['opportunities'] as List? ?? const [];
    final macro = data?['macro_events'] as List? ?? const [];
    final universe = data?['universe_count'] ?? 0;
    final updated = data?['updated_at']?.toString();
    final errors = data?['errors'] as Map? ?? const {};

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'AUTONOMICZNY RESEARCH · TOP 10',
                    style: TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
                  ),
                ),
                Icon(
                  available && !stale ? Icons.cloud_done : Icons.cloud_off,
                  color: available && !stale
                      ? Colors.greenAccent
                      : Colors.orangeAccent,
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              'Prawdziwe dane rynkowe i makro · pieniądze wyłącznie wirtualne · '
              'realne zlecenia: 0',
              style: const TextStyle(color: Colors.white60),
            ),
            if (error != null) ...[
              const SizedBox(height: 8),
              Text(error!, style: const TextStyle(color: Colors.redAccent)),
            ],
            if (!available) ...[
              const SizedBox(height: 12),
              const Text('Oczekiwanie na pierwszy pełny cykl research.'),
            ] else ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 18,
                runSpacing: 8,
                children: [
                  Text('Skanowany universu: $universe'),
                  Text('Wybrane: ${opportunities.length}/10'),
                  Text(stale ? 'Status: STALE' : 'Status: LIVE'),
                  if (updated != null) Text('Aktualizacja: $updated'),
                ],
              ),
              const SizedBox(height: 14),
              if (opportunities.isNotEmpty)
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: DataTable(
                    columns: const [
                      DataColumn(label: Text('#')),
                      DataColumn(label: Text('Aktywo')),
                      DataColumn(label: Text('Strategia')),
                      DataColumn(label: Text('Ocena')),
                      DataColumn(label: Text('Prognoza netto')),
                      DataColumn(label: Text('Walidacja')),
                      DataColumn(label: Text('Pamięć')),
                    ],
                    rows: opportunities.asMap().entries.map((entry) {
                      final row = Map<String, dynamic>.from(entry.value as Map);
                      final memory = row['memory'] as Map? ?? const {};
                      return DataRow(
                        cells: [
                          DataCell(Text('${entry.key + 1}')),
                          DataCell(Text(row['symbol']?.toString() ?? '—')),
                          DataCell(Text(row['strategy']?.toString() ?? '—')),
                          DataCell(Text(score(row['combined_score']))),
                          DataCell(Text(pct(row['expected_net_return']))),
                          DataCell(Text('${row['validation_trades'] ?? 0}')),
                          DataCell(Text('${memory['samples'] ?? 0} próbek')),
                        ],
                      );
                    }).toList(),
                  ),
                ),
              const SizedBox(height: 16),
              const Text(
                'OSTATNIE WYDARZENIA MAKRO',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 6),
              if (macro.isEmpty)
                const Text(
                  'Brak nowych komunikatów z podłączonych oficjalnych źródeł.',
                  style: TextStyle(color: Colors.white60),
                )
              else
                ...macro.reversed.take(6).map((raw) {
                  final event = Map<String, dynamic>.from(raw as Map);
                  final tags = (event['tags'] as List? ?? const []).join(', ');
                  return ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.public, size: 18),
                    title: Text(event['title']?.toString() ?? 'Wydarzenie makro'),
                    subtitle: Text(
                      '${event['source'] ?? ''}${tags.isEmpty ? '' : ' · $tags'}',
                    ),
                  );
                }),
              if (errors.values.any((value) => value != null)) ...[
                const SizedBox(height: 10),
                Text(
                  'Ostrzeżenia: ${errors.entries.where((e) => e.value != null).map((e) => '${e.key}: ${e.value}').join(' | ')}',
                  style: const TextStyle(color: Colors.orangeAccent, fontSize: 12),
                ),
              ],
              const SizedBox(height: 10),
              const Text(
                'Ranking to model badawczy, nie gwarancja zysku. Model korzysta z '
                'historycznych świec, walidacji czasowej, kosztów, płynności oraz '
                'ograniczonej pamięci podobnych sytuacji z wcześniejszych logów.',
                style: TextStyle(color: Colors.white54, fontSize: 12),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
