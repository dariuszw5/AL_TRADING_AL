import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';

import 'research_card.dart';

const ink = Color(0xFF071522);
const panel = Color(0xFF102638);
const cyan = Color(0xFF51C8FA);
const mint = Color(0xFF39DFAD);
const muted = Color(0xFF95AABE);

class ProDashboard extends StatefulWidget {
  final String baseUrl;
  final Future<Map<String, dynamic>> Function()? loader;
  const ProDashboard({super.key, required this.baseUrl, this.loader});
  @override
  State<ProDashboard> createState() => _ProDashboardState();
}

class _ProDashboardState extends State<ProDashboard> {
  Map<String, dynamic>? data;
  String? failure;
  DateTime? received;
  Timer? timer;
  bool busy = false;
  int page = 0;
  String query = '';
  late final http.Client client = IOClient(
    HttpClient()..findProxy = (_) => 'DIRECT',
  );
  final labels = ['Portfel', 'Rynki', 'Aktywność AI', 'Historia'];
  final icons = [
    Icons.account_balance_wallet_outlined,
    Icons.bar_chart,
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
    client.close();
    super.dispose();
  }

  Future<void> refresh() async {
    if (busy) return;
    busy = true;
    try {
      final Map<String, dynamic> next;
      if (widget.loader != null) {
        next = await widget.loader!();
      } else {
        http.Response? response;
        Object? lastError;
        for (var attempt = 0; attempt < 3; attempt++) {
          try {
            response = await client
                .get(
                  Uri.parse('${widget.baseUrl}/api/ai-research'),
                  headers: const {
                    'Connection': 'close',
                    'Cache-Control': 'no-cache',
                  },
                )
                .timeout(const Duration(seconds: 15));
            if (response.statusCode == 200) break;
          } catch (error) {
            lastError = error;
            if (attempt < 2) {
              await Future<void>.delayed(const Duration(milliseconds: 350));
            }
          }
        }
        if (response == null) {
          throw Exception(lastError ?? 'Brak odpowiedzi API');
        }
        if (response.statusCode != 200) {
          throw Exception('HTTP ${response.statusCode}');
        }
        next = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
      }
      if (next['available'] == false ||
          next['virtual_broker'] is! Map ||
          next['assets'] is! Map) {
        throw Exception('Oczekiwanie na pierwszy cykl AI');
      }
      if (mounted) {
        setState(() {
          data = next;
          received = DateTime.now();
          failure = null;
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() => failure = 'Połączenie API: $error');
      }
    } finally {
      busy = false;
    }
  }

  Map get broker => data?['virtual_broker'] as Map? ?? {};
  bool get isPln => broker['currency'] == 'PLN';
  String get unit => isPln ? 'zł' : 'jedn. sym.';
  Map get markets => data?['assets'] as Map? ?? {};
  List get trades => broker['trades'] as List? ?? [];
  List get curve => broker['equity_curve'] as List? ?? [];
  String number(dynamic n, [int digits = 2]) =>
      n is num ? n.toStringAsFixed(digits) : '—';
  bool get stale {
    final cycle = DateTime.tryParse(data?['last_cycle']?.toString() ?? '');
    return failure != null ||
        cycle == null ||
        DateTime.now().difference(cycle).inSeconds > 180 ||
        data?['stale'] == true;
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
  Widget stat(String title, String value, IconData icon, {Color? color}) => box(
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
            fontSize: 25,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
      ],
    ),
  );
  Widget summary() {
    final balance = broker['balance'];
    final equity = isPln
        ? broker['equity']
        : (curve.isEmpty ? balance : curve.last['equity']);
    final initial = broker['initial_balance'];
    final reserve = broker['user_portfolio'] as Map? ?? {};
    final gain = equity is num && initial is num
        ? (isPln
              ? (broker['realized_profit'] as num? ?? 0) +
                    equity -
                    (balance as num)
              : equity - initial)
        : null;
    return LayoutBuilder(
      builder: (context, c) {
        final children = [
          stat(
            'Kapitał AI • $unit',
            number(equity),
            Icons.account_balance_wallet_outlined,
          ),
          stat(
            'Wynik łączny • $unit',
            gain == null ? '—' : '${gain >= 0 ? '+' : ''}${number(gain)}',
            Icons.trending_up,
            color: gain == null || gain >= 0 ? mint : Colors.redAccent,
          ),
          stat(
            'Otwarte pozycje',
            data == null
                ? '—'
                : '${(broker['positions'] as Map? ?? {}).length}',
            Icons.layers_outlined,
          ),
          if (isPln)
            stat(
              'Mój portfel • zł',
              number(reserve['balance']),
              Icons.savings_outlined,
            ),
          if (isPln && (broker['shortfall'] as num? ?? 0) > 0)
            stat(
              'Brakuje do 1000 zł',
              number(broker['shortfall']),
              Icons.warning_amber,
              color: Colors.amber,
            ),
        ];
        if (c.maxWidth < 850) {
          return Column(
            children: [
              for (final child in children)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: SizedBox(width: double.infinity, child: child),
                ),
            ],
          );
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (int i = 0; i < children.length; i++)
              Expanded(
                child: Padding(
                  padding: EdgeInsets.only(right: i == 2 ? 0 : 12),
                  child: children[i],
                ),
              ),
          ],
        );
      },
    );
  }

  Widget equityChart() {
    final values = curve
        .where((p) => p['equity'] is num)
        .map<double>((p) => (p['equity'] as num).toDouble())
        .toList();
    return box(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          heading('Wartość portfela • $unit', 'Historia symulacji'),
          if (values.length < 2)
            const SizedBox(
              height: 220,
              child: Center(
                child: Text(
                  'Oczekiwanie na historię kapitału',
                  style: TextStyle(color: muted),
                ),
              ),
            )
          else
            Column(
              children: [
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
                Text(
                  isPln
                      ? 'Kapitał AI w zł • zyski po zamknięciu trafiają do rezerwy'
                      : 'Jednostki symulacyjne • bez przeliczenia walut',
                  style: const TextStyle(color: muted, fontSize: 12),
                ),
              ],
            ),
        ],
      ),
    );
  }

  void assetDetail(String symbol) {
    final asset = markets[symbol] as Map;
    final account = researchCard(data!, symbol)['account'] as Map;
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
                'Cena: ${number(isPln ? asset['market_price_pln'] : asset['market_price'], 5)} $unit',
              ),
              const SizedBox(height: 12),
              Text('Pozycja: ${account['position']}'),
              Text('Wynik: ${number(account['net_profit'])} $unit'),
              const SizedBox(height: 18),
              Text(
                asset['issue']?.toString() ??
                    (asset['recommendation'] == 'OBSERVE_SIGNAL'
                        ? 'Sygnał zakwalifikowany do symulacji'
                        : 'Oczekiwanie na sygnał spełniający warunki modelu'),
                style: const TextStyle(color: muted),
              ),
              const SizedBox(height: 20),
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
    final symbols = markets.keys
        .map((e) => e.toString())
        .where(
          (s) => '$s ${markets[s]['name']}'.toLowerCase().contains(
            query.toLowerCase(),
          ),
        )
        .toList();
    final shown = all ? symbols : symbols.take(8).toList();
    return box(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text(
                  'Rynki i pozycje',
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
          if (all)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: TextField(
                onChanged: (v) => setState(() => query = v),
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
          for (final symbol in shown)
            Builder(
              builder: (context) {
                final asset = markets[symbol] as Map;
                final account = researchCard(data!, symbol)['account'] as Map;
                final pnl = account['net_profit'] as num;
                return InkWell(
                  onTap: () => assetDetail(symbol),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 13),
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 17,
                          backgroundColor: const Color(0xFF23485F),
                          child: Text(
                            symbol.substring(0, 1),
                            style: const TextStyle(color: cyan),
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
                              number(
                                isPln
                                    ? asset['market_price_pln']
                                    : asset['market_price'],
                                (asset['market_price'] as num? ?? 100) < 10
                                    ? 5
                                    : 2,
                              ),
                            ),
                            Text(
                              '${pnl >= 0 ? '+' : ''}${number(pnl)} $unit',
                              style: TextStyle(
                                color: pnl >= 0 ? mint : Colors.redAccent,
                                fontSize: 12,
                              ),
                            ),
                            Text(
                              account['position'] == 'FLAT'
                                  ? 'Obserwacja'
                                  : 'Pozycja otwarta',
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

  Widget activity() => box(
    Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        heading('Aktywność AI'),
        const Icon(Icons.psychology_outlined, color: cyan, size: 30),
        const SizedBox(height: 14),
        Text(
          stale ? 'Oczekiwanie na aktualne dane' : 'Analiza rynków',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        Text(
          '${markets.length} instrumentów w ostatnim cyklu. ${(markets.values.where((a) => a['recommendation'] == 'OBSERVE_SIGNAL')).length} zakwalifikowanych sygnałów.',
          style: const TextStyle(color: muted, height: 1.6),
        ),
        const SizedBox(height: 20),
        const Divider(color: Color(0xFF294152)),
        const SizedBox(height: 16),
        const Text(
          'Ostatnie zamknięcia',
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
        if (trades.isEmpty)
          const Padding(
            padding: EdgeInsets.only(top: 12),
            child: Text(
              'Brak zamkniętych transakcji. Wyniki pojawią się po wykonaniu symulacji.',
              style: TextStyle(color: muted, height: 1.6),
            ),
          ),
        for (final t in trades.reversed.take(5))
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.swap_horiz, color: cyan),
            title: Text(t['symbol'].toString()),
            subtitle: Text(t['reason']?.toString() ?? ''),
            trailing: Text('${number(t['profit'])} $unit'),
          ),
        const SizedBox(height: 20),
        const Text(
          'Wirtualny broker\nBez prawdziwych zleceń',
          style: TextStyle(color: mint, height: 1.6),
        ),
      ],
    ),
  );
  Widget history() => box(
    Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        heading('Historia transakcji'),
        if (isPln) ...[
          const Text('Transfery między portfelami • zł'),
          for (final transfer
              in (broker['transfers'] as List? ?? []).reversed.take(30))
            ListTile(
              title: Text(
                transfer['direction'] == 'TO_RESERVE'
                    ? 'Zysk do Mojego portfela'
                    : 'Dopłata do kapitału AI',
              ),
              subtitle: Text(
                DateTime.fromMillisecondsSinceEpoch(
                  (transfer['timestamp'] as num).toInt(),
                ).toLocal().toString(),
              ),
              trailing: Text('${number(transfer['amount'])} zł'),
            ),
        ],
        if (trades.isEmpty) const Text('Nie zamknięto jeszcze żadnej pozycji.'),
        for (final t in trades.reversed)
          ListTile(
            title: Text(t['symbol'].toString()),
            subtitle: Text(
              '${t['reason']} • ${number(t['entry'])} → ${number(t['exit_price'])}',
            ),
            trailing: Text('${number(t['profit'])} $unit'),
          ),
      ],
    ),
  );
  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 1100;
    return Scaffold(
      backgroundColor: ink,
      bottomNavigationBar: wide
          ? null
          : NavigationBar(
              selectedIndex: page,
              backgroundColor: panel,
              onDestinationSelected: (v) => setState(() => page = v),
              destinations: [
                for (int i = 0; i < labels.length; i++)
                  NavigationDestination(
                    icon: Icon(icons[i]),
                    label: i == 2 ? 'AI' : labels[i],
                  ),
              ],
            ),
      body: SafeArea(
        child: Row(
          children: [
            if (wide)
              Container(
                width: 190,
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
                    const SizedBox(height: 44),
                    for (int i = 0; i < labels.length; i++)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
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
                    const Spacer(),
                    const Text(
                      'Dane rynkowe.\nWirtualny kapitał.',
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
                            'SYMULACJA • Dane rynkowe',
                            style: TextStyle(color: cyan, fontSize: 12),
                          ),
                        ),
                        Text(
                          received == null
                              ? 'Łączenie…'
                              : 'Odbiór: ${received!.toLocal().toString().substring(11, 19)}',
                          style: const TextStyle(color: muted, fontSize: 12),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    if (stale)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: Text(
                          failure ??
                              'Oczekiwanie na świeży cykl AI. Dane odświeżają się automatycznie.',
                          style: const TextStyle(color: Colors.amber),
                        ),
                      ),
                    if (data == null && failure == null)
                      const LinearProgressIndicator(),
                    if (page == 0) ...[
                      summary(),
                      if (isPln)
                        Padding(
                          padding: const EdgeInsets.only(top: 12),
                          child: Text(
                            'Wolne środki: ${number(broker['free_cash'])} zł • Cel kapitału: 1000 zł. Zajęte środki pozostają częścią kapitału.',
                            style: const TextStyle(color: muted),
                          ),
                        ),
                      if (isPln)
                        Text(
                          (data?['fx'] as Map? ?? {})['issue'] != null
                              ? 'Brak kursów walut — nowe rozliczenia wstrzymane.'
                              : 'Kursy orientacyjne Coinbase • odbiór: ${DateTime.fromMillisecondsSinceEpoch((((data?['fx'] as Map? ?? {})['received_at'] as num?) ?? 0).toInt()).toLocal()}',
                          style: const TextStyle(color: muted),
                        ),
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
                            Expanded(child: activity()),
                          ],
                        )
                      else ...[
                        equityChart(),
                        const SizedBox(height: 20),
                        marketTable(),
                        const SizedBox(height: 20),
                        activity(),
                      ],
                    ],
                    if (page == 1) marketTable(all: true),
                    if (page == 2) activity(),
                    if (page == 3) history(),
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

class EquityPainter extends CustomPainter {
  final List<double> values;
  EquityPainter(this.values);
  @override
  void paint(Canvas canvas, Size size) {
    if (values.length < 2) return;
    final low = values.reduce(math.min), high = values.reduce(math.max);
    final pad = math.max((high - low) * .15, .5);
    final minY = low - pad, span = high - low + 2 * pad;
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
