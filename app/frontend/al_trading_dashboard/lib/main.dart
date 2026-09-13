import 'dart:async';
import 'dart:convert';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

const List<Map<String, String>> fallbackAssets = [
  {'symbol': 'BTCUSDT', 'name': 'Bitcoin', 'asset_type': 'crypto'},
  {'symbol': 'ETHUSDT', 'name': 'Ethereum', 'asset_type': 'crypto'},
  {'symbol': 'SOLUSDT', 'name': 'Solana', 'asset_type': 'crypto'},
  {'symbol': 'BNBUSDT', 'name': 'BNB', 'asset_type': 'crypto'},
  {'symbol': 'XRPUSDT', 'name': 'XRP', 'asset_type': 'crypto'},
  {'symbol': 'XAUUSD', 'name': 'Złoto', 'asset_type': 'gold'},
  {'symbol': 'WTIUSD', 'name': 'Ropa WTI', 'asset_type': 'oil'},
  {'symbol': 'EURUSD', 'name': 'Euro / dolar', 'asset_type': 'forex'},
  {'symbol': 'AAPL', 'name': 'Apple', 'asset_type': 'stock'},
];

const String apiBaseUrl = String.fromEnvironment(
  'AL_TRADING_API_BASE_URL',
  defaultValue: 'http://100.77.193.89:8000',
);

void main() {
  runApp(const AlTradingApp());
}

class AlTradingApp extends StatelessWidget {
  const AlTradingApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AL Trading Agent',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0B1020),
        cardColor: const Color(0xFF151C2E),
        useMaterial3: true,
      ),
      home: const DashboardPage(),
    );
  }
}

class DashboardPage extends StatefulWidget {
  final bool liveMode;

  const DashboardPage({super.key, this.liveMode = true});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  Map<String, dynamic>? status;
  List<dynamic> trades = [];
  List<dynamic> equity = [];
  List<dynamic> marketCandles = [];
  List<Map<String, dynamic>> assets = fallbackAssets
      .map((asset) => Map<String, dynamic>.from(asset))
      .toList();
  String selectedSymbol = 'BTCUSDT';
  int requestGeneration = 0;

  String? error;
  bool loading = true;
  DateTime? lastUpdate;

  Timer? timer;

  @override
  void initState() {
    super.initState();

    if (widget.liveMode) {
      loadAssets();
      loadData();

      timer = Timer.periodic(const Duration(seconds: 5), (_) => loadData());
    } else {
      _loadTestData();
    }
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  void _loadTestData() {
    assets = fallbackAssets
        .map((asset) => Map<String, dynamic>.from(asset))
        .toList();

    status = {
      'available': true,
      'strategy': {
        'symbol': 'BTCUSDT',
        'interval': '1m',
        'buy_rsi': 33.8,
        'sell_rsi': 68.5,
        'max_position_candles': 241,
        'min_difference': 1.0,
        'rsi_method': 'classic',
        'trading_fee': 0.0004,
      },
      'system': {'state_version': 3, 'last_processed_timestamp': 0},
      'position': {
        'side': null,
        'entry_price': null,
        'quantity': 0.0,
        'stop_loss': null,
        'take_profit': null,
        'entry_timestamp': null,
      },
      'account': {
        'position': 'FLAT',
        'position_candles': 0,
        'balance': 1000.0,
        'initial_balance': 1000.0,
        'net_profit': 0.0,
        'peak_balance': 1000.0,
        'max_drawdown': 0.0,
        'market_price': 0.0,
        'daily_loss': 0.0,
      },
      'performance': {
        'trades': 0,
        'wins': 0,
        'losses': 0,
        'win_rate': 0.0,
        'profit_factor': null,
        'gross_profit': 0.0,
        'gross_loss': 0.0,
        'avg_win': 0.0,
        'avg_loss': 0.0,
        'expectancy': 0.0,
      },
    };

    trades = [];
    equity = [
      {'index': 0, 'balance': 1000.0},
    ];

    marketCandles = [];

    loading = false;
    lastUpdate = DateTime.now();
  }

  Future<dynamic> getJson(String endpoint) async {
    final response = await http
        .get(Uri.parse('$apiBaseUrl$endpoint'))
        .timeout(const Duration(seconds: 5));

    if (response.statusCode != 200) {
      throw Exception('HTTP ${response.statusCode}: ${response.body}');
    }

    return jsonDecode(response.body);
  }

  Future<void> loadAssets() async {
    try {
      final response = await getJson('/api/assets');

      if (!mounted) {
        return;
      }

      setState(() {
        assets = (response as List)
            .map((asset) => Map<String, dynamic>.from(asset as Map))
            .toList();
      });
    } catch (_) {
      // The legacy BTC-only API can still drive the dashboard.
    }
  }

  Future<void> loadData({String? symbol}) async {
    final requestSymbol = symbol ?? selectedSymbol;
    final currentRequest = ++requestGeneration;

    try {
      final query = '?symbol=${Uri.encodeQueryComponent(requestSymbol)}';

      final results = await Future.wait([
        getJson('/api/status$query'),
        getJson('/api/trades$query'),
        getJson('/api/equity$query'),
        getJson('/api/market$query'),
      ]);

      if (!mounted) {
        return;
      }

      final loadedStatus = Map<String, dynamic>.from(results[0] as Map);

      if (loadedStatus['available'] != true) {
        throw Exception(loadedStatus['error'] ?? 'Brak stanu aktywa');
      }

      final loadedStrategy = Map<String, dynamic>.from(
        loadedStatus['strategy'] as Map? ?? {},
      );

      if (loadedStrategy['symbol'] != requestSymbol) {
        throw Exception(
          'API zwróciło ${loadedStrategy['symbol'] ?? 'inne aktywo'} '
          'zamiast $requestSymbol',
        );
      }

      setState(() {
        if (currentRequest != requestGeneration ||
            requestSymbol != selectedSymbol) {
          return;
        }

        status = loadedStatus;
        trades = List<dynamic>.from(results[1] as List);

        final equityData = Map<String, dynamic>.from(results[2] as Map);

        equity = List<dynamic>.from(equityData['points'] as List? ?? []);

        final marketData = Map<String, dynamic>.from(results[3] as Map);

        marketCandles = List<dynamic>.from(marketData['points'] as List? ?? []);

        error = null;
        loading = false;
        lastUpdate = DateTime.now();
      });
    } catch (exc) {
      if (!mounted) {
        return;
      }

      setState(() {
        if (currentRequest != requestGeneration) {
          return;
        }

        error = exc.toString();
        loading = false;
      });
    }
  }

  String money(dynamic value) {
    final number = (value as num?)?.toDouble() ?? 0.0;
    return number.toStringAsFixed(2);
  }

  String money4(dynamic value) {
    final number = (value as num?)?.toDouble() ?? 0.0;
    return number.toStringAsFixed(4);
  }

  String pct(dynamic value) {
    final number = (value as num?)?.toDouble() ?? 0.0;
    return '${number.toStringAsFixed(2)}%';
  }

  Widget metricCard({
    required String title,
    required String value,
    String? subtitle,
    Color? valueColor,
  }) {
    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(color: Colors.white60, fontSize: 13),
            ),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                fontSize: 27,
                fontWeight: FontWeight.bold,
                color: valueColor,
              ),
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 5),
              Text(
                subtitle,
                style: const TextStyle(color: Colors.white54, fontSize: 12),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget sectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 10, top: 10),
      child: Text(
        title,
        style: const TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
      ),
    );
  }

  Widget buildAssetSelector() {
    final symbols = assets
        .map((asset) => asset['symbol']?.toString())
        .whereType<String>()
        .toList();

    if (!symbols.contains(selectedSymbol)) {
      symbols.insert(0, selectedSymbol);
    }

    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
        child: Row(
          children: [
            const Text(
              'AKTYWO TRENINGOWE',
              style: TextStyle(color: Colors.white60, fontSize: 12),
            ),
            const SizedBox(width: 18),
            DropdownButton<String>(
              value: selectedSymbol,
              items: symbols
                  .map(
                    (symbol) => DropdownMenuItem<String>(
                      value: symbol,
                      child: Text(symbol),
                    ),
                  )
                  .toList(),
              onChanged: (symbol) {
                if (symbol == null || symbol == selectedSymbol) {
                  return;
                }

                setState(() {
                  selectedSymbol = symbol;
                  status = null;
                  loading = true;
                  error = null;
                });

                if (widget.liveMode) {
                  loadData(symbol: symbol);
                }
              },
            ),
            const SizedBox(width: 12),
            const Expanded(
              child: Text(
                'Paper trading — bez prawdziwych zleceń',
                textAlign: TextAlign.right,
                style: TextStyle(color: Colors.white38, fontSize: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget infoItem(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(color: Colors.white54, fontSize: 12),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
      ],
    );
  }

  Widget buildPosition(
    Map<String, dynamic> account,
    Map<String, dynamic> position,
  ) {
    final side = position['side'];
    final isFlat = side == null;

    double unrealizedPnl = 0.0;

    if (!isFlat) {
      final entry = (position['entry_price'] as num).toDouble();

      final market = (account['market_price'] as num).toDouble();

      final quantity = (position['quantity'] as num).toDouble();

      if (side == 'SELL') {
        unrealizedPnl = (entry - market) * quantity;
      } else {
        unrealizedPnl = (market - entry) * quantity;
      }
    }

    final pnlPositive = unrealizedPnl >= 0;

    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              isFlat ? 'FLAT' : '${side.toString().toUpperCase()} OPEN',
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
                color: isFlat
                    ? Colors.white70
                    : side == 'SELL'
                    ? Colors.redAccent
                    : Colors.greenAccent,
              ),
            ),
            const SizedBox(height: 18),
            if (!isFlat) ...[
              Wrap(
                spacing: 50,
                runSpacing: 20,
                children: [
                  infoItem('Wejście', money(position['entry_price'])),
                  infoItem('Rynek', money(account['market_price'])),
                  infoItem('Ilość', position['quantity'].toString()),
                  infoItem('Stop Loss', money(position['stop_loss'])),
                  infoItem('Take Profit', money(position['take_profit'])),
                  infoItem(
                    'Świece pozycji',
                    account['position_candles'].toString(),
                  ),
                  infoItem(
                    'Niezrealizowany wynik',
                    '${pnlPositive ? '+' : ''}${money4(unrealizedPnl)}',
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Text(
                'NIEZREALIZOWANY WYNIK',
                style: const TextStyle(color: Colors.white54, fontSize: 12),
              ),
              const SizedBox(height: 5),
              Text(
                '${pnlPositive ? '+' : ''}${money4(unrealizedPnl)}',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: pnlPositive ? Colors.greenAccent : Colors.redAccent,
                ),
              ),
            ] else ...[
              infoItem(selectedSymbol, money(account['market_price'])),
            ],
          ],
        ),
      ),
    );
  }

  Widget buildMarketChart() {
    if (marketCandles.isEmpty) {
      return const Card(
        elevation: 0,
        child: SizedBox(
          height: 360,
          child: Center(child: Text('Brak danych rynku')),
        ),
      );
    }

    final candles = marketCandles.asMap().entries.map((entry) {
      final candle = Map<String, dynamic>.from(entry.value as Map);

      return CandlestickSpot(
        x: entry.key.toDouble(),
        open: (candle['open'] as num).toDouble(),
        high: (candle['high'] as num).toDouble(),
        low: (candle['low'] as num).toDouble(),
        close: (candle['close'] as num).toDouble(),
      );
    }).toList();

    final lows = candles.map((c) => c.low).toList();
    final highs = candles.map((c) => c.high).toList();

    var minY = lows.first;
    var maxY = highs.first;

    for (final value in lows) {
      if (value < minY) {
        minY = value;
      }
    }

    for (final value in highs) {
      if (value > maxY) {
        maxY = value;
      }
    }

    final range = maxY - minY;
    final padding = range > 0 ? range * 0.08 : 10.0;

    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 18, 20, 18),
        child: SizedBox(
          height: 360,
          child: CandlestickChart(
            CandlestickChartData(
              minX: 0,
              maxX: (candles.length - 1).toDouble(),
              minY: minY - padding,
              maxY: maxY + padding,
              candlestickSpots: candles,
              gridData: const FlGridData(show: true, drawVerticalLine: false),
              borderData: FlBorderData(show: false),
              titlesData: FlTitlesData(
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 72,
                    getTitlesWidget: (value, meta) => SideTitleWidget(
                      meta: meta,
                      child: Text(value.toStringAsFixed(1)),
                    ),
                  ),
                ),
                topTitles: const AxisTitles(
                  sideTitles: SideTitles(showTitles: false),
                ),
                rightTitles: const AxisTitles(
                  sideTitles: SideTitles(showTitles: false),
                ),
                bottomTitles: const AxisTitles(
                  sideTitles: SideTitles(showTitles: false),
                ),
              ),
              candlestickTouchData: CandlestickTouchData(
                enabled: true,
                handleBuiltInTouches: true,
              ),
            ),
            duration: Duration.zero,
          ),
        ),
      ),
    );
  }

  Widget buildEquityChart() {
    if (equity.isEmpty) {
      return const Card(
        child: SizedBox(
          height: 300,
          child: Center(child: Text('Brak danych krzywej kapitału')),
        ),
      );
    }

    final points = equity
        .map(
          (point) => FlSpot(
            (point['index'] as num).toDouble(),
            (point['balance'] as num).toDouble(),
          ),
        )
        .toList();

    final values = points.map((point) => point.y).toList();

    var minY = values.first;
    var maxY = values.first;

    for (final value in values) {
      if (value < minY) {
        minY = value;
      }
      if (value > maxY) {
        maxY = value;
      }
    }

    final range = maxY - minY;
    final padding = range > 0 ? range * 0.15 : 0.5;

    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 18, 20, 18),
        child: SizedBox(
          height: 300,
          child: LineChart(
            LineChartData(
              minY: minY - padding,
              maxY: maxY + padding,
              gridData: const FlGridData(show: true, drawVerticalLine: false),
              borderData: FlBorderData(show: false),
              lineTouchData: LineTouchData(
                touchTooltipData: LineTouchTooltipData(
                  fitInsideHorizontally: true,
                  fitInsideVertically: true,
                  getTooltipItems: (touchedSpots) => touchedSpots.map((spot) {
                    final textStyle = TextStyle(
                      color: spot.bar.color ?? Colors.blueGrey,
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    );
                    return LineTooltipItem(
                      spot.y.toStringAsFixed(1),
                      textStyle,
                    );
                  }).toList(),
                ),
              ),
              titlesData: FlTitlesData(
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 64,
                    getTitlesWidget: (value, meta) => SideTitleWidget(
                      meta: meta,
                      child: Text(value.toStringAsFixed(1)),
                    ),
                  ),
                ),
                bottomTitles: const AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 30,
                    maxIncluded: false,
                  ),
                ),
                topTitles: const AxisTitles(
                  sideTitles: SideTitles(showTitles: false),
                ),
                rightTitles: const AxisTitles(
                  sideTitles: SideTitles(showTitles: false),
                ),
              ),
              lineBarsData: [
                LineChartBarData(
                  spots: points,
                  isCurved: true,
                  barWidth: 2.5,
                  dotData: const FlDotData(show: false),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget buildTrades() {
    if (trades.isEmpty) {
      return const Card(
        elevation: 0,
        child: Padding(
          padding: EdgeInsets.all(20),
          child: Text('Brak zamkniętych transakcji.'),
        ),
      );
    }

    return Card(
      elevation: 0,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          columns: const [
            DataColumn(label: Text('#')),
            DataColumn(label: Text('Kierunek')),
            DataColumn(label: Text('Wejście')),
            DataColumn(label: Text('Wyjście')),
            DataColumn(label: Text('Powód')),
            DataColumn(label: Text('Wynik netto')),
            DataColumn(label: Text('Prowizja')),
          ],
          rows: trades.map((trade) {
            final profit = (trade['profit'] as num).toDouble();

            return DataRow(
              cells: [
                DataCell(Text(trade['trade_number'].toString())),
                DataCell(Text(trade['side'].toString())),
                DataCell(Text(money(trade['entry_price']))),
                DataCell(Text(money(trade['exit_price']))),
                DataCell(Text(trade['exit_reason'].toString())),
                DataCell(
                  Text(
                    money4(profit),
                    style: TextStyle(
                      color: profit >= 0
                          ? Colors.greenAccent
                          : Colors.redAccent,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                DataCell(Text(money4(trade['fee']))),
              ],
            );
          }).toList(),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (loading && status == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (status == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('AL Trading Agent')),
        body: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            buildAssetSelector(),
            const SizedBox(height: 24),
            Center(child: Text(error ?? 'Brak danych z API.')),
          ],
        ),
      );
    }

    final account = Map<String, dynamic>.from(status!['account'] as Map);

    final performance = Map<String, dynamic>.from(
      status!['performance'] as Map,
    );

    final strategy = Map<String, dynamic>.from(status!['strategy'] as Map);

    final position = Map<String, dynamic>.from(status!['position'] as Map);

    final portfolioBalance = (account['balance'] as num?)?.toDouble() ?? 0.0;
    final initialBalance =
        (account['initial_balance'] as num?)?.toDouble() ?? 1000.0;
    final earned = portfolioBalance - initialBalance;
    final isEarnedPositive = earned >= 0;

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'AL TRADING AGENT',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        actions: [
          const Icon(Icons.circle, color: Colors.greenAccent, size: 11),
          const SizedBox(width: 7),
          const Text('PAPER LIVE'),
          const SizedBox(width: 18),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: loadData,
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            if (error != null)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Text(
                    'BŁĄD API: $error',
                    style: const TextStyle(color: Colors.redAccent),
                  ),
                ),
              ),

            buildAssetSelector(),

            sectionTitle('KONTO'),

            LayoutBuilder(
              builder: (context, constraints) {
                final cards = [
                  metricCard(
                    title: 'PORTFEL',
                    value: '${money(portfolioBalance)} zł',
                    subtitle: 'Wpłata początkowa ${money(initialBalance)}',
                  ),
                  metricCard(
                    title: 'ZAROBIONO',
                    value: '${isEarnedPositive ? '+' : ''}${money(earned)} zł',
                    subtitle: 'Od wpłaty początkowej',
                    valueColor: isEarnedPositive
                        ? Colors.greenAccent
                        : Colors.redAccent,
                  ),
                  metricCard(
                    title: 'MAKS. OBSUNIĘCIE',
                    value: money(account['max_drawdown']),
                    subtitle: 'Ryzyko',
                  ),
                  metricCard(
                    title: selectedSymbol,
                    value: money(account['market_price']),
                    subtitle: 'Rynek',
                  ),
                ];

                return GridView.count(
                  crossAxisCount: constraints.maxWidth >= 950 ? 4 : 2,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  childAspectRatio: 1.8,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  children: cards,
                );
              },
            ),

            sectionTitle('POZYCJA'),
            buildPosition(account, position),

            sectionTitle('WYNIKI'),

            LayoutBuilder(
              builder: (context, constraints) {
                final cards = [
                  metricCard(
                    title: 'TRANSAKCJE',
                    value: performance['trades'].toString(),
                  ),
                  metricCard(
                    title: 'ZYSKOWNE',
                    value: performance['wins'].toString(),
                  ),
                  metricCard(
                    title: 'STRATNE',
                    value: performance['losses'].toString(),
                  ),
                  metricCard(
                    title: 'SKUTECZNOŚĆ',
                    value: pct(performance['win_rate']),
                  ),
                  metricCard(
                    title: 'WSPÓŁCZYNNIK ZYSKU',
                    value: performance['profit_factor'] == null
                        ? 'N/A'
                        : money4(performance['profit_factor']),
                  ),
                  metricCard(
                    title: 'OCZEKIWANA WARTOŚĆ',
                    value: money4(performance['expectancy']),
                  ),
                ];

                return GridView.count(
                  crossAxisCount: constraints.maxWidth >= 1100 ? 6 : 2,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  childAspectRatio: 1.6,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  children: cards,
                );
              },
            ),

            sectionTitle('STRATEGIA PAPER · ${strategy['symbol']}'),

            Card(
              elevation: 0,
              child: Padding(
                padding: const EdgeInsets.all(18),
                child: Wrap(
                  spacing: 35,
                  runSpacing: 18,
                  children: [
                    infoItem('BUY RSI', strategy['buy_rsi'].toString()),
                    infoItem('SELL RSI', strategy['sell_rsi'].toString()),
                    infoItem(
                      'MAKS. CZAS',
                      strategy['max_position_candles'].toString(),
                    ),
                    infoItem(
                      'MIN. RÓŻNICA',
                      strategy['min_difference'].toString(),
                    ),
                    infoItem('RSI', strategy['rsi_method'].toString()),
                    infoItem('PROWIZJA', strategy['trading_fee'].toString()),
                  ],
                ),
              ),
            ),

            sectionTitle('RYNEK ${strategy['symbol']} · ${strategy['interval']}'),
            buildMarketChart(),

            sectionTitle('KRZYWA KAPITAŁU'),
            buildEquityChart(),

            sectionTitle('HISTORIA TRANSAKCJI'),
            buildTrades(),

            const SizedBox(height: 25),

            Center(
              child: Text(
                lastUpdate == null
                    ? 'Automatyczne odświeżanie: 5 s'
                    : 'Automatyczne odświeżanie: 5 s  •  '
                          'Aktualizacja ${lastUpdate!.hour.toString().padLeft(2, '0')}:'
                          '${lastUpdate!.minute.toString().padLeft(2, '0')}:'
                          '${lastUpdate!.second.toString().padLeft(2, '0')}',
                style: const TextStyle(color: Colors.white38),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
