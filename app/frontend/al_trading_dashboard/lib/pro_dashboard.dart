import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'research_panel.dart';

const ink = Color(0xFF071522);
const panel = Color(0xFF102638);
const cyan = Color(0xFF51C8FA);
const mint = Color(0xFF39DFAD);
const muted = Color(0xFF95AABE);

class ProDashboard extends StatefulWidget {
  final String baseUrl;
  final Future<Map<String, dynamic>> Function()? loader;
  final WidgetBuilder? legacyBuilder;

  const ProDashboard({
    super.key,
    required this.baseUrl,
    this.loader,
    this.legacyBuilder,
  });

  @override
  State<ProDashboard> createState() => _ProDashboardState();
}

class _ProDashboardState extends State<ProDashboard> {
  List<Map<String, dynamic>> assets = [];
  Map<String, dynamic>? research;
  Map<String, dynamic>? ai;
  Map<String, dynamic>? userPortfolio;
  String? failure;
  DateTime? received;
  Timer? timer;
  bool busy = false;
  int page = 0;
  String query = '';

  final labels = const [
    'Portfel',
    'Rynki',
    'Research TOP 10',
    'Aktywność AI',
    'Historia',
  ];

  final icons = const [
    Icons.account_balance_wallet_outlined,
    Icons.bar_chart,
    Icons.travel_explore,
    Icons.psychology_outlined,
    Icons.history,
  ];

  @override
  void initState() {
    super.initState();
    refresh();
    timer = Timer.periodic(const Duration(seconds: 5), (_) => refresh());
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  Map<String, dynamic> asMap(dynamic value) {
    if (value is! Map) return <String, dynamic>{};
    return Map<String, dynamic>.from(value);
  }

  List<dynamic> asList(dynamic value) {
    if (value is! List) return const [];
    return value;
  }

  Future<dynamic> getJson(String path) async {
    final original = Uri.parse('${widget.baseUrl}$path');
    final params = Map<String, String>.from(original.queryParameters);
    params['_ts'] = DateTime.now().millisecondsSinceEpoch.toString();
    final uri = original.replace(queryParameters: params);

    final response = await http
        .get(
          uri,
          headers: const {
            'Cache-Control': 'no-cache, no-store, max-age=0',
            'Pragma': 'no-cache',
            'Connection': 'close',
          },
        )
        .timeout(const Duration(seconds: 15));

    if (response.statusCode != 200) {
      throw Exception('HTTP ${response.statusCode} dla $path');
    }
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> safeGet(String key, String path) async {
    try {
      return {
        'key': key,
        'ok': true,
        'value': await getJson(path),
      };
    } catch (error) {
      return {
        'key': key,
        'ok': false,
        'error': error.toString(),
      };
    }
  }

  Future<void> refresh() async {
    if (busy) return;
    busy = true;

    try {
      if (widget.loader != null) {
        final combined = await widget.loader!();
        final rawAssets = asList(combined['assets']);
        if (!mounted) return;
        setState(() {
          assets = rawAssets
              .whereType<Map>()
              .map((row) => Map<String, dynamic>.from(row))
              .toList();
          research = asMap(combined['research']);
          ai = asMap(combined['ai']);
          userPortfolio = asMap(combined['user_portfolio']);
          received = DateTime.now();
          failure = null;
        });
        return;
      }

      final results = await Future.wait([
        safeGet('assets', '/api/assets'),
        safeGet('research', '/api/research'),
        safeGet('ai', '/api/ai'),
        safeGet('portfolio', '/api/user-portfolio'),
      ]);

      final byKey = {
        for (final row in results) row['key'].toString(): row,
      };
      final errors = results
          .where((row) => row['ok'] != true)
          .map((row) => '${row['key']}: ${row['error']}')
          .toList();

      if (!mounted) return;
      setState(() {
        final assetsRow = byKey['assets'];
        if (assetsRow?['ok'] == true) {
          assets = asList(assetsRow?['value'])
              .whereType<Map>()
              .map((row) => Map<String, dynamic>.from(row))
              .toList();
        }

        final researchRow = byKey['research'];
        if (researchRow?['ok'] == true) {
          research = asMap(researchRow?['value']);
        }

        final aiRow = byKey['ai'];
        if (aiRow?['ok'] == true) {
          ai = asMap(aiRow?['value']);
        }

        final portfolioRow = byKey['portfolio'];
        if (portfolioRow?['ok'] == true) {
          userPortfolio = asMap(portfolioRow?['value']);
        }

        received = DateTime.now();
        failure = errors.isEmpty ? null : errors.join(' • ');
      });
    } finally {
      busy = false;
    }
  }

  bool get stale {
    return research?['stale'] == true;
  }

  String number(dynamic value, [int digits = 2]) {
    return value is num ? value.toDouble().toStringAsFixed(digits) : '—';
  }

  String signed(dynamic value, [int digits = 2]) {
    if (value is! num) return '—';
    final numberValue = value.toDouble();
    return '${numberValue >= 0 ? '+' : ''}${numberValue.toStringAsFixed(digits)}';
  }

  String classLabel(dynamic value) {
    switch (value?.toString()) {
      case 'crypto':
        return 'CRYPTO';
      case 'equity':
        return 'AKCJE';
      case 'etf':
        return 'ETF';
      case 'forex':
        return 'FOREX';
      case 'index':
        return 'INDEKS';
      case 'commodity':
        return 'SUROWCE';
      default:
        return value?.toString().toUpperCase() ?? '—';
    }
  }

  Widget box(Widget child) => Container(
    padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(
      color: panel,
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: const Color(0xFF243E52)),
    ),
    child: child,
  );

  Widget heading(String title, [String? detail]) => Padding(
    padding: const EdgeInsets.only(bottom: 18),
    child: Row(
      children: [
        Expanded(
          child: Text(
            title,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          ),
        ),
        if (detail != null)
          Text(detail, style: const TextStyle(color: muted, fontSize: 12)),
      ],
    ),
  );

  Widget stat(
    String title,
    String value,
    IconData icon, {
    Color? color,
    String? detail,
  }) => box(
    Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: cyan, size: 23),
        const SizedBox(height: 14),
        Text(title, style: const TextStyle(color: muted)),
        const SizedBox(height: 8),
        Text(
          value,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
        if (detail != null) ...[
          const SizedBox(height: 6),
          Text(detail, style: const TextStyle(color: muted, fontSize: 11)),
        ],
      ],
    ),
  );

  List<Map<String, dynamic>> get opportunities =>
      asList(research?['opportunities'])
          .whereType<Map>()
          .map((row) => Map<String, dynamic>.from(row))
          .toList();

  Map<String, dynamic>? opportunityFor(String symbol) {
    for (final row in opportunities) {
      if (row['symbol']?.toString() == symbol) return row;
    }
    return null;
  }

  int? opportunityRank(String symbol) {
    final rows = opportunities;
    final index = rows.indexWhere((row) => row['symbol']?.toString() == symbol);
    return index < 0 ? null : index + 1;
  }

  Widget summary() {
    final aiState = ai ?? const <String, dynamic>{};
    final initial = (aiState['initial_balance'] as num?)?.toDouble() ?? 0.0;
    final equity = (aiState['equity'] as num?)?.toDouble() ?? 0.0;
    final realized = (aiState['realized_pnl'] as num?)?.toDouble() ?? 0.0;
    final unrealized = (aiState['unrealized_pnl'] as num?)?.toDouble() ?? 0.0;
    final result = realized + unrealized;
    final positions = asMap(aiState['positions']);
    final portfolioBalance =
        (userPortfolio?['balance'] as num?)?.toDouble() ?? 0.0;
    final classes = asMap(research?['selected_by_class']).length;

    final cards = <Widget>[
      stat(
        'Kapitał AI',
        '${number(equity)} PLN',
        Icons.account_balance_wallet_outlined,
        detail: initial <= 0
            ? 'Najpierw przekaż środki z portfela'
            : 'Wpłacony kapitał: ${number(initial)} PLN',
      ),
      stat(
        'Wynik AI',
        '${signed(result)} PLN',
        Icons.trending_up,
        color: result >= 0 ? mint : Colors.redAccent,
        detail:
            'Zamknięty ${signed(realized)} • otwarty ${signed(unrealized)}',
      ),
      stat(
        'Pozycje AI',
        positions.isEmpty ? 'FLAT' : '${positions.length} OTWARTE',
        Icons.layers_outlined,
        color: positions.isEmpty ? muted : cyan,
        detail: positions.isEmpty
            ? (aiState['decision'] is Map
                  ? asMap(aiState['decision'])['action']?.toString()
                  : 'Brak otwartych pozycji')
            : positions.keys.take(4).join(' • '),
      ),
      stat(
        'Mój portfel',
        '${number(portfolioBalance)} PLN',
        Icons.savings_outlined,
        detail: 'Wirtualne środki oczekujące na decyzję użytkownika',
      ),
      stat(
        'Research TOP 10',
        '${opportunities.length}/10',
        Icons.travel_explore,
        detail: '$classes aktywnych klas w TOP 10',
      ),
      stat(
        'Status',
        stale ? 'STALE' : 'LIVE',
        stale ? Icons.cloud_off : Icons.cloud_done,
        color: stale ? Colors.amber : mint,
        detail: 'Realne dane • wyłącznie wirtualne zlecenia',
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 1200
            ? 3
            : constraints.maxWidth >= 760
            ? 2
            : 1;
        final width = (constraints.maxWidth - (columns - 1) * 12) / columns;
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            for (final child in cards) SizedBox(width: width, child: child),
          ],
        );
      },
    );
  }

  String assetBadge(String symbol) {
    const badges = <String, String>{
      'BTCUSDT': '₿',
      'ETHUSDT': 'Ξ',
      'SOLUSDT': '◎',
      'BNBUSDT': '◈',
      'XRPUSDT': '✕',
      'EURUSD': '€',
      'GBPUSD': '£',
      'USDJPY': '¥',
      'AAPL': 'A',
      'MSFT': 'M',
      'NVDA': 'N',
      'TSLA': 'T',
      'SPY': 'S',
      'QQQ': 'Q',
    };
    return badges[symbol] ?? (symbol.isEmpty ? '?' : symbol.substring(0, 1));
  }

  Widget fundsDonut() {
    final aiState = ai ?? const <String, dynamic>{};
    final positions = asMap(aiState['positions']);
    final wallet =
        (userPortfolio?['balance'] as num?)?.toDouble() ?? 0.0;
    final aiCash = (aiState['balance'] as num?)?.toDouble() ?? 0.0;
    final funded =
        (aiState['funded_capital'] as num?)?.toDouble() ?? 0.0;
    final equity = (aiState['equity'] as num?)?.toDouble() ?? 0.0;
    final swept =
        (userPortfolio?['profit_transferred'] as num?)?.toDouble() ?? 0.0;

    var positionsValue = 0.0;
    for (final raw in positions.values) {
      final p = asMap(raw);
      final allocation =
          (p['allocation_pln'] as num?)?.toDouble() ?? 0.0;
      final unrealized =
          (p['unrealized_pnl'] as num?)?.toDouble() ?? 0.0;
      positionsValue += math.max(0.0, allocation + unrealized);
    }

    final values = <double>[
      math.max(0.0, wallet),
      math.max(0.0, aiCash),
      math.max(0.0, positionsValue),
    ];
    final total = values.fold<double>(0.0, (sum, value) => sum + value);
    final loss = math.max(0.0, funded - equity);

    final labels = <String>[
      'Mój portfel',
      'Wolne AI',
      'Pozycje AI',
    ];
    final colors = <Color>[
      cyan,
      mint,
      const Color(0xFF9C7CFF),
    ];

    Widget legendRow(int index) {
      final value = values[index];
      final pct = total <= 0 ? 0.0 : value / total * 100;
      return Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          children: [
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: colors[index],
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                labels[index],
                style: const TextStyle(color: muted, fontSize: 12),
              ),
            ),
            Text(
              '${number(value)} PLN • ${pct.toStringAsFixed(1)}%',
              style: const TextStyle(fontSize: 12),
            ),
          ],
        ),
      );
    }

    return box(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          heading(
            'Podział środków',
            'Portfel użytkownika • wolna gotówka AI • aktywne pozycje',
          ),
          Row(
            children: [
              SizedBox(
                width: 170,
                height: 170,
                child: CustomPaint(
                  painter: FundsDonutPainter(
                    values: values,
                    colors: colors,
                  ),
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '${number(total)} PLN',
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const Text(
                          'łącznie',
                          style: TextStyle(color: muted, fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 20),
              Expanded(
                child: Column(
                  children: [
                    for (int i = 0; i < values.length; i++) legendRow(i),
                    const Divider(color: Color(0xFF294152)),
                    _miniMetric('Wpłacono do AI', funded),
                    _miniMetric('Zysk przelany', swept),
                    _miniMetric('Strata AI', loss),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _miniMetric(String label, double value) {
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: muted, fontSize: 12),
            ),
          ),
          Text(
            '${number(value)} PLN',
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  Widget marketTickerStrip() {
    final rows = assets.where((asset) => asset['market_price'] is num).toList()
      ..sort((a, b) {
        final aOpen = (a['position']?.toString() ?? 'FLAT') != 'FLAT';
        final bOpen = (b['position']?.toString() ?? 'FLAT') != 'FLAT';
        if (aOpen != bOpen) return aOpen ? -1 : 1;
        final ar = opportunityRank(a['symbol']?.toString() ?? '') ?? 9999;
        final br = opportunityRank(b['symbol']?.toString() ?? '') ?? 9999;
        return ar.compareTo(br);
      });

    final shown = rows.take(14).toList();

    return box(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          heading('Notowania', 'Szybki podgląd naszych aktywów'),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final asset in shown)
                Builder(
                  builder: (context) {
                    final symbol = asset['symbol']?.toString() ?? '';
                    final price =
                        (asset['market_price'] as num?)?.toDouble();
                    final position =
                        asset['position']?.toString() ?? 'FLAT';
                    final digits =
                        price != null && price.abs() < 10 ? 5 : 2;
                    return Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFF102534),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: position == 'FLAT'
                              ? const Color(0xFF294152)
                              : mint,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          CircleAvatar(
                            radius: 13,
                            backgroundColor: const Color(0xFF23485F),
                            child: Text(
                              assetBadge(symbol),
                              style: const TextStyle(
                                color: cyan,
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                symbol,
                                style: const TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              Text(
                                price == null
                                    ? '—'
                                    : '${number(price, digits)} ${asset['quote'] ?? ''}',
                                style: const TextStyle(
                                  color: muted,
                                  fontSize: 10,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    );
                  },
                ),
            ],
          ),
        ],
      ),
    );
  }

  List<double> aiEquityValues() {
    final aiState = ai ?? const <String, dynamic>{};
    final initial = (aiState['initial_balance'] as num?)?.toDouble() ?? 0.0;
    final values = <double>[initial];
    var running = initial;
    for (final raw in asList(aiState['trades'])) {
      if (raw is! Map) continue;
      final profit = raw['profit'];
      if (profit is! num) continue;
      running += profit.toDouble();
      values.add(running);
    }
    final current = (aiState['equity'] as num?)?.toDouble();
    if (current != null && (current - values.last).abs() > 0.000001) {
      values.add(current);
    }
    return values;
  }

  Widget equityChart() {
    final values = aiEquityValues();
    return box(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          heading('Kapitał AI', 'Historia zamknięć + bieżąca wycena'),
          if (values.length < 2)
            const SizedBox(
              height: 220,
              child: Center(
                child: Text(
                  'Oczekiwanie na pierwszą zmianę kapitału',
                  style: TextStyle(color: muted),
                ),
              ),
            )
          else ...[
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Min. ${number(values.reduce(math.min))}',
                  style: const TextStyle(color: muted),
                ),
                Text(
                  'Maks. ${number(values.reduce(math.max))}',
                  style: const TextStyle(color: muted),
                ),
              ],
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 220,
              width: double.infinity,
              child: CustomPaint(painter: EquityPainter(values)),
            ),
            const SizedBox(height: 10),
            const Text(
              'Kapitał i PnL konta AI są prowadzone w wirtualnych PLN. Notowania pozostają realne.',
              style: TextStyle(color: muted, fontSize: 12),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> changeUserFunds({required bool deposit}) async {
    final controller = TextEditingController();
    final amount = await showDialog<double>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(deposit ? 'Wpłata wirtualna PLN' : 'Wypłata wirtualna PLN'),
        content: TextField(
          controller: controller,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Kwota PLN'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Anuluj'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(
              context,
              double.tryParse(controller.text.replaceAll(',', '.')),
            ),
            child: const Text('Zapisz'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (amount == null || amount <= 0) return;

    final path = deposit
        ? '/api/user-portfolio/deposit'
        : '/api/user-portfolio/withdraw';
    try {
      final response = await http
          .post(
            Uri.parse('${widget.baseUrl}$path'),
            headers: const {
              'content-type': 'application/json',
              'Connection': 'close',
            },
            body: jsonEncode({'amount': amount}),
          )
          .timeout(const Duration(seconds: 15));
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw Exception('HTTP ${response.statusCode}: ${response.body}');
      }
      await refresh();
    } catch (error) {
      if (!mounted) return;
      setState(() => failure = 'Portfel: $error');
    }
  }

  Future<void> fundAi() async {
    final controller = TextEditingController();
    final amount = await showDialog<double>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Przekaż wirtualne PLN do AI'),
        content: TextField(
          controller: controller,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          autofocus: true,
          decoration: InputDecoration(
            labelText: 'Kwota PLN',
            helperText:
                'Dostępne: ${number(userPortfolio?['balance'])} PLN',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Anuluj'),
          ),
          FilledButton.icon(
            onPressed: () => Navigator.pop(
              context,
              double.tryParse(controller.text.replaceAll(',', '.')),
            ),
            icon: const Icon(Icons.play_arrow),
            label: const Text('WYKONAJ'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (amount == null || amount <= 0) return;

    try {
      final response = await http
          .post(
            Uri.parse('${widget.baseUrl}/api/ai/fund'),
            headers: const {
              'content-type': 'application/json',
              'Connection': 'close',
            },
            body: jsonEncode({'amount': amount}),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw Exception('HTTP ${response.statusCode}: ${response.body}');
      }

      await refresh();

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Przekazano ${amount.toStringAsFixed(2)} PLN do konta AI. '
            'Agent zastosuje środki w najbliższym cyklu.',
          ),
        ),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() => failure = 'Transfer do AI: $error');
    }
  }

  Widget portfolioActions() {
    final aiState = ai ?? const <String, dynamic>{};
    final aiBalance = (aiState['balance'] as num?)?.toDouble() ?? 0.0;
    final aiEquity = (aiState['equity'] as num?)?.toDouble() ?? 0.0;
    final aiRealized = (aiState['realized_pnl'] as num?)?.toDouble() ?? 0.0;
    final aiUnrealized =
        (aiState['unrealized_pnl'] as num?)?.toDouble() ?? 0.0;
    final positions = asMap(aiState['positions']);
    final decision = asMap(aiState['decision']);

    return box(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          heading('Mój portfel PLN', 'Wirtualne środki użytkownika'),
          Text(
            'Saldo: ${number(userPortfolio?['balance'])} PLN',
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 6),
          Text(
            'Wpłaty: ${number(userPortfolio?['total_deposited'])} PLN • '
            'Wypłaty: ${number(userPortfolio?['total_withdrawn'])} PLN • '
            'Do AI: ${number(userPortfolio?['transferred_to_ai'])} PLN',
            style: const TextStyle(color: muted),
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              FilledButton.icon(
                onPressed: () => changeUserFunds(deposit: true),
                icon: const Icon(Icons.add),
                label: const Text('Wpłać'),
              ),
              OutlinedButton.icon(
                onPressed: () => changeUserFunds(deposit: false),
                icon: const Icon(Icons.remove),
                label: const Text('Wypłać'),
              ),
              FilledButton.icon(
                onPressed:
                    ((userPortfolio?['balance'] as num?)?.toDouble() ?? 0.0) > 0
                    ? fundAi
                    : null,
                icon: const Icon(Icons.play_arrow),
                label: const Text('WYKONAJ • PRZEKAŻ DO AI'),
              ),
            ],
          ),
          const Divider(height: 34, color: Color(0xFF294152)),
          heading('Konto AI', 'Autonomiczny paper trading'),
          Text(
            'Gotówka: ${number(aiBalance)} PLN',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 4),
          Text(
            'Equity: ${number(aiEquity)} PLN • '
            'PnL otwarty: ${signed(aiUnrealized)} PLN • '
            'PnL zamknięty: ${signed(aiRealized)} PLN',
            style: const TextStyle(color: muted),
          ),
          const SizedBox(height: 8),
          Text(
            positions.isEmpty
                ? 'Pozycje: FLAT • ${decision['action'] ?? 'WAIT'}'
                : 'Otwarte pozycje: ${positions.length}',
            style: TextStyle(
              color: positions.isEmpty ? muted : mint,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (positions.isNotEmpty) ...[
            const SizedBox(height: 8),
            for (final entry in positions.entries)
              Builder(
                builder: (context) {
                  final p = asMap(entry.value);
                  final pnl =
                      (p['unrealized_pnl'] as num?)?.toDouble() ?? 0.0;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            '${entry.key} • ${p['side'] ?? ''} • ${p['strategy'] ?? ''}',
                            style: const TextStyle(fontSize: 12),
                          ),
                        ),
                        Text(
                          '${signed(pnl)} PLN',
                          style: TextStyle(
                            color: pnl >= 0 ? mint : Colors.redAccent,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
          ],
          if (decision['reason'] != null) ...[
            const SizedBox(height: 6),
            Text(
              decision['reason'].toString(),
              style: const TextStyle(color: muted, fontSize: 12),
            ),
          ],
          const SizedBox(height: 12),
          const Text(
            'WYKONAJ oznacza wyłącznie transfer wirtualnych PLN do autonomicznego konta paper. '
            'Nie są wysyłane żadne prawdziwe zlecenia.',
            style: TextStyle(color: muted, fontSize: 12),
          ),
        ],
      ),
    );
  }

  void assetDetail(Map<String, dynamic> asset) {
    final symbol = asset['symbol']?.toString() ?? '—';
    final opportunity = opportunityFor(symbol);
    final pln = asMap(asset['pln']);
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: panel,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              heading(symbol, asset['name']?.toString()),
              Text(
                'Cena: ${number(asset['market_price'], 5)} ${asset['quote'] ?? ''}',
              ),
              if (asset['market_price_pln'] is num)
                Text(
                  'Cena referencyjna: ${number(asset['market_price_pln'], 2)} PLN',
                ),
              const SizedBox(height: 10),
              Text('Pozycja paper-live: ${asset['position'] ?? 'FLAT'}'),
              Text(
                'Wynik paper-live: ${signed(asset['net_profit'])} ${asset['quote'] ?? ''}',
              ),
              if (asset['net_profit_pln'] is num)
                Text(
                  'Wynik paper-live: ${signed(asset['net_profit_pln'])} PLN',
                ),
              if (opportunity != null) ...[
                const SizedBox(height: 14),
                Text(
                  'Research TOP ${opportunityRank(symbol) ?? '—'} • ${classLabel(opportunity['asset_class'])}',
                  style: const TextStyle(
                    color: cyan,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text('Strategia: ${opportunity['strategy'] ?? '—'}'),
                if (opportunity['cross_market_score'] is num)
                  Text(
                    'Cross score: ${number(opportunity['cross_market_score'], 4)}',
                  ),
                if (opportunity['expected_net_return'] is num)
                  Text(
                    'Prognoza netto modelu: ${((opportunity['expected_net_return'] as num).toDouble() * 100).toStringAsFixed(3)}%',
                  ),
                Text(
                  'Walidacja: ${opportunity['validation_trades'] ?? 0} prób',
                ),
              ],
              const SizedBox(height: 12),
              Text(
                pln['available'] == true
                    ? 'PLN: ${pln['path'] ?? 'realna ścieżka FX'}'
                    : 'PLN niedostępne dla tego rynku',
                style: const TextStyle(color: muted, fontSize: 12),
              ),
              const SizedBox(height: 18),
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Zamknij'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget marketTable({bool all = false}) {
    final filtered = assets.where((asset) {
      final symbol = asset['symbol']?.toString() ?? '';
      final name = asset['name']?.toString() ?? '';
      return '$symbol $name'.toLowerCase().contains(query.toLowerCase());
    }).toList()
      ..sort((a, b) {
        final aOpen = (a['position']?.toString() ?? 'FLAT') != 'FLAT';
        final bOpen = (b['position']?.toString() ?? 'FLAT') != 'FLAT';
        if (aOpen != bOpen) return aOpen ? -1 : 1;

        final ar = opportunityRank(a['symbol']?.toString() ?? '') ?? 9999;
        final br = opportunityRank(b['symbol']?.toString() ?? '') ?? 9999;
        if (ar != br) return ar.compareTo(br);

        return (a['symbol']?.toString() ?? '')
            .compareTo(b['symbol']?.toString() ?? '');
      });
    final shown = all ? filtered : filtered.take(12).toList();

    return box(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text(
                  'Rynki AI paper-live',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                ),
              ),
              if (!all)
                TextButton(
                  onPressed: () => setState(() => page = 1),
                  child: const Text('Wszystkie rynki'),
                ),
            ],
          ),
          const Text(
            'Wszystkie skonfigurowane rynki • równoległe pozycje AI • wyłącznie wirtualne PLN',
            style: TextStyle(color: muted, fontSize: 12),
          ),
          if (all)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: TextField(
                onChanged: (value) => setState(() => query = value),
                decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.search),
                  hintText: 'Szukaj instrumentu',
                  border: OutlineInputBorder(),
                ),
              ),
            ),
          if (shown.isEmpty)
            const Padding(
              padding: EdgeInsets.all(24),
              child: Text(
                'Brak danych rynkowych',
                style: TextStyle(color: muted),
              ),
            ),
          for (final asset in shown)
            Builder(
              builder: (context) {
                final symbol = asset['symbol']?.toString() ?? '—';
                final pnl = (asset['net_profit'] as num?)?.toDouble() ?? 0.0;
                final pnlPln = (asset['net_profit_pln'] as num?)?.toDouble();
                final opportunity = opportunityFor(symbol);
                final rank = opportunity == null
                    ? null
                    : opportunityRank(symbol);
                final price = asset['market_price'];
                final digits = price is num && price.toDouble() < 10 ? 5 : 2;
                return InkWell(
                  onTap: () => assetDetail(asset),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 13),
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 17,
                          backgroundColor: const Color(0xFF23485F),
                          child: Text(
                            assetBadge(symbol),
                            style: const TextStyle(
                              color: cyan,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                symbol,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              Text(
                                asset['name']?.toString() ?? '',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  color: muted,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(
                              '${number(price, digits)} ${asset['quote'] ?? ''}',
                            ),
                            Text(
                              pnlPln != null
                                  ? '${signed(pnlPln)} PLN'
                                  : '${signed(pnl)} ${asset['quote'] ?? ''}',
                              style: TextStyle(
                                color: pnl >= 0 ? mint : Colors.redAccent,
                                fontSize: 12,
                              ),
                            ),
                            Text(
                              (asset['position']?.toString() ?? 'FLAT') != 'FLAT'
                                  ? '${asset['position']} • AI ${number(asset['ai_allocation_pln'])} PLN'
                                  : rank == null
                                  ? 'FLAT • poza TOP 10'
                                  : 'TOP $rank • ${classLabel(opportunity?['asset_class'])}',
                              style: const TextStyle(
                                color: muted,
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
        ],
      ),
    );
  }

  Widget activity() {
    final decisions = asList(ai?['decisions']);
    final macro = asList(research?['macro_events']);
    final errors = asMap(research?['errors']);
    return box(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          heading('Aktywność AI', 'Autonomiczny paper research'),
          const Row(
            children: [
              Icon(Icons.psychology_outlined, color: cyan, size: 30),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Model analizuje realne dane, ale wykonuje wyłącznie symulowane decyzje.',
                  style: TextStyle(color: muted),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          if (decisions.isEmpty)
            const Text(
              'Brak zapisanych decyzji AI.',
              style: TextStyle(color: muted),
            )
          else
            for (final raw in decisions.reversed.take(10))
              if (raw is Map)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.bolt, color: cyan, size: 20),
                  title: Text(
                    '${raw['symbol'] ?? 'Gotówka'} • ${raw['action'] ?? 'DECISION'}',
                  ),
                  subtitle: Text(raw['reason']?.toString() ?? ''),
                ),
          if (macro.isNotEmpty) ...[
            const Divider(color: Color(0xFF294152)),
            const SizedBox(height: 10),
            const Text(
              'Ostatnie wydarzenia makro',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            for (final raw in macro.reversed.take(5))
              if (raw is Map)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.public, color: mint, size: 20),
                  title: Text(raw['title']?.toString() ?? 'Wydarzenie makro'),
                  subtitle: Text(raw['source']?.toString() ?? ''),
                ),
          ],
          if (errors.values.any((value) => value != null)) ...[
            const Divider(color: Color(0xFF294152)),
            Text(
              errors.entries
                  .where((entry) => entry.value != null)
                  .map((entry) => '${entry.key}: ${entry.value}')
                  .join(' • '),
              style: const TextStyle(color: Colors.amber, fontSize: 12),
            ),
          ],
          const SizedBox(height: 14),
          const Text(
            'Wirtualny broker • brak prawdziwych zleceń • ranking nie jest gwarancją zysku.',
            style: TextStyle(color: mint, height: 1.5),
          ),
        ],
      ),
    );
  }

  Widget history() {
    final trades = asList(ai?['trades']);
    return box(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          heading('Historia transakcji AI', 'Paper only'),
          if (trades.isEmpty)
            const Text(
              'Nie zamknięto jeszcze żadnej pozycji AI.',
              style: TextStyle(color: muted),
            ),
          for (final raw in trades.reversed)
            if (raw is Map)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.swap_horiz, color: cyan),
                title: Text(
                  '${raw['symbol'] ?? '—'} • ${raw['strategy'] ?? '—'}',
                ),
                subtitle: Text(
                  '${raw['reason'] ?? ''} • ${number(raw['entry'], 5)} → ${number(raw['exit_price'], 5)}',
                ),
                trailing: Text(
                  '${signed(raw['profit'])} PLN',
                  style: TextStyle(
                    color: (raw['profit'] as num? ?? 0) >= 0
                        ? mint
                        : Colors.redAccent,
                  ),
                ),
              ),
        ],
      ),
    );
  }

  void openLegacy() {
    final builder = widget.legacyBuilder;
    if (builder == null) return;
    Navigator.of(context).push(MaterialPageRoute<void>(builder: builder));
  }

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 1100;
    final researchData = research;

    return Scaffold(
      backgroundColor: ink,
      bottomNavigationBar: wide
          ? null
          : NavigationBar(
              selectedIndex: page,
              backgroundColor: panel,
              onDestinationSelected: (value) => setState(() => page = value),
              destinations: [
                for (int i = 0; i < labels.length; i++)
                  NavigationDestination(
                    icon: Icon(icons[i]),
                    label: i == 2
                        ? 'TOP 10'
                        : i == 3
                        ? 'AI'
                        : labels[i],
                  ),
              ],
            ),
      body: SafeArea(
        child: Row(
          children: [
            if (wide)
              Container(
                width: 205,
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 30,
                ),
                decoration: const BoxDecoration(
                  border: Border(right: BorderSide(color: Color(0xFF243E52))),
                ),
                child: Column(
                  children: [
                    const Text(
                      'AL',
                      style: TextStyle(
                        color: cyan,
                        fontSize: 44,
                        fontWeight: FontWeight.w900,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                    const Text(
                      'AL TRADING',
                      style: TextStyle(letterSpacing: 2, fontSize: 12),
                    ),
                    const SizedBox(height: 38),
                    for (int i = 0; i < labels.length; i++)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                          selected: page == i,
                          selectedTileColor: panel,
                          selectedColor: cyan,
                          leading: Icon(icons[i], size: 20),
                          title: Text(
                            labels[i],
                            style: const TextStyle(fontSize: 13),
                          ),
                          onTap: () => setState(() => page = i),
                        ),
                      ),
                    if (widget.legacyBuilder != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: OutlinedButton.icon(
                          onPressed: openLegacy,
                          icon: const Icon(Icons.candlestick_chart, size: 18),
                          label: const Text('Szczegóły rynku'),
                        ),
                      ),
                    const Spacer(),
                    const Text(
                      'Realne dane rynkowe.\nWirtualny kapitał.',
                      style: TextStyle(color: muted, height: 1.6),
                    ),
                  ],
                ),
              ),
            Expanded(
              child: RefreshIndicator(
                onRefresh: refresh,
                child: ListView(
                  padding: EdgeInsets.all(wide ? 28 : 16),
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            page == 0 ? 'Przegląd portfela' : labels[page],
                            style: const TextStyle(
                              fontSize: 25,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        if (!wide && widget.legacyBuilder != null)
                          IconButton(
                            tooltip: 'Szczegóły rynku',
                            onPressed: openLegacy,
                            icon: const Icon(
                              Icons.candlestick_chart,
                              color: cyan,
                            ),
                          ),
                        IconButton(
                          tooltip: 'Odśwież',
                          onPressed: refresh,
                          icon: const Icon(Icons.refresh, color: cyan),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 16,
                      runSpacing: 8,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: panel,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: const Color(0xFF30546D)),
                          ),
                          child: const Text(
                            'PAPER ONLY • realne dane',
                            style: TextStyle(color: cyan, fontSize: 12),
                          ),
                        ),
                        Text(
                          received == null
                              ? 'Łączenie…'
                              : 'Odbiór: ${received!.toLocal().toString().substring(11, 19)}',
                          style: const TextStyle(color: muted, fontSize: 12),
                        ),
                        Text(
                          'TOP 10: ${opportunities.length} • klasy: ${asMap(research?['selected_by_class']).length}',
                          style: const TextStyle(color: muted, fontSize: 12),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    if (failure != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: Text(
                          failure!,
                          style: const TextStyle(color: Colors.amber),
                        ),
                      ),
                    if (received == null && failure == null)
                      const LinearProgressIndicator(),
                    if (page == 0) ...[
                      summary(),
                      const SizedBox(height: 20),
                      marketTickerStrip(),
                      const SizedBox(height: 20),
                      if (wide)
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              flex: 3,
                              child: Column(
                                children: [
                                  equityChart(),
                                  const SizedBox(height: 20),
                                  marketTable(),
                                ],
                              ),
                            ),
                            const SizedBox(width: 20),
                            Expanded(
                              flex: 2,
                              child: Column(
                                children: [
                                  fundsDonut(),
                                  const SizedBox(height: 20),
                                  portfolioActions(),
                                  const SizedBox(height: 20),
                                  activity(),
                                ],
                              ),
                            ),
                          ],
                        )
                      else ...[
                        fundsDonut(),
                        const SizedBox(height: 20),
                        portfolioActions(),
                        const SizedBox(height: 20),
                        equityChart(),
                        const SizedBox(height: 20),
                        marketTable(),
                        const SizedBox(height: 20),
                        activity(),
                      ],
                    ],
                    if (page == 1) marketTable(all: true),
                    if (page == 2)
                      ResearchPanel(data: researchData, error: failure),
                    if (page == 3) activity(),
                    if (page == 4) history(),
                    const SizedBox(height: 24),
                    const Center(
                      child: Text(
                        'AL Trading Agent • realne notowania • wirtualne środki • zero realnych zleceń',
                        style: TextStyle(color: muted, fontSize: 11),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class FundsDonutPainter extends CustomPainter {
  final List<double> values;
  final List<Color> colors;

  FundsDonutPainter({
    required this.values,
    required this.colors,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final total = values.fold<double>(
      0.0,
      (sum, value) => sum + math.max(0.0, value),
    );

    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) / 2 - 6;
    final rect = Rect.fromCircle(center: center, radius: radius);
    const stroke = 22.0;

    if (total <= 0) {
      canvas.drawArc(
        rect,
        0,
        math.pi * 2,
        false,
        Paint()
          ..color = const Color(0xFF294152)
          ..style = PaintingStyle.stroke
          ..strokeWidth = stroke,
      );
      return;
    }

    var start = -math.pi / 2;
    for (int i = 0; i < values.length; i++) {
      final value = math.max(0.0, values[i]);
      if (value <= 0) continue;

      final sweep = math.pi * 2 * value / total;
      canvas.drawArc(
        rect,
        start,
        sweep,
        false,
        Paint()
          ..color = colors[i % colors.length]
          ..style = PaintingStyle.stroke
          ..strokeWidth = stroke
          ..strokeCap = StrokeCap.butt,
      );
      start += sweep;
    }
  }

  @override
  bool shouldRepaint(covariant FundsDonutPainter oldDelegate) => true;
}


class EquityPainter extends CustomPainter {
  final List<double> values;

  EquityPainter(this.values);

  @override
  void paint(Canvas canvas, Size size) {
    if (values.length < 2) return;
    final low = values.reduce(math.min);
    final high = values.reduce(math.max);
    final pad = math.max((high - low) * 0.15, 0.5);
    final minY = low - pad;
    final span = high - low + 2 * pad;
    final grid = Paint()
      ..color = const Color(0xFF294152)
      ..strokeWidth = 1;

    for (int i = 0; i <= 4; i++) {
      final y = size.height * i / 4;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }

    final path = Path();
    for (int i = 0; i < values.length; i++) {
      final x = size.width * i / (values.length - 1);
      final y = size.height * (1 - (values[i] - minY) / span);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }

    final fill = Path.from(path)
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();

    canvas.drawPath(
      fill,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0x5539DFAD), Color(0x0039DFAD)],
        ).createShader(Offset.zero & size),
    );

    canvas.drawPath(
      path,
      Paint()
        ..color = mint
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );
  }

  @override
  bool shouldRepaint(covariant EquityPainter oldDelegate) => true;
}
