
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

/// AL Trading â€” nowoczesny dashboard desktop/web.
///
/// Wymaga:
///   flutter pub add fl_chart
///
/// Uruchom:
///   flutter run -d chrome
///
/// Dane w tym pliku sÄ… DEMO. W kolejnym kroku moĹĽna podpiÄ…Ä‡ je pod FastAPI
/// (/api/v1/portfolio, /api/v1/assets, /api/v1/portfolio/positions itd.).
class AlTradingDashboard extends StatefulWidget {
  const AlTradingDashboard({super.key});

  @override
  State<AlTradingDashboard> createState() => _AlTradingDashboardState();
}

class _AlTradingDashboardState extends State<AlTradingDashboard> {
  int selectedNav = 0;
  String selectedRange = '3M';

  static const bg = Color(0xFF07111E);
  static const panel = Color(0xFF0C1A2A);
  static const panel2 = Color(0xFF0F2235);
  static const border = Color(0xFF1C3953);
  static const text = Color(0xFFF2F7FF);
  static const muted = Color(0xFF91A6BC);
  static const cyan = Color(0xFF23B7FF);
  static const green = Color(0xFF26E3A7);
  static const red = Color(0xFFFF5C73);
  static const purple = Color(0xFF7B77FF);
  static const orange = Color(0xFFFFB34C);

  final List<_Position> positions = const [
    _Position('NVDA', 'BUY', 10, '420,15', '438,72', '17 534,42', 742.80, 4.43),
    _Position('BTC', 'BUY', 0.25, '238 450', '249 120', '24 912,00', 1067.00, 4.47),
    _Position('EUR/PLN', 'BUY', 10000, '4,2800', '4,3105', '43 105,00', 305.00, 0.71),
    _Position('GOLD', 'BUY', 2, '2 160,50', '2 201,30', '17 236,20', 318.98, 1.89),
    _Position('SPY', 'BUY', 5, '520,10', '528,76', '10 582,24', 173.20, 1.66),
    _Position('TSLA', 'SELL', 8, '177,30', '172,85', '5 673,25', 142.40, 2.53),
    _Position('ETH', 'BUY', 1.5, '3 680,20', '3 612,40', '21 987,36', -412.65, -1.84),
  ];

  final portfolioSpots = const [
    FlSpot(0, 94000),
    FlSpot(1, 96800),
    FlSpot(2, 100800),
    FlSpot(3, 103200),
    FlSpot(4, 101300),
    FlSpot(5, 102900),
    FlSpot(6, 104400),
    FlSpot(7, 105200),
    FlSpot(8, 106300),
    FlSpot(9, 108500),
    FlSpot(10, 112500),
    FlSpot(11, 111000),
    FlSpot(12, 113600),
    FlSpot(13, 115500),
    FlSpot(14, 114300),
    FlSpot(15, 118400),
    FlSpot(16, 116500),
    FlSpot(17, 120300),
    FlSpot(18, 118900),
    FlSpot(19, 121500),
    FlSpot(20, 120800),
    FlSpot(21, 125432),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: bg,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final desktop = constraints.maxWidth >= 1180;
            return Row(
              children: [
                if (desktop) _sidebar(),
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      children: [
                        _topSummary(),
                        const SizedBox(height: 14),
                        if (desktop)
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(flex: 7, child: _portfolioChart()),
                              const SizedBox(width: 14),
                              Expanded(flex: 3, child: _allocationCard()),
                              const SizedBox(width: 14),
                              Expanded(flex: 3, child: _marketMovers()),
                            ],
                          )
                        else ...[
                          _portfolioChart(),
                          const SizedBox(height: 14),
                          _allocationCard(),
                          const SizedBox(height: 14),
                          _marketMovers(),
                        ],
                        const SizedBox(height: 14),
                        if (desktop)
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(flex: 8, child: _positionsCard()),
                              const SizedBox(width: 14),
                              Expanded(
                                flex: 4,
                                child: Column(
                                  children: [
                                    _alertsCard(),
                                    const SizedBox(height: 14),
                                    _calendarCard(),
                                  ],
                                ),
                              ),
                            ],
                          )
                        else ...[
                          _positionsCard(),
                          const SizedBox(height: 14),
                          _alertsCard(),
                          const SizedBox(height: 14),
                          _calendarCard(),
                        ],
                        const SizedBox(height: 14),
                        if (desktop)
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(child: _strategyChart()),
                              const SizedBox(width: 14),
                              Expanded(child: _pnlChart()),
                              const SizedBox(width: 14),
                              Expanded(child: _exposureCard()),
                            ],
                          )
                        else ...[
                          _strategyChart(),
                          const SizedBox(height: 14),
                          _pnlChart(),
                          const SizedBox(height: 14),
                          _exposureCard(),
                        ],
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _sidebar() {
    final items = const [
      (Icons.dashboard_rounded, 'Dashboard'),
      (Icons.account_balance_wallet_outlined, 'Portfel'),
      (Icons.bar_chart_rounded, 'Rynki'),
      (Icons.auto_graph_rounded, 'Strategie'),
      (Icons.swap_horiz_rounded, 'Transakcje'),
      (Icons.analytics_outlined, 'Analizy'),
      (Icons.calendar_month_outlined, 'Kalendarz'),
      (Icons.notifications_none_rounded, 'Alerty'),
      (Icons.settings_outlined, 'Ustawienia'),
    ];

    return Container(
      width: 220,
      decoration: const BoxDecoration(
        color: Color(0xFF081522),
        border: Border(right: BorderSide(color: border)),
      ),
      child: Column(
        children: [
          const SizedBox(height: 22),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 18),
            child: Row(
              children: [
                _LogoMark(),
                SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'AL Trading',
                      style: TextStyle(
                        color: text,
                        fontWeight: FontWeight.w800,
                        fontSize: 21,
                      ),
                    ),
                    Text(
                      'Paper Trading (PLN)',
                      style: TextStyle(color: muted, fontSize: 12),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 22),
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 4),
              itemBuilder: (context, index) {
                final selected = selectedNav == index;
                return InkWell(
                  borderRadius: BorderRadius.circular(12),
                  onTap: () => setState(() => selectedNav = index),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 160),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    decoration: BoxDecoration(
                      color: selected ? const Color(0xFF102A40) : Colors.transparent,
                      borderRadius: BorderRadius.circular(12),
                      border: selected
                          ? Border.all(color: cyan.withOpacity(.35))
                          : null,
                    ),
                    child: Row(
                      children: [
                        Icon(items[index].$1, size: 20, color: selected ? cyan : muted),
                        const SizedBox(width: 12),
                        Text(
                          items[index].$2,
                          style: TextStyle(
                            color: selected ? text : const Color(0xFFC6D4E2),
                            fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                          ),
                        ),
                        const Spacer(),
                        if (items[index].$2 == 'Alerty')
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                            decoration: BoxDecoration(
                              color: red,
                              borderRadius: BorderRadius.circular(99),
                            ),
                            child: const Text('3', style: TextStyle(color: Colors.white, fontSize: 11)),
                          ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.circle, size: 9, color: green),
                      SizedBox(width: 8),
                      Text('Rynek aktywny', style: TextStyle(color: text, fontWeight: FontWeight.w700)),
                    ],
                  ),
                  const SizedBox(height: 10),
                  const Row(
                    children: [
                      Icon(Icons.circle, size: 9, color: green),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text('Wszystkie systemy online',
                            style: TextStyle(color: green, fontSize: 12)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  const Text('Paper Engine', style: TextStyle(color: muted, fontSize: 12)),
                  const SizedBox(height: 4),
                  const Text(
                    'REALISTIC_V2',
                    style: TextStyle(color: cyan, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 18),
                  Text(
                    'â€žRealny rynek. Wirtualny kapitaĹ‚.â€ť',
                    style: TextStyle(
                      color: Colors.white.withOpacity(.7),
                      fontStyle: FontStyle.italic,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _topSummary() {
    return _Card(
      padding: const EdgeInsets.all(16),
      child: LayoutBuilder(
        builder: (context, c) {
          final compact = c.maxWidth < 980;
          final tiles = [
            _mainBalance(),
            _metric('DzieĹ„', '+1 245,60', '+1,00%'),
            _metric('TydzieĹ„', '+3 120,85', '+2,55%'),
            _metric('MiesiÄ…c', '+8 742,31', '+7,49%'),
            _metric('ROI', '+12,34%', 'od poczÄ…tku'),
          ];
          if (compact) {
            return Wrap(
              spacing: 10,
              runSpacing: 10,
              children: tiles
                  .map((e) => SizedBox(width: c.maxWidth > 600 ? 220 : c.maxWidth, child: e))
                  .toList(),
            );
          }
          return Row(
            children: [
              Expanded(flex: 2, child: tiles[0]),
              ...tiles.skip(1).map((e) => Expanded(child: e)),
            ],
          );
        },
      ),
    );
  }

  Widget _mainBalance() {
    return Padding(
      padding: const EdgeInsets.only(right: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Text('WartoĹ›Ä‡ portfela (PLN)', style: TextStyle(color: muted, fontSize: 13)),
          SizedBox(height: 6),
          Text(
            '125 432,72',
            style: TextStyle(color: text, fontSize: 35, fontWeight: FontWeight.w900),
          ),
          SizedBox(height: 6),
          Row(
            children: [
              Icon(Icons.trending_up, color: green, size: 18),
              SizedBox(width: 5),
              Text('+2 834,19 (+2,31%)',
                  style: TextStyle(color: green, fontWeight: FontWeight.w800)),
            ],
          )
        ],
      ),
    );
  }

  Widget _metric(String title, String value, String sub) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 4),
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: panel2.withOpacity(.75),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: border.withOpacity(.75)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(color: muted, fontSize: 12)),
          const SizedBox(height: 8),
          Text(value,
              style: const TextStyle(color: green, fontSize: 17, fontWeight: FontWeight.w900)),
          const SizedBox(height: 3),
          Text(sub, style: const TextStyle(color: Color(0xFFA6B8C9), fontSize: 11)),
        ],
      ),
    );
  }

  Widget _portfolioChart() {
    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const _SectionTitle('WartoĹ›Ä‡ portfela'),
              const Spacer(),
              ...['1D', '1W', '1M', '3M', '1R', 'MAX'].map(
                (range) => Padding(
                  padding: const EdgeInsets.only(left: 4),
                  child: ChoiceChip(
                    selected: selectedRange == range,
                    label: Text(range),
                    onSelected: (_) => setState(() => selectedRange = range),
                    selectedColor: const Color(0xFF183A5A),
                    backgroundColor: Colors.transparent,
                    side: BorderSide(color: selectedRange == range ? cyan : border),
                    labelStyle: TextStyle(color: selectedRange == range ? Colors.white : muted),
                    showCheckmark: false,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 260,
            child: LineChart(
              LineChartData(
                minY: 90000,
                maxY: 130000,
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: true,
                  horizontalInterval: 10000,
                  getDrawingHorizontalLine: (_) =>
                      FlLine(color: border.withOpacity(.65), strokeWidth: 1),
                  getDrawingVerticalLine: (_) =>
                      FlLine(color: border.withOpacity(.45), strokeWidth: 1),
                ),
                borderData: FlBorderData(
                  show: true,
                  border: Border.all(color: border),
                ),
                titlesData: FlTitlesData(
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 48,
                      interval: 10000,
                      getTitlesWidget: (v, _) => Text(
                        '${(v / 1000).toStringAsFixed(0)}k',
                        style: const TextStyle(color: muted, fontSize: 10),
                      ),
                    ),
                  ),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      interval: 4,
                      getTitlesWidget: (v, _) => Text(
                        ['15 sty', '1 lut', '15 lut', '1 mar', '15 mar', '1 kwi'][v ~/ 4 % 6],
                        style: const TextStyle(color: muted, fontSize: 10),
                      ),
                    ),
                  ),
                ),
                lineTouchData: LineTouchData(
                  touchTooltipData: LineTouchTooltipData(
                    getTooltipItems: (items) => items
                        .map(
                          (e) => LineTooltipItem(
                            '${e.y.toStringAsFixed(0)} PLN',
                            const TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
                          ),
                        )
                        .toList(),
                  ),
                ),
                lineBarsData: [
                  LineChartBarData(
                    spots: portfolioSpots,
                    isCurved: true,
                    color: green,
                    barWidth: 2.4,
                    dotData: const FlDotData(show: false),
                    belowBarData: BarAreaData(
                      show: true,
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [green.withOpacity(.32), green.withOpacity(.02)],
                      ),
                    ),
                  )
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _allocationCard() {
    final sections = [
      PieChartSectionData(value: 38.2, color: cyan, radius: 24, showTitle: false),
      PieChartSectionData(value: 22.1, color: green, radius: 24, showTitle: false),
      PieChartSectionData(value: 15.4, color: purple, radius: 24, showTitle: false),
      PieChartSectionData(value: 12.8, color: orange, radius: 24, showTitle: false),
      PieChartSectionData(value: 7.6, color: const Color(0xFFFF884D), radius: 24, showTitle: false),
      PieChartSectionData(value: 3.9, color: const Color(0xFFC5D3E0), radius: 24, showTitle: false),
    ];

    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionTitle('Alokacja portfela'),
          const SizedBox(height: 14),
          SizedBox(
            height: 170,
            child: Stack(
              alignment: Alignment.center,
              children: [
                PieChart(
                  PieChartData(
                    centerSpaceRadius: 45,
                    sectionsSpace: 2,
                    sections: sections,
                  ),
                ),
                const Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('125 432', style: TextStyle(color: text, fontWeight: FontWeight.w900, fontSize: 18)),
                    Text('PLN', style: TextStyle(color: muted, fontSize: 11)),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          _legend(cyan, 'Akcje', '38,2%'),
          _legend(green, 'ETF', '22,1%'),
          _legend(purple, 'Krypto', '15,4%'),
          _legend(orange, 'Forex', '12,8%'),
          _legend(const Color(0xFFFF884D), 'Surowce', '7,6%'),
          _legend(const Color(0xFFC5D3E0), 'GotĂłwka', '3,9%'),
        ],
      ),
    );
  }

  Widget _legend(Color color, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Container(width: 9, height: 9, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          const SizedBox(width: 8),
          Expanded(child: Text(label, style: const TextStyle(color: Color(0xFFC9D7E4), fontSize: 12))),
          Text(value, style: const TextStyle(color: text, fontWeight: FontWeight.w700, fontSize: 12)),
        ],
      ),
    );
  }

  Widget _marketMovers() {
    const winners = [
      ('NVDA', '+4,21%'),
      ('BTC', '+3,84%'),
      ('EUR/PLN', '+2,11%'),
      ('GOLD', '+1,92%'),
      ('SPY', '+1,76%'),
    ];
    const losers = [
      ('TSLA', '-2,41%'),
      ('ETH', '-1,83%'),
      ('GBP/PLN', '-1,22%'),
      ('WTI', '-0,94%'),
      ('AAPL', '-0,71%'),
    ];

    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionTitle('Najlepsze aktywa (dzieĹ„)'),
          const SizedBox(height: 8),
          ...winners.map((e) => _mover(e.$1, e.$2, true)),
          const SizedBox(height: 14),
          const _SectionTitle('NajsĹ‚absze aktywa (dzieĹ„)'),
          const SizedBox(height: 8),
          ...losers.map((e) => _mover(e.$1, e.$2, false)),
        ],
      ),
    );
  }

  Widget _mover(String symbol, String pct, bool positive) {
    return Container(
      margin: const EdgeInsets.only(bottom: 5),
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 7),
      decoration: BoxDecoration(
        color: const Color(0xFF0A1725),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 10,
            backgroundColor: positive ? green.withOpacity(.15) : red.withOpacity(.15),
            child: Text(symbol.characters.first,
                style: TextStyle(color: positive ? green : red, fontSize: 10, fontWeight: FontWeight.w900)),
          ),
          const SizedBox(width: 8),
          Expanded(child: Text(symbol, style: const TextStyle(color: text, fontWeight: FontWeight.w700, fontSize: 12))),
          Text(pct,
              style: TextStyle(color: positive ? green : red, fontWeight: FontWeight.w800, fontSize: 12)),
        ],
      ),
    );
  }

  Widget _positionsCard() {
    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              _SectionTitle('Otwarte pozycje'),
              SizedBox(width: 8),
              _CountBadge('7'),
            ],
          ),
          const SizedBox(height: 10),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              headingRowHeight: 38,
              dataRowMinHeight: 38,
              dataRowMaxHeight: 44,
              horizontalMargin: 8,
              columnSpacing: 28,
              headingTextStyle: const TextStyle(color: muted, fontSize: 11, fontWeight: FontWeight.w700),
              dataTextStyle: const TextStyle(color: Color(0xFFD6E1EC), fontSize: 12),
              columns: const [
                DataColumn(label: Text('Symbol')),
                DataColumn(label: Text('Typ')),
                DataColumn(label: Text('IloĹ›Ä‡')),
                DataColumn(label: Text('Cena otwarcia')),
                DataColumn(label: Text('Cena bieĹĽÄ…ca')),
                DataColumn(label: Text('WartoĹ›Ä‡ (PLN)')),
                DataColumn(label: Text('Zysk/Strata')),
                DataColumn(label: Text('Zmiana %')),
              ],
              rows: positions
                  .map(
                    (p) => DataRow(
                      cells: [
                        DataCell(Text(p.symbol, style: const TextStyle(color: text, fontWeight: FontWeight.w800))),
                        DataCell(_sideBadge(p.side)),
                        DataCell(Text('${p.qty}')),
                        DataCell(Text(p.entry)),
                        DataCell(Text(p.current)),
                        DataCell(Text(p.valuePln)),
                        DataCell(
                          Text(
                            '${p.pnl >= 0 ? '+' : ''}${p.pnl.toStringAsFixed(2)} PLN',
                            style: TextStyle(
                              color: p.pnl >= 0 ? green : red,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                        DataCell(
                          Text(
                            '${p.pct >= 0 ? '+' : ''}${p.pct.toStringAsFixed(2)}%',
                            style: TextStyle(
                              color: p.pct >= 0 ? green : red,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                      ],
                    ),
                  )
                  .toList(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _sideBadge(String side) {
    final buy = side == 'BUY';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: (buy ? green : red).withOpacity(.14),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: (buy ? green : red).withOpacity(.45)),
      ),
      child: Text(
        side,
        style: TextStyle(color: buy ? green : red, fontSize: 10, fontWeight: FontWeight.w900),
      ),
    );
  }

  Widget _alertsCard() {
    const alerts = [
      ('NVDA', 'SygnaĹ‚ kupna', 'Wybicie z konsolidacji na H1', '14:12', true),
      ('EUR/PLN', 'Alert ceny', 'Kurs przekroczyĹ‚ 4,3100', '13:48', true),
      ('BTC', 'SygnaĹ‚ techniczny', 'RSI poniĹĽej 30 â€” moĹĽliwe odbicie', '12:31', true),
    ];
    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(children: [_SectionTitle('SygnaĹ‚y i alerty'), SizedBox(width: 8), _CountBadge('3')]),
          const SizedBox(height: 8),
          ...alerts.map(
            (a) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const CircleAvatar(
                    radius: 16,
                    backgroundColor: Color(0xFF12324A),
                    child: Icon(Icons.notifications_active_outlined, color: cyan, size: 16),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(a.$1, style: const TextStyle(color: text, fontWeight: FontWeight.w800, fontSize: 12)),
                            const SizedBox(width: 8),
                            Text(a.$2, style: const TextStyle(color: green, fontWeight: FontWeight.w700, fontSize: 11)),
                          ],
                        ),
                        const SizedBox(height: 3),
                        Text(a.$3, style: const TextStyle(color: muted, fontSize: 10)),
                      ],
                    ),
                  ),
                  Text(a.$4, style: const TextStyle(color: muted, fontSize: 10)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _calendarCard() {
    const events = [
      ('14:30', 'USD', 'CPI (r/r)', 'Wysoki'),
      ('16:00', 'EUR', 'PrzemĂłwienie EBC', 'Wysoki'),
      ('20:00', 'USD', 'ProtokĂłĹ‚ FOMC', 'Wysoki'),
    ];
    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionTitle('Kalendarz makroekonomiczny'),
          const SizedBox(height: 8),
          ...events.map(
            (e) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 7),
              child: Row(
                children: [
                  SizedBox(width: 42, child: Text(e.$1, style: const TextStyle(color: text, fontSize: 11))),
                  SizedBox(width: 40, child: Text(e.$2, style: const TextStyle(color: cyan, fontSize: 11, fontWeight: FontWeight.w700))),
                  Expanded(child: Text(e.$3, style: const TextStyle(color: Color(0xFFC8D4E1), fontSize: 11))),
                  Text(e.$4, style: const TextStyle(color: red, fontSize: 11, fontWeight: FontWeight.w700)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _strategyChart() {
    const a = [
      FlSpot(0, 0), FlSpot(1, 1), FlSpot(2, 3), FlSpot(3, 2), FlSpot(4, 5),
      FlSpot(5, 7), FlSpot(6, 5), FlSpot(7, 8), FlSpot(8, 11), FlSpot(9, 9),
      FlSpot(10, 13), FlSpot(11, 16), FlSpot(12, 14),
    ];
    const b = [
      FlSpot(0, 0), FlSpot(1, -1), FlSpot(2, 1), FlSpot(3, 3), FlSpot(4, 4),
      FlSpot(5, 5), FlSpot(6, 6), FlSpot(7, 5), FlSpot(8, 7), FlSpot(9, 8),
      FlSpot(10, 9), FlSpot(11, 9), FlSpot(12, 10),
    ];
    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionTitle('Wynik strategii'),
          const SizedBox(height: 14),
          SizedBox(
            height: 180,
            child: LineChart(
              LineChartData(
                minY: -4,
                maxY: 20,
                gridData: FlGridData(
                  show: true,
                  horizontalInterval: 5,
                  getDrawingHorizontalLine: (_) => FlLine(color: border.withOpacity(.6), strokeWidth: 1),
                  getDrawingVerticalLine: (_) => FlLine(color: border.withOpacity(.35), strokeWidth: 1),
                ),
                titlesData: const FlTitlesData(
                  topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 28, interval: 5)),
                ),
                borderData: FlBorderData(show: false),
                lineBarsData: [
                  LineChartBarData(spots: a, isCurved: true, color: cyan, barWidth: 2.2, dotData: const FlDotData(show: false)),
                  LineChartBarData(spots: b, isCurved: true, color: purple, barWidth: 2.0, dotData: const FlDotData(show: false)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _pnlChart() {
    const vals = [-1200.0, -400.0, 1800.0, 350.0, 3100.0, -1100.0, 800.0, 2200.0, 4100.0, 1500.0, 2800.0, -2400.0, 900.0, 1900.0, 4800.0, 2600.0, -2100.0];
    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionTitle('RozkĹ‚ad zyskĂłw / strat'),
          const SizedBox(height: 14),
          SizedBox(
            height: 180,
            child: BarChart(
              BarChartData(
                minY: -3000,
                maxY: 6000,
                gridData: FlGridData(
                  show: true,
                  horizontalInterval: 2000,
                  getDrawingHorizontalLine: (_) => FlLine(color: border.withOpacity(.55), strokeWidth: 1),
                ),
                borderData: FlBorderData(show: false),
                titlesData: const FlTitlesData(
                  topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 36, interval: 2000)),
                ),
                barGroups: [
                  for (var i = 0; i < vals.length; i++)
                    BarChartGroupData(
                      x: i,
                      barRods: [
                        BarChartRodData(
                          toY: vals[i],
                          width: 8,
                          color: vals[i] >= 0 ? green : red,
                          borderRadius: BorderRadius.circular(2),
                        )
                      ],
                    )
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          const Row(
            children: [
              Expanded(child: _MiniStat('Zyskowne dni', '12 (80%)', green)),
              Expanded(child: _MiniStat('Stratne dni', '3 (20%)', red)),
              Expanded(child: _MiniStat('Ĺšr. zysk', '+1 245,60', green)),
              Expanded(child: _MiniStat('Ĺšr. strata', '-842,30', red)),
            ],
          )
        ],
      ),
    );
  }

  Widget _exposureCard() {
    const rows = [
      ('Crypto', 42.1),
      ('Akcje', 24.7),
      ('Forex', 18.3),
      ('Metale', 8.9),
      ('Energia', 6.0),
    ];

    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionTitle('Ekspozycja na rynki'),
          const SizedBox(height: 18),
          ...rows.map(
            (r) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 7),
              child: Row(
                children: [
                  SizedBox(width: 58, child: Text(r.$1, style: const TextStyle(color: Color(0xFFD0DCE8), fontSize: 11))),
                  Expanded(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(99),
                      child: LinearProgressIndicator(
                        minHeight: 10,
                        value: r.$2 / 100,
                        backgroundColor: const Color(0xFF122A3D),
                        valueColor: const AlwaysStoppedAnimation(cyan),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  SizedBox(width: 42, child: Text('${r.$2}%', textAlign: TextAlign.right, style: const TextStyle(color: text, fontSize: 11))),
                ],
              ),
            ),
          ),
          const SizedBox(height: 18),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF0A1725),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: border),
            ),
            child: const Row(
              children: [
                Icon(Icons.security_rounded, color: green, size: 18),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Global RiskGuard: OK',
                    style: TextStyle(color: green, fontWeight: FontWeight.w800, fontSize: 12),
                  ),
                ),
                Text('HALT: OFF', style: TextStyle(color: muted, fontSize: 11)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Card extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;

  const _Card({
    required this.child,
    this.padding = const EdgeInsets.all(14),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: padding,
      decoration: BoxDecoration(
        color: _AlTradingDashboardState.panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _AlTradingDashboardState.border),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(.18),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: child,
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: _AlTradingDashboardState.text,
        fontSize: 15,
        fontWeight: FontWeight.w800,
      ),
    );
  }
}

class _CountBadge extends StatelessWidget {
  final String text;
  const _CountBadge(this.text);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: _AlTradingDashboardState.red,
        borderRadius: BorderRadius.circular(99),
      ),
      child: Text(text, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 10)),
    );
  }
}

class _MiniStat extends StatelessWidget {
  final String title;
  final String value;
  final Color color;

  const _MiniStat(this.title, this.value, this.color);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(color: _AlTradingDashboardState.muted, fontSize: 9)),
          const SizedBox(height: 4),
          Text(value, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}

class _LogoMark extends StatelessWidget {
  const _LogoMark();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 42,
      height: 42,
      child: Stack(
        children: [
          Positioned(
            left: 4,
            top: 2,
            child: Transform.rotate(
              angle: .5,
              child: Container(
                width: 13,
                height: 36,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(colors: [_AlTradingDashboardState.cyan, Color(0xFF246BFF)]),
                  borderRadius: BorderRadius.circular(3),
                ),
              ),
            ),
          ),
          Positioned(
            right: 5,
            bottom: 2,
            child: Transform.rotate(
              angle: -.55,
              child: Container(
                width: 12,
                height: 27,
                decoration: BoxDecoration(
                  color: const Color(0xFF5AC8FF),
                  borderRadius: BorderRadius.circular(3),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Position {
  final String symbol;
  final String side;
  final double qty;
  final String entry;
  final String current;
  final String valuePln;
  final double pnl;
  final double pct;

  const _Position(
    this.symbol,
    this.side,
    this.qty,
    this.entry,
    this.current,
    this.valuePln,
    this.pnl,
    this.pct,
  );
}

/// Minimalny przykĹ‚ad uruchomienia.
///
/// MoĹĽesz uĹĽyÄ‡ wĹ‚asnego main.dart i ustawiÄ‡:
/// home: const AlTradingDashboard()
class AlTradingPreviewApp extends StatelessWidget {
  const AlTradingPreviewApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'AL Trading',
      theme: ThemeData(
        brightness: Brightness.dark,
        useMaterial3: true,
        scaffoldBackgroundColor: _AlTradingDashboardState.bg,
        fontFamily: 'Arial',
        colorScheme: const ColorScheme.dark(
          primary: _AlTradingDashboardState.cyan,
          secondary: _AlTradingDashboardState.green,
          surface: _AlTradingDashboardState.panel,
        ),
        dividerColor: _AlTradingDashboardState.border,
      ),
      home: const AlTradingDashboard(),
    );
  }
}

