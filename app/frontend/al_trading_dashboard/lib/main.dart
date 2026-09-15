import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

const apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://100.77.193.89:8000',
);

void main() => runApp(const AlTradingApp());

class AlTradingApp extends StatelessWidget {
  const AlTradingApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'AL Trading',
      theme: ThemeData(
        brightness: Brightness.dark,
        useMaterial3: true,
        scaffoldBackgroundColor: Ui.bg,
        colorScheme: const ColorScheme.dark(
          primary: Ui.cyan,
          secondary: Ui.green,
          surface: Ui.panel,
        ),
      ),
      home: const TradingHome(),
    );
  }
}

class Ui {
  static const bg = Color(0xFF06111E);
  static const sidebar = Color(0xFF071522);
  static const panel = Color(0xFF0B1A29);
  static const panel2 = Color(0xFF0F2335);
  static const border = Color(0xFF1C3C54);
  static const text = Color(0xFFF4F8FE);
  static const muted = Color(0xFF8FA7BC);
  static const cyan = Color(0xFF36B8FF);
  static const green = Color(0xFF20E5A5);
  static const red = Color(0xFFFF6078);
  static const orange = Color(0xFFFFB44C);
  static const purple = Color(0xFF827BFF);
}

class TradingHome extends StatefulWidget {
  const TradingHome({super.key});

  @override
  State<TradingHome> createState() => _TradingHomeState();
}

class _TradingHomeState extends State<TradingHome> {
  int page = 0;
  String symbol = 'BTCUSDT';
  bool loading = true;
  bool online = false;
  String? error;
  Timer? timer;

  List<Map<String, dynamic>> assets = [];
  List<Map<String, dynamic>> trades = [];
  List<Map<String, dynamic>> daily = [];
  Map<String, dynamic> status = {};
  Map<String, dynamic> equity = {};
  Map<String, dynamic> market = {};
  Map<String, dynamic> portfolio = {};
  Map<String, dynamic> ai = {};

  final nav = const [
    (Icons.dashboard_rounded, 'Pulpit'),
    (Icons.account_balance_wallet_outlined, 'Portfel'),
    (Icons.candlestick_chart_rounded, 'Rynki'),
    (Icons.auto_graph_rounded, 'Strategie'),
    (Icons.swap_horiz_rounded, 'Transakcje'),
    (Icons.analytics_outlined, 'Analizy'),
    (Icons.calendar_month_outlined, 'Kalendarz'),
    (Icons.notifications_none_rounded, 'Alerty'),
    (Icons.settings_outlined, 'Ustawienia'),
  ];

  @override
  void initState() {
    super.initState();
    refresh();
    timer = Timer.periodic(const Duration(seconds: 10), (_) => refresh());
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  Future<dynamic> getJson(String path) async {
    final response = await http
        .get(Uri.parse('$apiBaseUrl$path'))
        .timeout(const Duration(seconds: 7));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('HTTP ${response.statusCode}');
    }
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  Future<void> refresh() async {
    try {
      final common = await Future.wait([
        getJson('/api/assets'),
        getJson('/api/user-portfolio'),
        getJson('/api/daily'),
        getJson('/api/ai'),
      ]);
      final nextAssets = (common[0] as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      if (nextAssets.isNotEmpty &&
          !nextAssets.any((e) => '${e['symbol']}' == symbol)) {
        symbol = '${nextAssets.first['symbol']}';
      }
      final detail = await Future.wait([
        getJson('/api/status?symbol=$symbol'),
        getJson('/api/trades?symbol=$symbol'),
        getJson('/api/equity?symbol=$symbol'),
        getJson('/api/market?symbol=$symbol'),
      ]);
      if (!mounted) return;
      setState(() {
        assets = nextAssets;
        portfolio = Map<String, dynamic>.from(common[1] as Map);
        daily = (common[2] as List)
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
        ai = Map<String, dynamic>.from(common[3] as Map);
        status = Map<String, dynamic>.from(detail[0] as Map);
        trades = (detail[1] as List)
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
        equity = Map<String, dynamic>.from(detail[2] as Map);
        market = Map<String, dynamic>.from(detail[3] as Map);
        online = true;
        loading = false;
        error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        online = false;
        loading = false;
        error = '$e';
      });
    }
  }

  Future<void> changeSymbol(String next) async {
    if (next == symbol) return;
    setState(() {
      symbol = next;
      loading = true;
    });
    await refresh();
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, c) {
        final desktop = c.maxWidth >= 1000;
        return Scaffold(
          backgroundColor: Ui.bg,
          drawer: desktop ? null : Drawer(backgroundColor: Ui.sidebar, child: navList()),
          appBar: desktop
              ? null
              : AppBar(
                  backgroundColor: Ui.sidebar,
                  title: const Text('AL Trading', style: TextStyle(fontWeight: FontWeight.w900)),
                  actions: [
                    Padding(
                      padding: const EdgeInsets.only(right: 12),
                      child: statusPill(online ? 'API ONLINE' : 'API OFFLINE', online ? Ui.green : Ui.red),
                    ),
                  ],
                ),
          body: Row(
            children: [
              if (desktop) SizedBox(width: 220, child: navList()),
              Expanded(
                child: Column(
                  children: [
                    if (!online && error != null)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(7),
                        color: Ui.red.withOpacity(.12),
                        child: Text(error!, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Ui.red, fontSize: 11)),
                      ),
                    Expanded(
                      child: loading && assets.isEmpty
                          ? const Center(child: CircularProgressIndicator())
                          : pageBody(),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget navList() {
    return Container(
      color: Ui.sidebar,
      child: SafeArea(
        child: Column(
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(18, 18, 18, 14),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 21,
                    backgroundColor: Ui.cyan,
                    child: Icon(Icons.show_chart_rounded, color: Colors.white),
                  ),
                  SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('AL Trading', style: TextStyle(color: Ui.text, fontSize: 20, fontWeight: FontWeight.w900)),
                      Text('Paper Trading (PLN)', style: TextStyle(color: Ui.muted, fontSize: 11)),
                    ],
                  ),
                ],
              ),
            ),
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 9),
                itemCount: nav.length,
                itemBuilder: (_, i) => Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: ListTile(
                    dense: true,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    tileColor: page == i ? const Color(0xFF102B41) : null,
                    leading: Icon(nav[i].$1, color: page == i ? Ui.cyan : Ui.muted),
                    title: Text(nav[i].$2, style: TextStyle(color: page == i ? Ui.text : Ui.muted, fontWeight: page == i ? FontWeight.w800 : FontWeight.w500)),
                    trailing: i == 7 && alerts().isNotEmpty
                        ? CircleAvatar(radius: 10, backgroundColor: Ui.red, child: Text('${alerts().length}', style: const TextStyle(fontSize: 9)))
                        : null,
                    onTap: () {
                      setState(() => page = i);
                      if (Navigator.canPop(context)) Navigator.pop(context);
                    },
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(10),
              child: card(
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [Icon(Icons.circle, size: 9, color: online ? Ui.green : Ui.red), const SizedBox(width: 7), Text(online ? 'System połączony' : 'API offline', style: const TextStyle(fontWeight: FontWeight.w800))]),
                    const SizedBox(height: 7),
                    Text(symbol, style: const TextStyle(color: Ui.cyan, fontSize: 11)),
                    const SizedBox(height: 4),
                    Text(apiBaseUrl, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Ui.muted, fontSize: 9)),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget pageBody() {
    return switch (page) {
      0 => dashboard(),
      1 => portfolioPage(),
      2 => marketsPage(),
      3 => strategyPage(),
      4 => tradesPage(),
      5 => analyticsPage(),
      6 => pendingPage('Kalendarz', 'FastAPI nie ma jeszcze endpointu kalendarza makro.'),
      7 => alertsPage(),
      _ => settingsPage(),
    };
  }

  Widget dashboard() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(12),
      child: Column(
        children: [
          topSummary(),
          const SizedBox(height: 10),
          LayoutBuilder(builder: (_, c) {
            if (c.maxWidth >= 1050) {
              return SizedBox(
                height: 310,
                child: Row(
                  children: [
                    Expanded(flex: 6, child: equityCard()),
                    const SizedBox(width: 10),
                    Expanded(flex: 3, child: allocationCard()),
                    const SizedBox(width: 10),
                    Expanded(flex: 3, child: moversCard()),
                  ],
                ),
              );
            }
            return Column(children: [SizedBox(height: 290, child: equityCard()), const SizedBox(height: 10), Row(crossAxisAlignment: CrossAxisAlignment.start, children: [Expanded(child: SizedBox(height: 290, child: allocationCard())), const SizedBox(width: 10), Expanded(child: SizedBox(height: 290, child: moversCard()))])]);
          }),
          const SizedBox(height: 10),
          positionsCard(),
          const SizedBox(height: 10),
          LayoutBuilder(builder: (_, c) {
            final items = [strategyChartCard(), pnlCard(), exposureCard()];
            if (c.maxWidth >= 1050) {
              return SizedBox(height: 245, child: Row(children: [Expanded(child: items[0]), const SizedBox(width: 10), Expanded(child: items[1]), const SizedBox(width: 10), Expanded(child: items[2])]));
            }
            return Column(children: [SizedBox(height: 240, child: items[0]), const SizedBox(height: 10), SizedBox(height: 240, child: items[1]), const SizedBox(height: 10), SizedBox(height: 260, child: items[2])]);
          }),
        ],
      ),
    );
  }

  Widget topSummary() {
    final account = map(status['account']);
    final perf = map(status['performance']);
    final marketPoints = maps(market['points']);
    final price = marketPoints.isEmpty ? numd(account['market_price']) : numd(marketPoints.last['close']);
    final values = [
      ('Wartość portfela (PLN)', '${money(numd(portfolio['balance']))} PLN', Ui.green),
      ('Saldo silnika', fmt(numd(account['balance'])), Ui.cyan),
      ('Wynik silnika', signed(numd(account['net_profit'])), numd(account['net_profit']) >= 0 ? Ui.green : Ui.red),
      ('Cena rynkowa', fmt(price), Ui.cyan),
      ('Win rate', '${fmt(numd(perf['win_rate']))}%', Ui.green),
    ];
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: values.map((e) => SizedBox(width: 215, height: 105, child: card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(e.$1, style: const TextStyle(color: Ui.muted, fontSize: 11)), const Spacer(), Text(e.$2, style: const TextStyle(color: Ui.text, fontSize: 21, fontWeight: FontWeight.w900)), const SizedBox(height: 5), Container(width: 34, height: 3, color: e.$3)])))).toList(),
    );
  }

  Widget equityCard() {
    final points = maps(equity['points']);
    final spots = points.isNotEmpty
        ? points.map((e) => FlSpot(numd(e['index']), numd(e['balance']))).toList()
        : maps(market['points']).asMap().entries.map((e) => FlSpot(e.key.toDouble(), numd(e.value['close']))).toList();
    return card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      rowTitle('Wartość / przebieg kapitału', '/api/equity'),
      const SizedBox(height: 10),
      Expanded(child: spots.length < 2 ? const Center(child: Text('Brak danych', style: TextStyle(color: Ui.muted))) : LineChart(LineChartData(gridData: FlGridData(show: true, getDrawingHorizontalLine: (_) => FlLine(color: Ui.border), getDrawingVerticalLine: (_) => FlLine(color: Ui.border)), borderData: FlBorderData(show: true, border: Border.all(color: Ui.border)), titlesData: const FlTitlesData(topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)), rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)), bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)), leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 48))), lineBarsData: [LineChartBarData(spots: spots, isCurved: true, color: Ui.green, barWidth: 2.3, dotData: const FlDotData(show: false), belowBarData: BarAreaData(show: true, color: Ui.green.withOpacity(.12)))]))),
    ]));
  }

  Widget allocationCard() {
    final dist = <String, int>{};
    for (final a in assets) {
      final type = '${a['asset_type'] ?? 'Inne'}';
      dist[type] = (dist[type] ?? 0) + 1;
    }
    final colors = [Ui.cyan, Ui.green, Ui.purple, Ui.orange, Ui.red];
    final entries = dist.entries.toList();
    return card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      rowTitle('Struktura rynków', '${assets.length} instrumentów'),
      Expanded(child: entries.isEmpty ? const Center(child: Text('Brak danych')) : PieChart(PieChartData(centerSpaceRadius: 47, sectionsSpace: 2, sections: [for (var i = 0; i < entries.length; i++) PieChartSectionData(value: entries[i].value.toDouble(), color: colors[i % colors.length], title: '', radius: 25)]))),
      ...[for (var i = 0; i < entries.length && i < 5; i++) Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Row(children: [Container(width: 8, height: 8, decoration: BoxDecoration(color: colors[i % colors.length], shape: BoxShape.circle)), const SizedBox(width: 7), Expanded(child: Text(entries[i].key, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Ui.muted, fontSize: 10))), Text('${entries[i].value}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 10))]))],
    ]));
  }

  Widget moversCard() {
    final rows = assets.take(8).toList();
    return card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      rowTitle('Najlepsze / obserwowane', 'API'),
      const SizedBox(height: 7),
      ...rows.map((a) => Container(height: 27, margin: const EdgeInsets.only(bottom: 4), padding: const EdgeInsets.symmetric(horizontal: 7), decoration: BoxDecoration(color: Ui.panel2, borderRadius: BorderRadius.circular(6)), child: Row(children: [Expanded(child: Text('${a['symbol'] ?? '—'}', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800))), Text(fmt(numd(a['market_price'])), style: const TextStyle(color: Ui.green, fontSize: 10, fontWeight: FontWeight.w800))]))),
      const Spacer(),
      const Text('Ceny pochodzą z /api/assets.', style: TextStyle(color: Ui.muted, fontSize: 9)),
    ]));
  }

  Widget positionsCard() {
    final pos = map(status['position']);
    final rows = assets.take(7).toList();
    return card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      rowTitle('Otwarte pozycje / rynki', '${rows.length}'),
      const SizedBox(height: 8),
      SingleChildScrollView(scrollDirection: Axis.horizontal, child: DataTable(
        headingRowHeight: 32,
        dataRowMinHeight: 31,
        dataRowMaxHeight: 36,
        columns: const [DataColumn(label: Text('Symbol')), DataColumn(label: Text('Typ')), DataColumn(label: Text('Ilość')), DataColumn(label: Text('Cena wejścia')), DataColumn(label: Text('Cena bieżąca')), DataColumn(label: Text('Provider')), DataColumn(label: Text('Pozycja'))],
        rows: rows.map((a) {
          final current = '${a['symbol']}' == symbol;
          final side = current ? '${pos['side'] ?? a['position'] ?? 'FLAT'}' : '${a['position'] ?? 'FLAT'}';
          return DataRow(cells: [DataCell(Text('${a['symbol'] ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w800))), DataCell(Text('${a['asset_type'] ?? '—'}')), DataCell(Text(current ? display(pos['quantity']) : '—')), DataCell(Text(current ? display(pos['entry_price']) : '—')), DataCell(Text(fmt(numd(a['market_price'])))), DataCell(Text('${a['provider'] ?? '—'}')), DataCell(Text(side, style: TextStyle(color: side == 'FLAT' || side == 'null' ? Ui.muted : Ui.green, fontWeight: FontWeight.w800))) ]);
        }).toList(),
      )),
    ]));
  }

  Widget strategyChartCard() {
    var sum = 0.0;
    final spots = <FlSpot>[];
    for (var i = 0; i < trades.length; i++) {
      sum += numd(trades[i]['profit']);
      spots.add(FlSpot(i.toDouble(), sum));
    }
    return card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      rowTitle('Wynik strategii', symbol),
      const SizedBox(height: 8),
      Expanded(child: spots.length < 2 ? const Center(child: Text('Brak transakcji', style: TextStyle(color: Ui.muted))) : LineChart(LineChartData(gridData: FlGridData(show: true, getDrawingHorizontalLine: (_) => FlLine(color: Ui.border)), titlesData: const FlTitlesData(topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)), rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)), bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false))), borderData: FlBorderData(show: false), lineBarsData: [LineChartBarData(spots: spots, color: Ui.cyan, isCurved: true, dotData: const FlDotData(show: false))]))),
    ]));
  }

  Widget pnlCard() {
    final rows = daily.length > 16 ? daily.sublist(daily.length - 16) : daily;
    final vals = rows.map((e) => numd(e['net_profit'])).toList();
    return card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      rowTitle('Rozkład zysków / strat', '/api/daily'),
      const SizedBox(height: 8),
      Expanded(child: vals.isEmpty ? const Center(child: Text('Brak danych', style: TextStyle(color: Ui.muted))) : BarChart(BarChartData(gridData: FlGridData(show: true, getDrawingHorizontalLine: (_) => FlLine(color: Ui.border)), titlesData: const FlTitlesData(topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)), rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)), bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false))), borderData: FlBorderData(show: false), barGroups: [for (var i = 0; i < vals.length; i++) BarChartGroupData(x: i, barRods: [BarChartRodData(toY: vals[i], width: 8, color: vals[i] >= 0 ? Ui.green : Ui.red)])]))),
    ]));
  }

  Widget exposureCard() {
    final count = assets.isEmpty ? 1 : assets.length;
    final groups = <String, int>{};
    for (final a in assets) {
      final type = '${a['asset_type'] ?? 'Inne'}';
      groups[type] = (groups[type] ?? 0) + 1;
    }
    final colors = [Ui.cyan, Ui.green, Ui.orange, Ui.purple, Ui.red];
    return card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      rowTitle('Ekspozycja na rynki', 'wg liczby instrumentów'),
      const SizedBox(height: 14),
      ...groups.entries.toList().asMap().entries.take(5).map((x) {
        final pct = x.value.value / count;
        return Padding(padding: const EdgeInsets.only(bottom: 11), child: Row(children: [SizedBox(width: 85, child: Text(x.value.key, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 10))), Expanded(child: LinearProgressIndicator(minHeight: 9, value: pct, backgroundColor: Ui.panel2, valueColor: AlwaysStoppedAnimation(colors[x.key % colors.length]))), const SizedBox(width: 8), Text('${(pct * 100).toStringAsFixed(1)}%', style: const TextStyle(fontSize: 10))]));
      }),
      const Spacer(),
      Row(children: [Icon(Icons.public_rounded, color: Ui.cyan.withOpacity(.7), size: 40), const SizedBox(width: 12), const Expanded(child: Text('Krypto • Forex • Akcje • Metale • Energia', style: TextStyle(color: Ui.muted, fontSize: 10)))]),
    ]));
  }

  Widget portfolioPage() => detailShell('Portfel', [
    metric('Saldo', '${money(numd(portfolio['balance']))} PLN', Ui.green),
    metric('Wpłaty', '${money(numd(portfolio['total_deposited']))} PLN', Ui.cyan),
    metric('Wypłaty', '${money(numd(portfolio['total_withdrawn']))} PLN', Ui.orange),
    metric('Wynik', '${money(numd(portfolio['result']))} PLN', numd(portfolio['result']) >= 0 ? Ui.green : Ui.red),
    SizedBox(height: 320, child: equityCard()),
  ]);

  Widget marketsPage() => detailShell('Rynki', [
    card(SingleChildScrollView(scrollDirection: Axis.horizontal, child: DataTable(columns: const [DataColumn(label: Text('Symbol')), DataColumn(label: Text('Nazwa')), DataColumn(label: Text('Klasa')), DataColumn(label: Text('Provider')), DataColumn(label: Text('Cena')), DataColumn(label: Text('Pozycja'))], rows: assets.map((a) => DataRow(cells: [DataCell(Text('${a['symbol']}', style: const TextStyle(fontWeight: FontWeight.w800))), DataCell(Text('${a['name'] ?? '—'}')), DataCell(Text('${a['asset_type'] ?? '—'}')), DataCell(Text('${a['provider'] ?? '—'}')), DataCell(Text(fmt(numd(a['market_price'])))), DataCell(Text('${a['position'] ?? 'FLAT'}'))])).toList()))),
  ]);

  Widget strategyPage() {
    final s = map(status['strategy']);
    final p = map(status['performance']);
    final a = map(status['account']);
    return detailShell('Strategie', [
      Wrap(spacing: 10, runSpacing: 10, children: [metric('BUY RSI', fmt(numd(s['buy_rsi'])), Ui.cyan), metric('SELL RSI', fmt(numd(s['sell_rsi'])), Ui.cyan), metric('TIME', '${s['max_position_candles'] ?? '—'}', Ui.orange), metric('Profit Factor', display(p['profit_factor']), Ui.green), metric('Max DD', fmt(numd(a['max_drawdown'])), Ui.red)]),
      SizedBox(height: 300, child: strategyChartCard()),
    ]);
  }

  Widget tradesPage() => detailShell('Transakcje', [
    card(SingleChildScrollView(scrollDirection: Axis.horizontal, child: DataTable(columns: const [DataColumn(label: Text('#')), DataColumn(label: Text('Side')), DataColumn(label: Text('Entry')), DataColumn(label: Text('Exit')), DataColumn(label: Text('Qty')), DataColumn(label: Text('Profit')), DataColumn(label: Text('Reason'))], rows: trades.map((t) => DataRow(cells: [DataCell(Text('${t['trade_number'] ?? '—'}')), DataCell(Text('${t['side'] ?? '—'}')), DataCell(Text(fmt(numd(t['entry_price'])))), DataCell(Text(fmt(numd(t['exit_price'])))), DataCell(Text(fmt(numd(t['quantity'])))), DataCell(Text(signed(numd(t['profit'])), style: TextStyle(color: numd(t['profit']) >= 0 ? Ui.green : Ui.red, fontWeight: FontWeight.w800))), DataCell(Text('${t['exit_reason'] ?? '—'}'))])).toList()))),
  ]);

  Widget analyticsPage() => detailShell('Analizy', [
    Wrap(spacing: 10, runSpacing: 10, children: [SizedBox(width: 300, height: 260, child: strategyChartCard()), SizedBox(width: 300, height: 260, child: pnlCard()), SizedBox(width: 300, height: 260, child: exposureCard())]),
  ]);

  Widget alertsPage() {
    final list = alerts();
    return detailShell('Alerty', [
      card(list.isEmpty ? const Text('Brak aktywnych alertów systemowych.', style: TextStyle(color: Ui.green)) : Column(children: list.map((e) => ListTile(leading: const Icon(Icons.warning_amber_rounded, color: Ui.orange), title: Text(e.$1), subtitle: Text(e.$2), trailing: Text(e.$3, style: const TextStyle(color: Ui.red, fontWeight: FontWeight.w800)))).toList())),
    ]);
  }

  Widget settingsPage() => detailShell('Ustawienia', [
    card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [info('API', apiBaseUrl), info('Status', online ? 'ONLINE' : 'OFFLINE'), info('Instrument', symbol), info('Auto-refresh', '10 sekund'), info('AI', ai['available'] == true ? 'DOSTĘPNE' : 'NIEDOSTĘPNE')])),
  ]);

  Widget pendingPage(String title, String text) => detailShell(title, [card(Row(crossAxisAlignment: CrossAxisAlignment.start, children: [const Icon(Icons.info_outline_rounded, color: Ui.orange), const SizedBox(width: 10), Expanded(child: Text(text, style: const TextStyle(color: Ui.muted, height: 1.5))) ]))]);

  Widget detailShell(String title, List<Widget> children) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [Text(title, style: const TextStyle(fontSize: 25, fontWeight: FontWeight.w900)), const SizedBox(width: 14), if (assets.isNotEmpty) DropdownButton<String>(value: assets.any((a) => '${a['symbol']}' == symbol) ? symbol : null, items: assets.map((a) => DropdownMenuItem(value: '${a['symbol']}', child: Text('${a['symbol']}'))).toList(), onChanged: (v) { if (v != null) changeSymbol(v); }), const Spacer(), statusPill(online ? 'API ONLINE' : 'API OFFLINE', online ? Ui.green : Ui.red), IconButton(onPressed: refresh, icon: const Icon(Icons.refresh_rounded))]),
          const SizedBox(height: 14),
          ...children.expand((w) => [w, const SizedBox(height: 10)]),
        ],
      ),
    );
  }

  Widget card(Widget child) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Ui.panel,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Ui.border),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(.15), blurRadius: 14, offset: const Offset(0, 6))],
        ),
        child: child,
      );

  Widget metric(String title, String value, Color color) => SizedBox(
        width: 215,
        height: 100,
        child: card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(color: Ui.muted, fontSize: 11)), const Spacer(), Text(value, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900)), const SizedBox(height: 5), Container(width: 30, height: 3, color: color)])),
      );

  Widget rowTitle(String title, String sub) => Row(children: [Expanded(child: Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w900))), Text(sub, style: const TextStyle(color: Ui.muted, fontSize: 9))]);

  Widget statusPill(String text, Color color) => Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5), decoration: BoxDecoration(color: color.withOpacity(.1), border: Border.all(color: color.withOpacity(.7)), borderRadius: BorderRadius.circular(20)), child: Text(text, style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.w900)));

  Widget info(String title, String value) => Padding(padding: const EdgeInsets.symmetric(vertical: 5), child: Row(children: [Expanded(child: Text(title, style: const TextStyle(color: Ui.muted))), Flexible(child: Text(value, textAlign: TextAlign.right, style: const TextStyle(fontWeight: FontWeight.w800))) ]));

  List<(String, String, String)> alerts() {
    final result = <(String, String, String)>[];
    if (!online) result.add(('FastAPI', 'Brak połączenia z backendem', 'Wysoki'));
    if (market['stale'] == true) result.add((symbol, 'Dane rynku są stare', 'Wysoki'));
    if (ai['stale'] == true) result.add(('AI', 'Dane AI są stare', 'Średni'));
    if (ai.isNotEmpty && ai['available'] == false) result.add(('AI', 'Moduł AI niedostępny', 'Średni'));
    return result;
  }
}

Map<String, dynamic> map(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
List<Map<String, dynamic>> maps(dynamic v) => v is List ? v.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList() : <Map<String, dynamic>>[];
double numd(dynamic v) => v is num ? v.toDouble() : double.tryParse('$v') ?? 0.0;
String fmt(double v) => v.isFinite ? v.toStringAsFixed(2) : '—';
String signed(double v) => '${v > 0 ? '+' : ''}${fmt(v)}';
String display(dynamic v) => v == null || '$v' == 'null' ? '—' : (v is num ? fmt(v.toDouble()) : '$v');
String money(double v) {
  final negative = v < 0;
  final parts = v.abs().toStringAsFixed(2).split('.');
  final chars = parts[0].split('').reversed.toList();
  final out = <String>[];
  for (var i = 0; i < chars.length; i++) {
    if (i > 0 && i % 3 == 0) out.add(' ');
    out.add(chars[i]);
  }
  return '${negative ? '-' : ''}${out.reversed.join()},${parts[1]}';
}
