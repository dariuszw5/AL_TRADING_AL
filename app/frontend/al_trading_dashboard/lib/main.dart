import 'dart:async';
import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import 'api_client.dart';

void main() {
  runApp(const AlTradingWindowsApp());
}

class AlTradingWindowsApp extends StatelessWidget {
  const AlTradingWindowsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'AL Trading',
      theme: ThemeData(
        brightness: Brightness.dark,
        useMaterial3: true,
        scaffoldBackgroundColor: AppColors.bg,
        colorScheme: const ColorScheme.dark(
          primary: AppColors.cyan,
          secondary: AppColors.green,
          surface: AppColors.panel,
        ),
        dividerColor: AppColors.border,
      ),
      home: const ConnectedProDashboard(),
    );
  }
}

class AppColors {
  static const bg = Color(0xFF07111E);
  static const panel = Color(0xFF0C1A2A);
  static const panel2 = Color(0xFF102338);
  static const border = Color(0xFF1C3953);
  static const text = Color(0xFFF3F8FF);
  static const muted = Color(0xFF91A6BC);
  static const cyan = Color(0xFF29B6F6);
  static const green = Color(0xFF29E6A7);
  static const red = Color(0xFFFF617A);
  static const purple = Color(0xFF827BFF);
  static const orange = Color(0xFFFFB74D);
}

class NavItem {
  final IconData icon;
  final String label;
  const NavItem(this.icon, this.label);
}

class ConnectedProDashboard extends StatefulWidget {
  const ConnectedProDashboard({super.key});

  @override
  State<ConnectedProDashboard> createState() => _ConnectedProDashboardState();
}

class _ConnectedProDashboardState extends State<ConnectedProDashboard> {
  final AlTradingApi api = AlTradingApi();

  final navItems = const [
    NavItem(Icons.dashboard_rounded, 'Pulpit'),
    NavItem(Icons.account_balance_wallet_outlined, 'Portfel'),
    NavItem(Icons.candlestick_chart_rounded, 'Rynki'),
    NavItem(Icons.auto_graph_rounded, 'Strategie'),
    NavItem(Icons.swap_horiz_rounded, 'Transakcje'),
    NavItem(Icons.analytics_outlined, 'Analizy'),
    NavItem(Icons.calendar_month_outlined, 'Kalendarz'),
    NavItem(Icons.notifications_none_rounded, 'Alerty'),
    NavItem(Icons.settings_outlined, 'Ustawienia'),
  ];

  int selectedIndex = 0;
  String selectedSymbol = 'BTCUSDT';
  String selectedRange = '3M';

  bool paperUiEnabled = true;
  bool alertsEnabled = true;
  bool compactTables = false;

  bool loading = true;
  bool connected = false;
  bool refreshInProgress = false;
  String? errorMessage;
  DateTime? lastRefresh;

  List<Map<String, dynamic>> assets = [];
  List<Map<String, dynamic>> trades = [];
  List<Map<String, dynamic>> daily = [];
  Map<String, dynamic> status = {};
  Map<String, dynamic> equity = {};
  Map<String, dynamic> market = {};
  Map<String, dynamic> ai = {};
  Map<String, dynamic> portfolio = {};

  Timer? refreshTimer;

  @override
  void initState() {
    super.initState();
    _refreshAll(firstLoad: true);
    refreshTimer = Timer.periodic(
      const Duration(seconds: 10),
      (_) => _refreshAll(),
    );
  }

  @override
  void dispose() {
    refreshTimer?.cancel();
    api.close();
    super.dispose();
  }

  Future<void> _refreshAll({bool firstLoad = false}) async {
    if (refreshInProgress) return;
    refreshInProgress = true;

    if (firstLoad && mounted) {
      setState(() => loading = true);
    }

    try {
      final common = await Future.wait<dynamic>([
        api.assets(),
        api.userPortfolio(),
        api.aiStatus(),
        api.daily(),
      ]);

      final nextAssets = List<Map<String, dynamic>>.from(common[0] as List);
      final symbols = nextAssets.map((a) => '${a['symbol'] ?? ''}').toSet();

      if (!symbols.contains(selectedSymbol) && symbols.isNotEmpty) {
        selectedSymbol = symbols.first;
      }

      final details = await Future.wait<dynamic>([
        api.status(selectedSymbol),
        api.trades(selectedSymbol),
        api.equity(selectedSymbol),
        api.market(selectedSymbol),
      ]);

      if (!mounted) return;

      setState(() {
        assets = nextAssets;
        portfolio = Map<String, dynamic>.from(common[1] as Map);
        ai = Map<String, dynamic>.from(common[2] as Map);
        daily = List<Map<String, dynamic>>.from(common[3] as List);

        status = Map<String, dynamic>.from(details[0] as Map);
        trades = List<Map<String, dynamic>>.from(details[1] as List);
        equity = Map<String, dynamic>.from(details[2] as Map);
        market = Map<String, dynamic>.from(details[3] as Map);

        connected = true;
        errorMessage = null;
        loading = false;
        lastRefresh = DateTime.now();
      });
    } catch (error) {
      if (!mounted) return;

      setState(() {
        connected = false;
        errorMessage = '$error';
        loading = false;
      });
    } finally {
      refreshInProgress = false;
    }
  }

  Future<void> _changeSymbol(String symbol) async {
    if (symbol == selectedSymbol) return;

    setState(() {
      selectedSymbol = symbol;
      loading = true;
    });

    await _refreshAll(firstLoad: true);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bg,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final desktop = constraints.maxWidth >= 1080;

            return Row(
              children: [
                if (desktop) _buildSidebar(),
                Expanded(
                  child: Column(
                    children: [
                      _buildTopBar(desktop),
                      if (!connected && errorMessage != null)
                        _connectionBanner(),
                      Expanded(
                        child: loading && assets.isEmpty
                            ? const Center(child: CircularProgressIndicator())
                            : AnimatedSwitcher(
                                duration: const Duration(milliseconds: 220),
                                child: _pageForIndex(),
                              ),
                      ),
                    ],
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildTopBar(bool desktop) {
    return Container(
      height: 68,
      padding: const EdgeInsets.symmetric(horizontal: 18),
      decoration: const BoxDecoration(
        color: Color(0xFF091624),
        border: Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: Row(
        children: [
          if (!desktop)
            PopupMenuButton<int>(
              tooltip: 'Menu',
              icon: const Icon(Icons.menu_rounded, color: AppColors.text),
              onSelected: (index) => setState(() => selectedIndex = index),
              itemBuilder: (_) => [
                for (int i = 0; i < navItems.length; i++)
                  PopupMenuItem<int>(
                    value: i,
                    child: Row(
                      children: [
                        Icon(navItems[i].icon, size: 19),
                        const SizedBox(width: 10),
                        Text(navItems[i].label),
                      ],
                    ),
                  ),
              ],
            ),
          Text(
            navItems[selectedIndex].label,
            style: const TextStyle(
              color: AppColors.text,
              fontSize: 20,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(width: 18),
          if (assets.isNotEmpty)
            DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value:
                    assets.any(
                      (asset) => '${asset['symbol']}' == selectedSymbol,
                    )
                    ? selectedSymbol
                    : null,
                dropdownColor: AppColors.panel2,
                borderRadius: BorderRadius.circular(12),
                iconEnabledColor: AppColors.cyan,
                style: const TextStyle(
                  color: AppColors.text,
                  fontWeight: FontWeight.w800,
                ),
                items: assets
                    .map(
                      (asset) => DropdownMenuItem<String>(
                        value: '${asset['symbol']}',
                        child: Text('${asset['symbol']}'),
                      ),
                    )
                    .toList(),
                onChanged: (value) {
                  if (value != null) {
                    _changeSymbol(value);
                  }
                },
              ),
            ),
          const Spacer(),
          _statusPill(
            paperUiEnabled ? 'PAPER LIVE' : 'PAPER UI STOP',
            paperUiEnabled ? AppColors.green : AppColors.orange,
          ),
          const SizedBox(width: 8),
          _statusPill(
            connected ? 'API ONLINE' : 'API OFFLINE',
            connected ? AppColors.green : AppColors.red,
          ),
          const SizedBox(width: 8),
          _statusPill(
            market['stale'] == true ? 'DANE STARE' : 'DANE API',
            market['stale'] == true ? AppColors.orange : AppColors.cyan,
          ),
          const SizedBox(width: 10),
          IconButton(
            tooltip: 'Odśwież dane',
            onPressed: refreshInProgress ? null : () => _refreshAll(),
            icon: refreshInProgress
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh_rounded, color: AppColors.muted),
          ),
          IconButton(
            tooltip: 'Alerty',
            onPressed: () => setState(() => selectedIndex = 7),
            icon: Badge(
              isLabelVisible: _derivedAlerts().isNotEmpty,
              label: Text('${_derivedAlerts().length}'),
              child: const Icon(
                Icons.notifications_none_rounded,
                color: AppColors.muted,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSidebar() {
    return Container(
      width: 228,
      decoration: const BoxDecoration(
        color: Color(0xFF081522),
        border: Border(right: BorderSide(color: AppColors.border)),
      ),
      child: Column(
        children: [
          const SizedBox(height: 20),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 18),
            child: Row(
              children: [
                _Logo(),
                SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'AL Trading',
                      style: TextStyle(
                        color: AppColors.text,
                        fontSize: 21,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    Text(
                      'Wirtualny kapitał • PLN',
                      style: TextStyle(color: AppColors.muted, fontSize: 11),
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
              itemCount: navItems.length,
              separatorBuilder: (_, __) => const SizedBox(height: 4),
              itemBuilder: (context, index) {
                final selected = index == selectedIndex;

                return InkWell(
                  borderRadius: BorderRadius.circular(12),
                  onTap: () => setState(() => selectedIndex = index),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 12,
                    ),
                    decoration: BoxDecoration(
                      color: selected
                          ? const Color(0xFF102B41)
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(12),
                      border: selected
                          ? Border.all(color: AppColors.cyan.withOpacity(.35))
                          : null,
                    ),
                    child: Row(
                      children: [
                        Icon(
                          navItems[index].icon,
                          size: 20,
                          color: selected ? AppColors.cyan : AppColors.muted,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            navItems[index].label,
                            style: TextStyle(
                              color: selected
                                  ? AppColors.text
                                  : const Color(0xFFC5D4E2),
                              fontWeight: selected
                                  ? FontWeight.w800
                                  : FontWeight.w500,
                            ),
                          ),
                        ),
                        if (index == 7 && _derivedAlerts().isNotEmpty)
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 7,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: AppColors.red,
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Text(
                              '${_derivedAlerts().length}',
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w800,
                                fontSize: 10,
                              ),
                            ),
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
            child: AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.circle,
                        size: 9,
                        color: connected ? AppColors.green : AppColors.red,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        connected ? 'System połączony' : 'Brak API',
                        style: const TextStyle(
                          color: AppColors.text,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'API: ${api.baseUrl}',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: AppColors.muted,
                      fontSize: 10,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    'Instrument: $selectedSymbol',
                    style: const TextStyle(color: AppColors.cyan, fontSize: 11),
                  ),
                  if (lastRefresh != null) ...[
                    const SizedBox(height: 5),
                    Text(
                      'Odświeżono: ${_time(lastRefresh!)}',
                      style: const TextStyle(
                        color: AppColors.muted,
                        fontSize: 10,
                      ),
                    ),
                  ],
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: () => _showSystemDialog(),
                      icon: const Icon(
                        Icons.health_and_safety_outlined,
                        size: 17,
                      ),
                      label: const Text('Stan systemu'),
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

  Widget _connectionBanner() {
    return Container(
      width: double.infinity,
      color: AppColors.red.withOpacity(.12),
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
      child: Row(
        children: [
          const Icon(Icons.cloud_off_rounded, color: AppColors.red, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              errorMessage ?? 'Brak połączenia z FastAPI',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: AppColors.red, fontSize: 11),
            ),
          ),
          TextButton(
            onPressed: () => _refreshAll(),
            child: const Text('Ponów'),
          ),
        ],
      ),
    );
  }

  Widget _pageForIndex() {
    switch (selectedIndex) {
      case 0:
        return _dashboardPage();
      case 1:
        return _portfolioPage();
      case 2:
        return _marketsPage();
      case 3:
        return _strategiesPage();
      case 4:
        return _transactionsPage();
      case 5:
        return _analyticsPage();
      case 6:
        return _calendarPage();
      case 7:
        return _alertsPage();
      case 8:
        return _settingsPage();
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _dashboardPage() {
    final account = _map(status['account']);
    final performance = _map(status['performance']);
    final strategy = _map(status['strategy']);
    final position = _map(status['position']);
    final portfolioBalance = _num(portfolio['balance']);
    final marketPoints = _listOfMaps(market['points']);
    final lastClose = marketPoints.isNotEmpty
        ? _num(marketPoints.last['close'])
        : _num(account['market_price']);

    return PageShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PageHeading(
            'Pulpit — $selectedSymbol',
            'Nowoczesny panel paper trading • dane z Twojego FastAPI • automatyczne odświeżanie co 10 s.',
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Wartość portfela (PLN)',
                  '${_money(portfolioBalance)} PLN',
                  'źródło: /api/user-portfolio',
                  AppColors.green,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Saldo silnika',
                  _format(_num(account['balance'])),
                  'wartość natywna API',
                  AppColors.cyan,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Wynik silnika',
                  _signed(_num(account['net_profit'])),
                  'bez sztucznego FX',
                  _num(account['net_profit']) >= 0
                      ? AppColors.green
                      : AppColors.red,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Cena rynkowa',
                  _format(lastClose),
                  '${strategy['quote'] ?? ''}',
                  AppColors.cyan,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Win rate',
                  '${_format(_num(performance['win_rate']))}%',
                  '${performance['trades'] ?? 0} transakcji',
                  AppColors.green,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (context, constraints) {
              if (constraints.maxWidth >= 1180) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 7, child: _portfolioValueChart()),
                    const SizedBox(width: 14),
                    Expanded(flex: 3, child: _assetClassDonut()),
                    const SizedBox(width: 14),
                    Expanded(flex: 3, child: _marketStatusCard()),
                  ],
                );
              }

              return Column(
                children: [
                  _portfolioValueChart(),
                  const SizedBox(height: 14),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(child: _assetClassDonut()),
                      const SizedBox(width: 14),
                      Expanded(child: _marketStatusCard()),
                    ],
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 14),
          _openPositionsCard(),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (context, constraints) {
              if (constraints.maxWidth >= 1100) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: _tradePerformanceMiniChart()),
                    const SizedBox(width: 14),
                    Expanded(child: _dailyPnlMiniChart()),
                    const SizedBox(width: 14),
                    Expanded(
                      child: _systemHealthCard(
                        account,
                        performance,
                        strategy,
                        position,
                      ),
                    ),
                  ],
                );
              }

              return Column(
                children: [
                  _tradePerformanceMiniChart(),
                  const SizedBox(height: 14),
                  _dailyPnlMiniChart(),
                  const SizedBox(height: 14),
                  _systemHealthCard(account, performance, strategy, position),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _portfolioValueChart() {
    final equityPoints = _listOfMaps(equity['points']);
    final spots = <FlSpot>[];

    if (equityPoints.length >= 2) {
      for (final point in equityPoints) {
        spots.add(FlSpot(_num(point['index']), _num(point['balance'])));
      }
    } else {
      final marketPoints = _listOfMaps(market['points']);
      for (int i = 0; i < marketPoints.length; i++) {
        spots.add(FlSpot(i.toDouble(), _num(marketPoints[i]['close'])));
      }
    }

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const SectionTitle('Wartość / przebieg kapitału'),
              const Spacer(),
              ...['1D', '1T', '1M', '3M', '1R', 'MAX'].map(
                (range) => Padding(
                  padding: const EdgeInsets.only(left: 5),
                  child: ChoiceChip(
                    selected: selectedRange == range,
                    label: Text(range),
                    onSelected: (_) {
                      setState(() => selectedRange = range);
                    },
                    showCheckmark: false,
                    selectedColor: const Color(0xFF173A58),
                    backgroundColor: Colors.transparent,
                    side: BorderSide(
                      color: selectedRange == range
                          ? AppColors.cyan
                          : AppColors.border,
                    ),
                    labelStyle: TextStyle(
                      color: selectedRange == range
                          ? AppColors.text
                          : AppColors.muted,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (spots.length < 2)
            const SizedBox(
              height: 285,
              child: Center(
                child: Text(
                  'Brak wystarczających danych do wykresu.',
                  style: TextStyle(color: AppColors.muted),
                ),
              ),
            )
          else
            SizedBox(
              height: 285,
              child: LineChart(
                LineChartData(
                  gridData: FlGridData(
                    show: true,
                    getDrawingHorizontalLine: (_) => FlLine(
                      color: AppColors.border.withOpacity(.62),
                      strokeWidth: 1,
                    ),
                    getDrawingVerticalLine: (_) => FlLine(
                      color: AppColors.border.withOpacity(.28),
                      strokeWidth: 1,
                    ),
                  ),
                  borderData: FlBorderData(
                    show: true,
                    border: Border.all(color: AppColors.border),
                  ),
                  titlesData: const FlTitlesData(
                    topTitles: AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    rightTitles: AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 58,
                      ),
                    ),
                  ),
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      color: AppColors.green,
                      barWidth: 2.5,
                      dotData: const FlDotData(show: false),
                      belowBarData: BarAreaData(
                        show: true,
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            AppColors.green.withOpacity(.30),
                            AppColors.green.withOpacity(.02),
                          ],
                        ),
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

  Widget _assetClassDonut() {
    final counts = <String, int>{};

    for (final asset in assets) {
      final type = '${asset['asset_type'] ?? 'Inne'}';
      counts[type] = (counts[type] ?? 0) + 1;
    }

    final entries = counts.entries.toList();
    final colors = [
      AppColors.cyan,
      AppColors.green,
      AppColors.purple,
      AppColors.orange,
      AppColors.red,
      const Color(0xFFB5C6D8),
    ];

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Struktura obsługiwanych rynków'),
          const SizedBox(height: 3),
          const Text(
            'To udział liczby instrumentów, nie alokacja kapitału.',
            style: TextStyle(color: AppColors.muted, fontSize: 10),
          ),
          const SizedBox(height: 10),
          SizedBox(
            height: 165,
            child: entries.isEmpty
                ? const Center(
                    child: Text(
                      'Brak aktywów',
                      style: TextStyle(color: AppColors.muted),
                    ),
                  )
                : PieChart(
                    PieChartData(
                      centerSpaceRadius: 43,
                      sectionsSpace: 2,
                      sections: [
                        for (int i = 0; i < entries.length; i++)
                          PieChartSectionData(
                            value: entries[i].value.toDouble(),
                            color: colors[i % colors.length],
                            title: '',
                            radius: 24,
                          ),
                      ],
                    ),
                  ),
          ),
          ...[
            for (int i = 0; i < entries.length; i++)
              LegendRow(
                colors[i % colors.length],
                entries[i].key,
                '${entries[i].value}',
              ),
          ],
        ],
      ),
    );
  }

  Widget _marketStatusCard() {
    final shown = assets.take(6).toList();

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Status rynków'),
          const SizedBox(height: 10),
          if (shown.isEmpty)
            const Text(
              'Brak danych z /api/assets.',
              style: TextStyle(color: AppColors.muted),
            )
          else
            ...shown.map((asset) {
              final symbol = '${asset['symbol'] ?? '—'}';
              final provider = '${asset['provider'] ?? '—'}';
              final position = '${asset['position'] ?? 'FLAT'}';

              return Container(
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFF0A1725),
                  borderRadius: BorderRadius.circular(9),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            symbol,
                            style: const TextStyle(
                              color: AppColors.text,
                              fontWeight: FontWeight.w800,
                              fontSize: 12,
                            ),
                          ),
                          Text(
                            provider,
                            style: const TextStyle(
                              color: AppColors.muted,
                              fontSize: 9,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Text(
                      position,
                      style: TextStyle(
                        color: position == 'FLAT'
                            ? AppColors.muted
                            : AppColors.green,
                        fontWeight: FontWeight.w800,
                        fontSize: 10,
                      ),
                    ),
                  ],
                ),
              );
            }),
          const SizedBox(height: 6),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => setState(() => selectedIndex = 2),
              icon: const Icon(Icons.open_in_new_rounded, size: 16),
              label: const Text('Zobacz wszystkie rynki'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _openPositionsCard() {
    final positioned = assets.where((asset) {
      final position = '${asset['position'] ?? 'FLAT'}';
      return position != 'FLAT' && position.isNotEmpty;
    }).toList();

    final rows = positioned.isEmpty ? assets.take(5).toList() : positioned;

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const SectionTitle('Pozycje / stan instrumentów'),
              const SizedBox(width: 8),
              CountBadge('${positioned.length}'),
              const Spacer(),
              Text(
                'źródło: /api/assets',
                style: const TextStyle(color: AppColors.muted, fontSize: 10),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (rows.isEmpty)
            const Padding(
              padding: EdgeInsets.all(22),
              child: Center(
                child: Text(
                  'Brak instrumentów w API.',
                  style: TextStyle(color: AppColors.muted),
                ),
              ),
            )
          else
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: SizedBox(
                width: 980,
                child: Table(
                  columnWidths: const {
                    0: FlexColumnWidth(1.4),
                    1: FlexColumnWidth(1.3),
                    2: FlexColumnWidth(1.3),
                    3: FlexColumnWidth(1.3),
                    4: FlexColumnWidth(1.4),
                    5: FlexColumnWidth(1.3),
                  },
                  children: [
                    _headerRow([
                      'Instrument',
                      'Nazwa',
                      'Klasa',
                      'Provider',
                      'Cena stanu',
                      'Pozycja',
                    ]),
                    ...rows.map(
                      (asset) => TableRow(
                        children: [
                          _cell('${asset['symbol'] ?? '—'}', bold: true),
                          _cell('${asset['name'] ?? '—'}'),
                          _cell('${asset['asset_type'] ?? '—'}'),
                          _cell('${asset['provider'] ?? '—'}'),
                          _cell(_format(_num(asset['market_price']))),
                          _cell(
                            '${asset['position'] ?? 'FLAT'}',
                            color: '${asset['position'] ?? 'FLAT'}' == 'FLAT'
                                ? AppColors.muted
                                : AppColors.green,
                            bold: true,
                          ),
                        ],
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

  Widget _tradePerformanceMiniChart() {
    final profits = trades.map((trade) => _num(trade['profit'])).toList();

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Wynik strategii'),
          const SizedBox(height: 4),
          Text(
            '$selectedSymbol • ${trades.length} transakcji',
            style: const TextStyle(color: AppColors.muted, fontSize: 10),
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 185,
            child: profits.isEmpty
                ? const Center(
                    child: Text(
                      'Brak zamkniętych transakcji.',
                      style: TextStyle(color: AppColors.muted),
                    ),
                  )
                : LineChart(
                    LineChartData(
                      gridData: FlGridData(
                        show: true,
                        getDrawingHorizontalLine: (_) => FlLine(
                          color: AppColors.border.withOpacity(.55),
                          strokeWidth: 1,
                        ),
                      ),
                      titlesData: const FlTitlesData(
                        topTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        rightTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        bottomTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        leftTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 38,
                          ),
                        ),
                      ),
                      borderData: FlBorderData(show: false),
                      lineBarsData: [
                        LineChartBarData(
                          spots: _cumulativeSpots(profits),
                          isCurved: true,
                          color: AppColors.cyan,
                          barWidth: 2.2,
                          dotData: const FlDotData(show: false),
                        ),
                      ],
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _dailyPnlMiniChart() {
    final recent = daily.length > 18 ? daily.sublist(daily.length - 18) : daily;

    final values = recent.map((row) => _num(row['net_profit'])).toList();

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Rozkład wyników dziennych'),
          const SizedBox(height: 4),
          const Text(
            'net_profit z /api/daily',
            style: TextStyle(color: AppColors.muted, fontSize: 10),
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 185,
            child: values.isEmpty
                ? const Center(
                    child: Text(
                      'Brak raportów dziennych.',
                      style: TextStyle(color: AppColors.muted),
                    ),
                  )
                : BarChart(
                    BarChartData(
                      gridData: FlGridData(
                        show: true,
                        getDrawingHorizontalLine: (_) => FlLine(
                          color: AppColors.border.withOpacity(.55),
                          strokeWidth: 1,
                        ),
                      ),
                      borderData: FlBorderData(show: false),
                      titlesData: const FlTitlesData(
                        topTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        rightTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        bottomTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        leftTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 40,
                          ),
                        ),
                      ),
                      barGroups: [
                        for (int i = 0; i < values.length; i++)
                          BarChartGroupData(
                            x: i,
                            barRods: [
                              BarChartRodData(
                                toY: values[i],
                                width: 9,
                                color: values[i] >= 0
                                    ? AppColors.green
                                    : AppColors.red,
                                borderRadius: BorderRadius.circular(2),
                              ),
                            ],
                          ),
                      ],
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _systemHealthCard(
    Map<String, dynamic> account,
    Map<String, dynamic> performance,
    Map<String, dynamic> strategy,
    Map<String, dynamic> position,
  ) {
    final positionSide = '${position['side'] ?? ''}';

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Stan systemu'),
          const SizedBox(height: 12),
          InfoRow(
            label: 'FastAPI',
            value: connected ? 'ONLINE' : 'OFFLINE',
            color: connected ? AppColors.green : AppColors.red,
          ),
          InfoRow(
            label: 'Dane rynku',
            value: market['stale'] == true ? 'STALE' : 'OK',
            color: market['stale'] == true ? AppColors.orange : AppColors.green,
          ),
          InfoRow(
            label: 'AI',
            value: ai['available'] == true ? 'DOSTĘPNE' : 'NIEDOSTĘPNE',
            color: ai['available'] == true ? AppColors.green : AppColors.orange,
          ),
          InfoRow(
            label: 'Pozycja',
            value: positionSide.isEmpty ? 'FLAT' : positionSide,
            color: positionSide.isEmpty ? AppColors.muted : AppColors.green,
          ),
          InfoRow(
            label: 'Profit factor',
            value: _nullableNumber(performance['profit_factor']),
          ),
          InfoRow(
            label: 'Max DD',
            value: _format(_num(account['max_drawdown'])),
            color: AppColors.red,
          ),
          InfoRow(
            label: 'TIME',
            value: '${strategy['max_position_candles'] ?? '—'}',
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(11),
            decoration: BoxDecoration(
              color: const Color(0xFF0A1725),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              children: [
                Icon(
                  connected
                      ? Icons.verified_user_outlined
                      : Icons.warning_amber_rounded,
                  color: connected ? AppColors.green : AppColors.orange,
                ),
                const SizedBox(width: 9),
                Expanded(
                  child: Text(
                    connected
                        ? 'Dashboard czyta bieżący stan projektu.'
                        : 'Dashboard działa, ale API jest niedostępne.',
                    style: TextStyle(
                      color: connected ? AppColors.green : AppColors.orange,
                      fontWeight: FontWeight.w800,
                      fontSize: 11,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _portfolioPage() {
    final balance = _num(portfolio['balance']);
    final deposited = _num(portfolio['total_deposited']);
    final withdrawn = _num(portfolio['total_withdrawn']);
    final result = _num(portfolio['result']);

    return PageShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const PageHeading(
            'Portfel',
            'Wirtualny kapitał w PLN oraz stan finansowy zwracany przez FastAPI.',
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SizedBox(
                width: 245,
                child: MetricCard(
                  'Saldo',
                  '${_money(balance)} PLN',
                  'bieżący portfel użytkownika',
                  AppColors.green,
                ),
              ),
              SizedBox(
                width: 245,
                child: MetricCard(
                  'Wpłaty',
                  '${_money(deposited)} PLN',
                  'łącznie',
                  AppColors.cyan,
                ),
              ),
              SizedBox(
                width: 245,
                child: MetricCard(
                  'Wypłaty',
                  '${_money(withdrawn)} PLN',
                  'łącznie',
                  AppColors.orange,
                ),
              ),
              SizedBox(
                width: 245,
                child: MetricCard(
                  'Wynik portfela',
                  '${_money(result)} PLN',
                  'pole result z API',
                  result >= 0 ? AppColors.green : AppColors.red,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (context, constraints) {
              if (constraints.maxWidth >= 1000) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 6, child: _portfolioFlowCard()),
                    const SizedBox(width: 14),
                    Expanded(flex: 4, child: _assetClassDonut()),
                  ],
                );
              }

              return Column(
                children: [
                  _portfolioFlowCard(),
                  const SizedBox(height: 14),
                  _assetClassDonut(),
                ],
              );
            },
          ),
          const SizedBox(height: 14),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SectionTitle('Stan finansowy i ograniczenia'),
                const SizedBox(height: 12),
                InfoRow(
                  label: 'Waluta raportowa',
                  value: '${portfolio['currency'] ?? 'PLN'}',
                  color: AppColors.cyan,
                ),
                InfoRow(
                  label: 'Wersja stanu',
                  value: '${portfolio['version'] ?? '—'}',
                ),
                InfoRow(label: 'Źródło', value: '/api/user-portfolio'),
                const SizedBox(height: 14),
                const Text(
                  'FastAPI nie wystawia jeszcze pełnej alokacji portfela '
                  'multi-asset z historycznym FX. Dlatego dashboard nie '
                  'wymyśla wartości ekspozycji w PLN per klasa aktywów.',
                  style: TextStyle(color: AppColors.muted, height: 1.5),
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    FilledButton.icon(
                      onPressed: () => _showMessage(
                        'Raport korzysta z bieżących danych portfela z API.',
                      ),
                      icon: const Icon(Icons.description_outlined),
                      label: const Text('Podsumowanie portfela'),
                    ),
                    const SizedBox(width: 10),
                    OutlinedButton.icon(
                      onPressed: () => setState(() => selectedIndex = 5),
                      icon: const Icon(Icons.analytics_outlined),
                      label: const Text('Przejdź do analiz'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _portfolioFlowCard() {
    final deposited = _num(portfolio['total_deposited']);
    final withdrawn = _num(portfolio['total_withdrawn']);
    final balance = _num(portfolio['balance']);

    final maxValue = math.max(
      1.0,
      [deposited.abs(), withdrawn.abs(), balance.abs()].reduce(math.max),
    );

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Przepływy kapitału'),
          const SizedBox(height: 18),
          ExposureBar(
            'Wpłaty',
            (deposited.abs() / maxValue).clamp(0.0, 1.0),
            '${_money(deposited)} PLN',
            AppColors.cyan,
          ),
          ExposureBar(
            'Wypłaty',
            (withdrawn.abs() / maxValue).clamp(0.0, 1.0),
            '${_money(withdrawn)} PLN',
            AppColors.orange,
          ),
          ExposureBar(
            'Saldo',
            (balance.abs() / maxValue).clamp(0.0, 1.0),
            '${_money(balance)} PLN',
            AppColors.green,
          ),
          const SizedBox(height: 14),
          const Text(
            'Skala słupków jest względna do największej z trzech wartości.',
            style: TextStyle(color: AppColors.muted, fontSize: 10),
          ),
        ],
      ),
    );
  }

  Widget _marketsPage() {
    final selectedMarketPoints = _listOfMaps(market['points']);
    final selectedLast = selectedMarketPoints.isEmpty
        ? 0.0
        : _num(selectedMarketPoints.last['close']);

    return PageShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const PageHeading(
            'Rynki',
            'Obsługiwane instrumenty, providerzy i bieżący stan danych.',
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SizedBox(
                width: 245,
                child: MetricCard(
                  'Liczba instrumentów',
                  '${assets.length}',
                  'z /api/assets',
                  AppColors.cyan,
                ),
              ),
              SizedBox(
                width: 245,
                child: MetricCard(
                  'Wybrany rynek',
                  selectedSymbol,
                  'zmienisz go w górnym pasku',
                  AppColors.green,
                ),
              ),
              SizedBox(
                width: 245,
                child: MetricCard(
                  'Ostatnia cena',
                  _format(selectedLast),
                  'z /api/market',
                  AppColors.cyan,
                ),
              ),
              SizedBox(
                width: 245,
                child: MetricCard(
                  'Stan danych',
                  market['stale'] == true ? 'STALE' : 'AKTUALNE',
                  market['cached'] == true ? 'cache API' : 'provider API',
                  market['stale'] == true ? AppColors.orange : AppColors.green,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SectionTitle('Lista rynków'),
                const SizedBox(height: 10),
                if (assets.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(
                      child: Text(
                        'Brak instrumentów w /api/assets.',
                        style: TextStyle(color: AppColors.muted),
                      ),
                    ),
                  )
                else
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: SizedBox(
                      width: 1120,
                      child: Table(
                        columnWidths: const {
                          0: FlexColumnWidth(1.5),
                          1: FlexColumnWidth(1.8),
                          2: FlexColumnWidth(1.4),
                          3: FlexColumnWidth(1.5),
                          4: FlexColumnWidth(1.3),
                          5: FlexColumnWidth(1.2),
                        },
                        children: [
                          _headerRow([
                            'Instrument',
                            'Nazwa',
                            'Klasa',
                            'Provider',
                            'Cena stanu',
                            'Pozycja',
                          ]),
                          ...assets.map((asset) {
                            final symbol = '${asset['symbol'] ?? '—'}';
                            final position = '${asset['position'] ?? 'FLAT'}';

                            return TableRow(
                              children: [
                                _cell(
                                  symbol,
                                  bold: true,
                                  color: symbol == selectedSymbol
                                      ? AppColors.cyan
                                      : AppColors.text,
                                ),
                                _cell('${asset['name'] ?? '—'}'),
                                _cell('${asset['asset_type'] ?? '—'}'),
                                _cell('${asset['provider'] ?? '—'}'),
                                _cell(_format(_num(asset['market_price']))),
                                _cell(
                                  position,
                                  color: position == 'FLAT'
                                      ? AppColors.muted
                                      : AppColors.green,
                                  bold: true,
                                ),
                              ],
                            );
                          }),
                        ],
                      ),
                    ),
                  ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    OutlinedButton.icon(
                      onPressed: () => _refreshAll(),
                      icon: const Icon(Icons.refresh_rounded),
                      label: const Text('Odśwież notowania'),
                    ),
                    const SizedBox(width: 10),
                    FilledButton.icon(
                      onPressed: () => _showMessage(
                        'Instrument wybierasz z listy w górnym pasku.',
                      ),
                      icon: const Icon(Icons.info_outline_rounded),
                      label: const Text('Jak wybrać instrument'),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          _marketDetailsPanel(),
        ],
      ),
    );
  }

  Widget _marketDetailsPanel() {
    final points = _listOfMaps(market['points']);
    final last = points.isNotEmpty ? points.last : <String, dynamic>{};

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionTitle('Szczegóły $selectedSymbol'),
          const SizedBox(height: 12),
          Wrap(
            spacing: 24,
            runSpacing: 12,
            children: [
              _tinyMetric('Open', _format(_num(last['open']))),
              _tinyMetric('High', _format(_num(last['high']))),
              _tinyMetric('Low', _format(_num(last['low']))),
              _tinyMetric('Close', _format(_num(last['close']))),
              _tinyMetric('Volume', _format(_num(last['volume']))),
              _tinyMetric('Punkty', '${points.length}'),
            ],
          ),
          const SizedBox(height: 14),
          const Text(
            'Obecne API /api/market zwraca świece. Bid/ask, spread i '
            'pełna jakość REALTIME_BOOK będą widoczne tutaj po udostępnieniu '
            'ich przez backend.',
            style: TextStyle(color: AppColors.muted, height: 1.45),
          ),
        ],
      ),
    );
  }

  Widget _strategiesPage() {
    final strategy = _map(status['strategy']);
    final performance = _map(status['performance']);
    final account = _map(status['account']);

    return PageShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PageHeading(
            'Strategie — $selectedSymbol',
            'Konfiguracja, status i wynik bieżącego silnika paper.',
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SizedBox(
                width: 230,
                child: MetricCard(
                  'BUY RSI',
                  _format(_num(strategy['buy_rsi'])),
                  'próg BUY',
                  AppColors.cyan,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'SELL RSI',
                  _format(_num(strategy['sell_rsi'])),
                  'próg SELL',
                  AppColors.cyan,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Profit Factor',
                  _nullableNumber(performance['profit_factor']),
                  '${performance['trades'] ?? 0} transakcji',
                  AppColors.green,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Max Drawdown',
                  _format(_num(account['max_drawdown'])),
                  'wartość silnika',
                  AppColors.red,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Expectancy',
                  _format(_num(performance['expectancy'])),
                  'na transakcję',
                  AppColors.purple,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (context, constraints) {
              if (constraints.maxWidth >= 1000) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: _strategyConfigCard(strategy)),
                    const SizedBox(width: 14),
                    Expanded(child: _strategyResultCard(performance, account)),
                  ],
                );
              }

              return Column(
                children: [
                  _strategyConfigCard(strategy),
                  const SizedBox(height: 14),
                  _strategyResultCard(performance, account),
                ],
              );
            },
          ),
          const SizedBox(height: 14),
          _tradePerformanceMiniChart(),
        ],
      ),
    );
  }

  Widget _strategyConfigCard(Map<String, dynamic> strategy) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Konfiguracja strategii'),
          const SizedBox(height: 12),
          InfoRow(
            label: 'Instrument',
            value: '${strategy['symbol'] ?? selectedSymbol}',
          ),
          InfoRow(label: 'Provider', value: '${strategy['provider'] ?? '—'}'),
          InfoRow(label: 'Interwał', value: '${strategy['interval'] ?? '—'}'),
          InfoRow(
            label: 'Metoda RSI',
            value: '${strategy['rsi_method'] ?? '—'}',
          ),
          InfoRow(
            label: 'Min. difference',
            value: _format(_num(strategy['min_difference'])),
          ),
          InfoRow(
            label: 'Fee',
            value: _format(_num(strategy['trading_fee']), decimals: 6),
          ),
          InfoRow(
            label: 'TIME',
            value: '${strategy['max_position_candles'] ?? '—'}',
          ),
        ],
      ),
    );
  }

  Widget _strategyResultCard(
    Map<String, dynamic> performance,
    Map<String, dynamic> account,
  ) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Wynik bieżącego silnika'),
          const SizedBox(height: 12),
          InfoRow(label: 'Saldo', value: _format(_num(account['balance']))),
          InfoRow(
            label: 'Net profit',
            value: _signed(_num(account['net_profit'])),
            color: _num(account['net_profit']) >= 0
                ? AppColors.green
                : AppColors.red,
          ),
          InfoRow(label: 'Wygrane', value: '${performance['wins'] ?? 0}'),
          InfoRow(label: 'Przegrane', value: '${performance['losses'] ?? 0}'),
          InfoRow(
            label: 'Win rate',
            value: '${_format(_num(performance['win_rate']))}%',
          ),
          InfoRow(
            label: 'Profit factor',
            value: _nullableNumber(performance['profit_factor']),
          ),
        ],
      ),
    );
  }

  Widget _transactionsPage() {
    return PageShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PageHeading(
            'Transakcje — $selectedSymbol',
            'Pełna historia zwracana przez /api/trades.',
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Transakcje',
                  '${trades.length}',
                  'zamknięte',
                  AppColors.cyan,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Łączny wynik',
                  _signed(
                    trades.fold<double>(
                      0,
                      (sum, trade) => sum + _num(trade['profit']),
                    ),
                  ),
                  'wartość natywna API',
                  trades.fold<double>(
                            0,
                            (sum, trade) => sum + _num(trade['profit']),
                          ) >=
                          0
                      ? AppColors.green
                      : AppColors.red,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Najlepsza',
                  _signed(_bestTrade()),
                  'profit',
                  AppColors.green,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Najgorsza',
                  _signed(_worstTrade()),
                  'profit',
                  AppColors.red,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const SectionTitle('Historia transakcji'),
                    const Spacer(),
                    Text(
                      '${trades.length} rekordów',
                      style: const TextStyle(
                        color: AppColors.muted,
                        fontSize: 10,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                if (trades.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(
                      child: Text(
                        'Brak zamkniętych transakcji dla tego instrumentu.',
                        style: TextStyle(color: AppColors.muted),
                      ),
                    ),
                  )
                else
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: SizedBox(
                      width: 1160,
                      child: Table(
                        defaultVerticalAlignment:
                            TableCellVerticalAlignment.middle,
                        columnWidths: const {
                          0: FlexColumnWidth(.7),
                          1: FlexColumnWidth(1),
                          2: FlexColumnWidth(1.4),
                          3: FlexColumnWidth(1.4),
                          4: FlexColumnWidth(1.1),
                          5: FlexColumnWidth(1.3),
                          6: FlexColumnWidth(1.3),
                          7: FlexColumnWidth(1.3),
                        },
                        children: [
                          _headerRow([
                            '#',
                            'Strona',
                            'Wejście',
                            'Wyjście',
                            'Ilość',
                            'Wynik',
                            'Powód',
                            'Czas',
                          ]),
                          ...trades.map((trade) {
                            final profit = _num(trade['profit']);

                            return TableRow(
                              children: [
                                _cell(
                                  '${trade['trade_number'] ?? '—'}',
                                  dense: compactTables,
                                ),
                                _cell(
                                  '${trade['side'] ?? '—'}',
                                  bold: true,
                                  dense: compactTables,
                                ),
                                _cell(
                                  _format(_num(trade['entry_price'])),
                                  dense: compactTables,
                                ),
                                _cell(
                                  _format(_num(trade['exit_price'])),
                                  dense: compactTables,
                                ),
                                _cell(
                                  _format(_num(trade['quantity'])),
                                  dense: compactTables,
                                ),
                                _cell(
                                  _signed(profit),
                                  color: profit >= 0
                                      ? AppColors.green
                                      : AppColors.red,
                                  bold: true,
                                  dense: compactTables,
                                ),
                                _cell(
                                  '${trade['exit_reason'] ?? '—'}',
                                  dense: compactTables,
                                ),
                                _cell(
                                  '${trade['exit_timestamp'] ?? trade['timestamp'] ?? '—'}',
                                  dense: compactTables,
                                ),
                              ],
                            );
                          }),
                        ],
                      ),
                    ),
                  ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    OutlinedButton.icon(
                      onPressed: () => _showMessage(
                        'Filtrowanie po symbolu działa przez wybór instrumentu w górnym pasku.',
                      ),
                      icon: const Icon(Icons.filter_alt_outlined),
                      label: const Text('Filtr symbolu'),
                    ),
                    const SizedBox(width: 10),
                    FilledButton.icon(
                      onPressed: () => _showMessage(
                        'Eksport CSV nie ma jeszcze endpointu w FastAPI.',
                      ),
                      icon: const Icon(Icons.download_rounded),
                      label: const Text('Eksport CSV'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _analyticsPage() {
    final performance = _map(status['performance']);
    final account = _map(status['account']);
    final equityPoints = _listOfMaps(equity['points']);
    final equitySpots = <FlSpot>[];

    for (final point in equityPoints) {
      equitySpots.add(FlSpot(_num(point['index']), _num(point['balance'])));
    }

    final profits = trades.map((trade) => _num(trade['profit'])).toList();

    return PageShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PageHeading(
            'Analizy — $selectedSymbol',
            'Equity, rozkład transakcji, wyniki dzienne i kluczowe metryki.',
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Profit Factor',
                  _nullableNumber(performance['profit_factor']),
                  'bieżący stan',
                  AppColors.green,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Win rate',
                  '${_format(_num(performance['win_rate']))}%',
                  '${performance['wins'] ?? 0} / ${performance['trades'] ?? 0}',
                  AppColors.cyan,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Maks. DD',
                  _format(_num(account['max_drawdown'])),
                  'wartość silnika',
                  AppColors.red,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Expectancy',
                  _format(_num(performance['expectancy'])),
                  'na transakcję',
                  AppColors.purple,
                ),
              ),
              SizedBox(
                width: 230,
                child: MetricCard(
                  'Daily loss',
                  _format(_num(account['daily_loss'])),
                  'RiskGuard',
                  AppColors.orange,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (context, constraints) {
              if (constraints.maxWidth >= 1100) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: _equityAnalyticsCard(equitySpots)),
                    const SizedBox(width: 14),
                    Expanded(child: _profitDistributionCard(profits)),
                  ],
                );
              }

              return Column(
                children: [
                  _equityAnalyticsCard(equitySpots),
                  const SizedBox(height: 14),
                  _profitDistributionCard(profits),
                ],
              );
            },
          ),
          const SizedBox(height: 14),
          _dailyReportTable(),
        ],
      ),
    );
  }

  Widget _equityAnalyticsCard(List<FlSpot> spots) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Krzywa equity'),
          const SizedBox(height: 14),
          SizedBox(
            height: 270,
            child: spots.length < 2
                ? const Center(
                    child: Text(
                      'Brak wystarczających punktów equity.',
                      style: TextStyle(color: AppColors.muted),
                    ),
                  )
                : LineChart(
                    LineChartData(
                      gridData: FlGridData(
                        show: true,
                        getDrawingHorizontalLine: (_) => FlLine(
                          color: AppColors.border.withOpacity(.55),
                          strokeWidth: 1,
                        ),
                      ),
                      titlesData: const FlTitlesData(
                        topTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        rightTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        bottomTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        leftTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 56,
                          ),
                        ),
                      ),
                      borderData: FlBorderData(show: false),
                      lineBarsData: [
                        LineChartBarData(
                          spots: spots,
                          isCurved: true,
                          color: AppColors.green,
                          barWidth: 2.3,
                          dotData: const FlDotData(show: false),
                          belowBarData: BarAreaData(
                            show: true,
                            color: AppColors.green.withOpacity(.08),
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

  Widget _profitDistributionCard(List<double> profits) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Zyski i straty transakcji'),
          const SizedBox(height: 14),
          SizedBox(
            height: 270,
            child: profits.isEmpty
                ? const Center(
                    child: Text(
                      'Brak transakcji.',
                      style: TextStyle(color: AppColors.muted),
                    ),
                  )
                : BarChart(
                    BarChartData(
                      gridData: FlGridData(
                        show: true,
                        getDrawingHorizontalLine: (_) => FlLine(
                          color: AppColors.border.withOpacity(.55),
                          strokeWidth: 1,
                        ),
                      ),
                      borderData: FlBorderData(show: false),
                      titlesData: const FlTitlesData(
                        topTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        rightTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        bottomTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        leftTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 42,
                          ),
                        ),
                      ),
                      barGroups: [
                        for (int i = 0; i < profits.length; i++)
                          BarChartGroupData(
                            x: i,
                            barRods: [
                              BarChartRodData(
                                toY: profits[i],
                                width: 10,
                                color: profits[i] >= 0
                                    ? AppColors.green
                                    : AppColors.red,
                                borderRadius: BorderRadius.circular(2),
                              ),
                            ],
                          ),
                      ],
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _dailyReportTable() {
    final recent = daily.length > 12 ? daily.sublist(daily.length - 12) : daily;

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Raport dzienny'),
          const SizedBox(height: 10),
          if (recent.isEmpty)
            const Padding(
              padding: EdgeInsets.all(22),
              child: Center(
                child: Text(
                  'Brak danych w /api/daily.',
                  style: TextStyle(color: AppColors.muted),
                ),
              ),
            )
          else
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: SizedBox(
                width: 900,
                child: Table(
                  children: [
                    _headerRow([
                      'Data',
                      'Balance',
                      'Net profit',
                      'Trades',
                      'Win rate',
                    ]),
                    ...recent.map(
                      (row) => TableRow(
                        children: [
                          _cell('${row['date'] ?? '—'}'),
                          _cell(_format(_num(row['balance']))),
                          _cell(
                            _signed(_num(row['net_profit'])),
                            color: _num(row['net_profit']) >= 0
                                ? AppColors.green
                                : AppColors.red,
                            bold: true,
                          ),
                          _cell('${row['trades'] ?? 0}'),
                          _cell('${_format(_num(row['win_rate']))}%'),
                        ],
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

  Widget _calendarPage() {
    return PageShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const PageHeading(
            'Kalendarz',
            'Pełny ekran kalendarza zachowany — backend nie ma jeszcze endpointu makro.',
          ),
          const SizedBox(height: 14),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const ApiPendingBanner(
                  text:
                      'FastAPI nie wystawia obecnie /api/calendar. '
                      'Nie wstawiam fałszywych wydarzeń makro.',
                ),
                const SizedBox(height: 14),
                const SectionTitle('Najbliższe wydarzenia'),
                const SizedBox(height: 10),
                Table(
                  children: [
                    _headerRow(['Termin', 'Waluta', 'Wydarzenie', 'Znaczenie']),
                    TableRow(
                      children: [
                        _cell('—'),
                        _cell('—'),
                        _cell('Oczekuje na endpoint FastAPI'),
                        _cell('—', color: AppColors.muted),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                OutlinedButton.icon(
                  onPressed: () => _showMessage(
                    'Po dodaniu endpointu /api/calendar ten ekran może zostać wypełniony realnymi danymi.',
                  ),
                  icon: const Icon(Icons.refresh_rounded),
                  label: const Text('Odśwież kalendarz'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SectionTitle('Rynki objęte kalendarzem'),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: assets
                      .map(
                        (asset) => Chip(
                          avatar: const Icon(Icons.public_rounded, size: 16),
                          label: Text('${asset['symbol'] ?? '—'}'),
                        ),
                      )
                      .toList(),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _alertsPage() {
    final alerts = _derivedAlerts();

    return PageShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const PageHeading(
            'Alerty',
            'Alerty systemowe wyliczane z realnego stanu API; reguły użytkownika oczekują na endpoint.',
          ),
          const SizedBox(height: 14),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text(
                    'Powiadomienia interfejsu aktywne',
                    style: TextStyle(
                      color: AppColors.text,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  subtitle: const Text(
                    'Ustawienie lokalne dashboardu. Nie zmienia backendu.',
                    style: TextStyle(color: AppColors.muted),
                  ),
                  value: alertsEnabled,
                  onChanged: (value) {
                    setState(() => alertsEnabled = value);
                  },
                ),
                const Divider(),
                const SectionTitle('Alerty systemowe'),
                const SizedBox(height: 10),
                if (alerts.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(18),
                    child: Row(
                      children: [
                        Icon(
                          Icons.check_circle_outline_rounded,
                          color: AppColors.green,
                        ),
                        SizedBox(width: 10),
                        Text(
                          'Brak aktywnych alertów systemowych.',
                          style: TextStyle(color: AppColors.green),
                        ),
                      ],
                    ),
                  )
                else
                  Table(
                    children: [
                      _headerRow(['Obszar', 'Warunek', 'Status', 'Priorytet']),
                      ...alerts.map(
                        (alert) => TableRow(
                          children: [
                            _cell(alert.$1, bold: true),
                            _cell(alert.$2),
                            _cell(
                              alertsEnabled ? 'Aktywny' : 'Wstrzymany',
                              color: alertsEnabled
                                  ? AppColors.red
                                  : AppColors.orange,
                              bold: true,
                            ),
                            _cell(
                              alert.$3,
                              color: alert.$3 == 'Wysoki'
                                  ? AppColors.red
                                  : AppColors.orange,
                              bold: true,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                const SizedBox(height: 14),
                const ApiPendingBanner(
                  text:
                      'Reguły alertów użytkownika nie mają jeszcze własnego endpointu FastAPI. '
                      'Ten ekran zachowuje pełny moduł UI bez wymyślania danych.',
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _settingsPage() {
    return PageShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const PageHeading(
            'Ustawienia',
            'Ustawienia dashboardu oraz informacje o połączeniu z FastAPI.',
          ),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (context, constraints) {
              if (constraints.maxWidth >= 1000) {
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: _uiSettingsCard()),
                    const SizedBox(width: 14),
                    Expanded(child: _apiSettingsCard()),
                  ],
                );
              }

              return Column(
                children: [
                  _uiSettingsCard(),
                  const SizedBox(height: 14),
                  _apiSettingsCard(),
                ],
              );
            },
          ),
          const SizedBox(height: 14),
          _aiSettingsCard(),
        ],
      ),
    );
  }

  Widget _uiSettingsCard() {
    return AppCard(
      child: Column(
        children: [
          const Align(
            alignment: Alignment.centerLeft,
            child: SectionTitle('Interfejs'),
          ),
          const SizedBox(height: 8),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Paper LIVE w interfejsie'),
            subtitle: const Text(
              'To przełącznik wizualny. Nie wysyła komendy do silnika.',
              style: TextStyle(color: AppColors.muted),
            ),
            value: paperUiEnabled,
            onChanged: (value) {
              setState(() => paperUiEnabled = value);
            },
          ),
          const Divider(),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Kompaktowe tabele'),
            subtitle: const Text(
              'Zmniejsza wysokość wierszy historii transakcji.',
              style: TextStyle(color: AppColors.muted),
            ),
            value: compactTables,
            onChanged: (value) {
              setState(() => compactTables = value);
            },
          ),
          const Divider(),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(
              Icons.currency_exchange_rounded,
              color: AppColors.cyan,
            ),
            title: const Text('Waluta raportowa portfela'),
            subtitle: Text('${portfolio['currency'] ?? 'PLN'}'),
            trailing: const Icon(
              Icons.lock_outline_rounded,
              color: AppColors.muted,
            ),
          ),
        ],
      ),
    );
  }

  Widget _apiSettingsCard() {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Połączenie FastAPI'),
          const SizedBox(height: 12),
          InfoRow(label: 'Adres API', value: api.baseUrl),
          InfoRow(
            label: 'Status',
            value: connected ? 'ONLINE' : 'OFFLINE',
            color: connected ? AppColors.green : AppColors.red,
          ),
          InfoRow(
            label: 'Instrument',
            value: selectedSymbol,
            color: AppColors.cyan,
          ),
          const InfoRow(label: 'Auto refresh', value: '10 sekund'),
          InfoRow(
            label: 'Dane rynku',
            value: market['stale'] == true ? 'STALE' : 'OK',
            color: market['stale'] == true ? AppColors.orange : AppColors.green,
          ),
          const SizedBox(height: 14),
          const Text(
            'Obsługiwane zmienne startowe:\n'
            'API_BASE_URL lub AL_TRADING_API_BASE_URL',
            style: TextStyle(color: AppColors.muted, height: 1.5, fontSize: 11),
          ),
        ],
      ),
    );
  }

  Widget _aiSettingsCard() {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('AI Paper'),
          const SizedBox(height: 12),
          InfoRow(
            label: 'Dostępność',
            value: ai['available'] == true ? 'TAK' : 'NIE',
            color: ai['available'] == true ? AppColors.green : AppColors.orange,
          ),
          InfoRow(label: 'Tryb', value: '${ai['mode'] ?? '—'}'),
          InfoRow(
            label: 'Stare dane',
            value: ai['stale'] == true ? 'TAK' : 'NIE',
            color: ai['stale'] == true ? AppColors.orange : AppColors.green,
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              FilledButton.icon(
                onPressed: () => _refreshAll(),
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Odśwież cały dashboard'),
              ),
              const SizedBox(width: 10),
              OutlinedButton.icon(
                onPressed: () => _showSystemDialog(),
                icon: const Icon(Icons.info_outline_rounded),
                label: const Text('Szczegóły systemu'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _tinyMetric(String label, String value) {
    return Container(
      width: 145,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0A1725),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(color: AppColors.muted, fontSize: 10),
          ),
          const SizedBox(height: 5),
          Text(
            value,
            style: const TextStyle(
              color: AppColors.text,
              fontWeight: FontWeight.w900,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }

  double _bestTrade() {
    if (trades.isEmpty) return 0.0;
    return trades.map((trade) => _num(trade['profit'])).reduce(math.max);
  }

  double _worstTrade() {
    if (trades.isEmpty) return 0.0;
    return trades.map((trade) => _num(trade['profit'])).reduce(math.min);
  }

  List<FlSpot> _cumulativeSpots(List<double> values) {
    final spots = <FlSpot>[];
    var cumulative = 0.0;

    for (int i = 0; i < values.length; i++) {
      cumulative += values[i];
      spots.add(FlSpot(i.toDouble(), cumulative));
    }

    return spots;
  }

  List<(String, String, String)> _derivedAlerts() {
    final result = <(String, String, String)>[];

    if (!connected) {
      result.add(('FastAPI', 'Brak połączenia z backendem', 'Wysoki'));
    }

    if (market['stale'] == true) {
      result.add((selectedSymbol, 'Dane rynku oznaczone jako stare', 'Wysoki'));
    }

    if (ai['stale'] == true) {
      result.add(('AI', 'Dane AI są oznaczone jako stare', 'Średni'));
    }

    if (ai.isNotEmpty && ai['available'] == false) {
      result.add(('AI', 'Moduł AI niedostępny', 'Średni'));
    }

    return result;
  }

  void _showMessage(String text) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(text),
        backgroundColor: AppColors.panel2,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  void _showSystemDialog() {
    if (!mounted) return;

    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.panel,
        title: const Text('Stan systemu'),
        content: SizedBox(
          width: 440,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              InfoRow(
                label: 'FastAPI',
                value: connected ? 'ONLINE' : 'OFFLINE',
                color: connected ? AppColors.green : AppColors.red,
              ),
              InfoRow(label: 'API URL', value: api.baseUrl),
              InfoRow(label: 'Instrument', value: selectedSymbol),
              InfoRow(
                label: 'Market stale',
                value: market['stale'] == true ? 'TAK' : 'NIE',
                color: market['stale'] == true
                    ? AppColors.orange
                    : AppColors.green,
              ),
              InfoRow(
                label: 'AI available',
                value: ai['available'] == true ? 'TAK' : 'NIE',
              ),
              if (lastRefresh != null)
                InfoRow(label: 'Odświeżono', value: _time(lastRefresh!)),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Zamknij'),
          ),
        ],
      ),
    );
  }

  Widget _statusPill(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(.12),
        border: Border.all(color: color.withOpacity(.55)),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w900,
          letterSpacing: .35,
        ),
      ),
    );
  }
}

class PageShell extends StatelessWidget {
  final Widget child;

  const PageShell({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      key: ValueKey(child.runtimeType),
      padding: const EdgeInsets.all(18),
      child: child,
    );
  }
}

class AppCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;

  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(15),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: padding,
      decoration: BoxDecoration(
        color: AppColors.panel,
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: AppColors.border),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(.17),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: child,
    );
  }
}

class MetricCard extends StatelessWidget {
  final String title;
  final String value;
  final String subtitle;
  final Color color;

  const MetricCard(
    this.title,
    this.value,
    this.subtitle,
    this.color, {
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(color: AppColors.muted, fontSize: 12),
          ),
          const SizedBox(height: 7),
          Text(
            value,
            style: const TextStyle(
              color: AppColors.text,
              fontSize: 19,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            subtitle,
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class PageHeading extends StatelessWidget {
  final String title;
  final String subtitle;

  const PageHeading(this.title, this.subtitle, {super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            color: AppColors.text,
            fontSize: 26,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 4),
        Text(subtitle, style: const TextStyle(color: AppColors.muted)),
      ],
    );
  }
}

class SectionTitle extends StatelessWidget {
  final String text;

  const SectionTitle(this.text, {super.key});

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: AppColors.text,
        fontSize: 15,
        fontWeight: FontWeight.w900,
      ),
    );
  }
}

class InfoRow extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const InfoRow({
    super.key,
    required this.label,
    required this.value,
    this.color = AppColors.text,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: AppColors.muted, fontSize: 12),
            ),
          ),
          const SizedBox(width: 10),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: TextStyle(
                color: color,
                fontSize: 12,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class LegendRow extends StatelessWidget {
  final Color color;
  final String label;
  final String value;

  const LegendRow(this.color, this.label, this.value, {super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Container(
            width: 9,
            height: 9,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: AppColors.muted, fontSize: 12),
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              color: AppColors.text,
              fontWeight: FontWeight.w800,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}

class ExposureBar extends StatelessWidget {
  final String label;
  final double value;
  final String amount;
  final Color color;

  const ExposureBar(
    this.label,
    this.value,
    this.amount,
    this.color, {
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        children: [
          SizedBox(
            width: 90,
            child: Text(label, style: const TextStyle(color: AppColors.text)),
          ),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: LinearProgressIndicator(
                value: value,
                minHeight: 11,
                backgroundColor: const Color(0xFF11283A),
                valueColor: AlwaysStoppedAnimation<Color>(color),
              ),
            ),
          ),
          const SizedBox(width: 12),
          SizedBox(
            width: 130,
            child: Text(
              amount,
              textAlign: TextAlign.right,
              style: const TextStyle(color: AppColors.muted, fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }
}

class CountBadge extends StatelessWidget {
  final String value;

  const CountBadge(this.value, {super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: AppColors.red,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        value,
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w900,
          fontSize: 10,
        ),
      ),
    );
  }
}

class ApiPendingBanner extends StatelessWidget {
  final String text;

  const ApiPendingBanner({super.key, required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.orange.withOpacity(.10),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.orange.withOpacity(.45)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.info_outline_rounded,
            color: AppColors.orange,
            size: 20,
          ),
          const SizedBox(width: 9),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(
                color: AppColors.orange,
                height: 1.4,
                fontSize: 11,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Logo extends StatelessWidget {
  const _Logo();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 42,
      height: 42,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.cyan, Color(0xFF3C66FF)],
        ),
        boxShadow: [
          BoxShadow(color: AppColors.cyan.withOpacity(.25), blurRadius: 14),
        ],
      ),
      child: const Icon(
        Icons.show_chart_rounded,
        color: Colors.white,
        size: 25,
      ),
    );
  }
}

TableRow _headerRow(List<String> values) {
  return TableRow(
    decoration: const BoxDecoration(color: Color(0xFF0F2436)),
    children: values
        .map(
          (value) => Padding(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 10),
            child: Text(
              value,
              style: const TextStyle(
                color: AppColors.muted,
                fontSize: 11,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        )
        .toList(),
  );
}

Widget _cell(
  String value, {
  Color color = AppColors.text,
  bool bold = false,
  bool dense = false,
}) {
  return Padding(
    padding: EdgeInsets.symmetric(horizontal: 9, vertical: dense ? 7 : 10),
    child: Text(
      value,
      style: TextStyle(
        color: color,
        fontSize: 12,
        fontWeight: bold ? FontWeight.w800 : FontWeight.w500,
      ),
    ),
  );
}

Map<String, dynamic> _map(dynamic value) {
  if (value is Map) {
    return Map<String, dynamic>.from(value);
  }
  return <String, dynamic>{};
}

List<Map<String, dynamic>> _listOfMaps(dynamic value) {
  if (value is! List) {
    return <Map<String, dynamic>>[];
  }

  return value
      .whereType<Map>()
      .map((item) => Map<String, dynamic>.from(item))
      .toList();
}

double _num(dynamic value) {
  if (value is num) {
    return value.toDouble();
  }

  return double.tryParse('$value') ?? 0.0;
}

String _format(double value, {int decimals = 2}) {
  if (!value.isFinite) return '—';
  return value.toStringAsFixed(decimals);
}

String _signed(double value) {
  final prefix = value > 0 ? '+' : '';
  return '$prefix${_format(value)}';
}

String _money(double value) {
  final negative = value < 0;
  final abs = value.abs();
  final fixed = abs.toStringAsFixed(2);
  final parts = fixed.split('.');
  final chars = parts[0].split('').reversed.toList();
  final grouped = <String>[];

  for (int i = 0; i < chars.length; i++) {
    if (i > 0 && i % 3 == 0) {
      grouped.add(' ');
    }
    grouped.add(chars[i]);
  }

  final integer = grouped.reversed.join();
  return '${negative ? '-' : ''}$integer,${parts[1]}';
}

String _nullableNumber(dynamic value) {
  if (value == null) return '—';
  return _format(_num(value));
}

String _time(DateTime value) {
  String two(int number) => number.toString().padLeft(2, '0');
  return '${two(value.hour)}:${two(value.minute)}:${two(value.second)}';
}
