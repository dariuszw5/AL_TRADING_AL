import 'package:flutter/material.dart';

/// Observation-only Brain v3.5. Uses ai data from /api/dashboard-snapshot.
/// Counterfactual returns are fractions, NOT PLN and NOT executed paper trades.
class BrainPanel extends StatelessWidget {
  final Map<String, dynamic>? data;

  const BrainPanel({super.key, required this.data});

  static const ink = Color(0xFF102638);
  static const cyan = Color(0xFF51C8FA);
  static const mint = Color(0xFF39DFAD);
  static const muted = Color(0xFF95AABE);

  Map<String, dynamic> _map(dynamic value) {
    if (value is! Map) return <String, dynamic>{};
    return Map<String, dynamic>.from(
      value.map((key, item) => MapEntry(key.toString(), item)),
    );
  }

  List<Map<String, dynamic>> _rows(dynamic value) {
    if (value is! List) return const <Map<String, dynamic>>[];
    return value.whereType<Map>().map(_map).toList();
  }

  int _int(dynamic v) =>
      v is num ? v.toInt() : int.tryParse(v?.toString() ?? '') ?? 0;

  double? _num(dynamic v) =>
      v is num ? v.toDouble() : double.tryParse(v?.toString() ?? '');

  String _pct(dynamic v, [int digits = 3]) {
    final n = _num(v);
    if (n == null || !n.isFinite) return '—';
    final value = (n * 100).toStringAsFixed(digits) + '%';
    return n > 0 ? '+' + value : value;
  }

  String _pf(dynamic v) {
    final n = _num(v);
    return n == null || !n.isFinite ? '—' : n.toStringAsFixed(2);
  }

  String _status(dynamic v) {
    switch (v?.toString()) {
      case 'SHADOW_CONFIRMED_FOR_RANKING':
        return 'Potwierdzony tylko do rankingu';
      case 'INSUFFICIENT_SAMPLES':
        return 'Zbieranie próbek';
      case 'CONCENTRATED_SAMPLE':
        return 'Zbyt duża koncentracja rynku';
      case 'INCONSISTENT_WINDOWS':
        return 'Niespójne okresy';
      case 'INSUFFICIENT_NET_EDGE':
        return 'Brak przewagi po kosztach';
      default:
        return v?.toString() ?? 'Oczekiwanie na ocenę';
    }
  }

  Widget _metric(String title, int value) => Container(
    constraints: const BoxConstraints(minWidth: 115),
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: cyan.withValues(alpha: 0.06),
      border: Border.all(color: cyan.withValues(alpha: 0.18)),
      borderRadius: BorderRadius.circular(10),
    ),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(color: muted, fontSize: 11)),
        const SizedBox(height: 5),
        Text(
          value.toString(),
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
        ),
      ],
    ),
  );

  Widget _advisorRow(String key, Map<String, dynamic> a) {
    final confirmed = a['status'] == 'SHADOW_CONFIRMED_FOR_RANKING';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            confirmed ? Icons.check_circle_outline : Icons.hourglass_bottom,
            size: 18,
            color: confirmed ? mint : muted,
          ),
          const SizedBox(width: 9),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  key.replaceAll('|', ' · '),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                Text(
                  _status(a['status']) +
                      ' • próbek: ' + _int(a['samples']).toString() +
                      ' • rynków: ' + _int(a['distinct_symbols']).toString() +
                      ' • średnio: ' + _pct(a['mean_after_costs']) +
                      ' • PF: ' + _pf(a['profit_factor']) +
                      ' • premia rankingu: ' + _pct(a['bonus'], 4),
                  style: const TextStyle(fontSize: 11, color: muted, height: 1.4),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _learningRow(String key, Map<String, dynamic> a) {
    final count = _int(a['trades']);
    final total = _num(a['total_return']) ?? 0.0;
    return ListTile(
      dense: true,
      title: Text(key.replaceAll('|', ' · ')),
      subtitle: Text(
        'Obserwacje: ' + count.toString() +
            ' • trafne: ' + _int(a['wins']).toString() +
            ' • średni zwrot netto: ' + _pct(count > 0 ? total / count : null),
        style: const TextStyle(fontSize: 11, color: muted),
      ),
    );
  }

  Widget _tradeRow(Map<String, dynamic> t) {
    final value = _num(t['return_fraction']);
    return ListTile(
      dense: true,
      title: Text(
        (t['symbol']?.toString() ?? '—') + ' · ' +
            (t['strategy']?.toString() ?? '—') + ' · ' +
            (t['side']?.toString() ?? '—'),
      ),
      subtitle: Text(
        (t['reason']?.toString() ?? '—') + ' • transakcja kontrfaktyczna',
        style: const TextStyle(fontSize: 11, color: muted),
      ),
      trailing: Text(
        _pct(value),
        style: TextStyle(
          color: (value ?? 0) >= 0 ? mint : Colors.redAccent,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final ai = _map(data);
    final shadow = _map(ai['shadow']);
    final summary = _map(shadow['summary']);
    final learning = _map(shadow['learning']);
    final advisor = _map(ai['shadow_advisor']);
    final trades = _rows(shadow['trades'])
        .where((t) => t['counterfactual'] == true)
        .toList();
    final historical = _rows(ai['ranking'])
        .where((r) => _int(r['shadow_validation_trades']) > 0)
        .take(6)
        .toList();

    final pending = summary.containsKey('pending')
        ? _int(summary['pending'])
        : _map(shadow['pending']).length;
    final open = summary.containsKey('open')
        ? _int(summary['open'])
        : _map(shadow['positions']).length;
    final completed = summary.containsKey('completed_total')
        ? _int(summary['completed_total'])
        : learning.values.fold<int>(
            0,
            (count, value) => count + _int(_map(value)['trades']),
          );

    return Material(
      color: ink,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: Color(0xFF294152)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Wrap(
            spacing: 8,
            runSpacing: 6,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Icon(Icons.psychology_outlined, color: cyan),
              Text(
                'BRAIN v3.5 · SHADOW',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
              ),
              Chip(
                visualDensity: VisualDensity.compact,
                label: Text('OBSERWACJE, NIE ZLECENIA',
                    style: TextStyle(fontSize: 10)),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'Wyniki są kontrfaktyczne i procentowe. Nie są transakcjami '
            'portfela PAPER_ONLY ani wynikiem finansowym w PLN.',
            style: TextStyle(color: muted, fontSize: 12, height: 1.4),
          ),
          if (ai['stale'] == true)
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text(
                'Dane AI są nieaktualne.',
                style: TextStyle(color: Colors.amber, fontSize: 12),
              ),
            ),
          const SizedBox(height: 14),
          if (ai['available'] != true || shadow.isEmpty)
            const Text(
              'Oczekiwanie na pierwszy cykl Shadow Ledger w API.',
              style: TextStyle(color: muted),
            )
          else ...[
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _metric('Zakończone', completed),
                _metric('W historii', _int(summary['stored_trades'])),
                _metric('Oczekujące', pending),
                _metric('Otwarte shadow', open),
                _metric('Wygasłe', _int(summary['expired_signals'])),
                _metric('Luki danych', _int(summary['data_gaps'])),
              ],
            ),
            const SizedBox(height: 18),
            const Text(
              'Shadow Advisor',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            const Text(
              'Może skorygować wyłącznie kolejność kandydatów wcześniej '
              'dopuszczonych przez model, Supervisor i kontrolę ryzyka.',
              style: TextStyle(color: muted, fontSize: 11, height: 1.4),
            ),
            const SizedBox(height: 10),
            if (advisor.isEmpty)
              const Text(
                'Oczekiwanie na ocenę doradcy.',
                style: TextStyle(color: muted, fontSize: 12),
              )
            else
              for (final a in advisor.entries) _advisorRow(a.key, _map(a.value)),
            if (learning.isNotEmpty) ...[
              const Divider(height: 22, color: Color(0xFF294152)),
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: const Text('Pamięć kierunkowa LONG / SHORT'),
                children: [
                  for (final l in learning.entries)
                    _learningRow(l.key, _map(l.value)),
                ],
              ),
            ],
            if (historical.isNotEmpty)
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: const Text('Historyczna walidacja shadow'),
                subtitle: const Text(
                  'Oddzielna od walidacji dopuszczającej transakcję',
                  style: TextStyle(color: muted, fontSize: 11),
                ),
                children: [
                  for (final r in historical)
                    ListTile(
                      dense: true,
                      title: Text(
                        (r['symbol']?.toString() ?? '—') + ' · ' +
                            (r['strategy']?.toString() ?? '—') + ' · ' +
                            (r['side']?.toString() ?? '—'),
                      ),
                      subtitle: Text(
                        'Prób: ' + _int(r['shadow_validation_trades']).toString() +
                            ' • średnio netto: ' + _pct(r['shadow_validation_mean']) +
                            ' • PF: ' + _pf(r['shadow_validation_profit_factor']),
                        style: const TextStyle(fontSize: 11, color: muted),
                      ),
                    ),
                ],
              ),
            if (trades.isNotEmpty)
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: const Text('Ostatnie obserwacje kontrfaktyczne'),
                subtitle: const Text(
                  'Zwroty procentowe; nie zwiększają ani nie zmniejszają salda PLN',
                  style: TextStyle(color: muted, fontSize: 11),
                ),
                children: [
                  for (final trade in trades.reversed.take(8))
                    _tradeRow(trade),
                ],
              ),
          ],
        ],
        ),
      ),
    );
  }
}
