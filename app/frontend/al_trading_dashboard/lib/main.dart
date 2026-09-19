import 'dart:async';
import 'dart:convert';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'ai_panel.dart';

const List<Map<String, String>> fallbackAssets = [
  {'symbol': 'BTCUSDT', 'name': 'Bitcoin', 'asset_type': 'crypto'},
  {'symbol': 'ETHUSDT', 'name': 'Ethereum', 'asset_type': 'crypto'},
  {'symbol': 'SOLUSDT', 'name': 'Solana', 'asset_type': 'crypto'},
  {'symbol': 'BNBUSDT', 'name': 'BNB', 'asset_type': 'crypto'},
  {'symbol': 'XRPUSDT', 'name': 'XRP', 'asset_type': 'crypto'},
  {'symbol': 'GOLD_FUT_CONT', 'name': 'Złoto (futures proxy)', 'asset_type': 'gold'},
  {'symbol': 'WTI_FUT_CONT', 'name': 'Ropa WTI (futures proxy)', 'asset_type': 'oil'},
  {'symbol': 'EURUSD', 'name': 'Euro / dolar', 'asset_type': 'forex'},
  {'symbol': 'AAPL', 'name': 'Apple', 'asset_type': 'stock'},
];

const String apiBaseUrl = String.fromEnvironment(
  'AL_TRADING_API_BASE_URL',
  defaultValue: 'http://127.0.0.1:8000',
);

class ChartAxisBounds {
  final double minY;
  final double maxY;

  const ChartAxisBounds({required this.minY, required this.maxY});
}

ChartAxisBounds marketChartAxisBounds(Iterable<dynamic> rawCandles) {
  final candles = rawCandles
      .map((value) => Map<String, dynamic>.from(value as Map))
      .toList();

  if (candles.isEmpty) {
    throw ArgumentError('marketChartAxisBounds requires at least one candle');
  }

  var minLow = (candles.first['low'] as num).toDouble();
  var maxHigh = (candles.first['high'] as num).toDouble();

  for (final candle in candles) {
    final low = (candle['low'] as num).toDouble();
    final high = (candle['high'] as num).toDouble();

    if (low < minLow) {
      minLow = low;
    }
    if (high > maxHigh) {
      maxHigh = high;
    }
  }

  final range = maxHigh - minLow;
  final padding = range > 0 ? range * 0.08 : 10.0;

  return ChartAxisBounds(
    minY: minLow - padding,
    maxY: maxHigh + padding,
  );
}

String equityAxisLabel(num value) => value.toDouble().toStringAsFixed(1);

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
  Map<String, dynamic>? marketInfo;
  List<Map<String, dynamic>> assets = fallbackAssets
      .map((asset) => Map<String, dynamic>.from(asset))
      .toList();
  String selectedSymbol = 'BTCUSDT';
  int requestGeneration = 0;
  Map<String, dynamic>? aiData;
  String? aiError;
  bool aiLoading = false;
  Map<String, dynamic>? userPortfolio;
  Map<String, Map<String, dynamic>> assetStatuses = {};
  String? userPortfolioError;
  bool followAiSelection = false;

  String? error;
  bool loading = true;
  DateTime? lastUpdate;

  Timer? timer;

  @override
  void initState() {
    super.initState();

    if (widget.liveMode) {
      loadAssets();
      loadAssetOverview();
      loadData();
      loadAi();
      loadUserPortfolio();

      timer = Timer.periodic(const Duration(seconds: 5), (_) {
        loadData();
        loadAi();
        loadUserPortfolio();
        loadAssetOverview();
      });
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
    userPortfolio = {
      'available': true,
      'balance': 0.0,
      'total_deposited': 0.0,
      'total_withdrawn': 0.0,
      'result': 0.0,
    };

    status = {
      'available': true,
      'strategy': {
        'symbol': selectedSymbol,
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
        'quote_currency': 'USDT',
        'balance_pln': 3800.0,
        'initial_balance_pln': 3800.0,
        'net_profit_pln': 0.0,
        'unrealized_profit_pln': 0.0,
        'max_drawdown_pln': 0.0,
        'market_price_pln': 0.0,
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
    marketInfo = {
      'provider': 'test',
      'provider_symbol': selectedSymbol,
      'stale': false,
      'age_seconds': 0.0,
      'pln': {'available': true, 'path': 'TEST→PLN'},
    };

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

  Future<dynamic> postJson(String endpoint, double amount) async {
    final response = await http
        .post(
          Uri.parse('$apiBaseUrl$endpoint'),
          headers: {'content-type': 'application/json'},
          body: jsonEncode({'amount': amount}),
        )
        .timeout(const Duration(seconds: 5));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('HTTP ${response.statusCode}: ${response.body}');
    }
    return jsonDecode(response.body);
  }

  Future<void> loadUserPortfolio() async {
    try {
      final result = await getJson('/api/user-portfolio');
      if (!mounted) return;
      setState(() {
        userPortfolio = Map<String, dynamic>.from(result as Map);
        userPortfolioError = null;
      });
    } catch (exc) {
      if (mounted) setState(() => userPortfolioError = exc.toString());
    }
  }

  Future<void> changeUserFunds({required bool deposit}) async {
    final controller = TextEditingController();
    final amount = await showDialog<double>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          deposit ? 'Wpłata do mojego portfela' : 'Wypłata z mojego portfela',
        ),
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
    try {
      final result = await postJson(
        deposit
            ? '/api/user-portfolio/deposit'
            : '/api/user-portfolio/withdraw',
        amount,
      );
      if (mounted) {
        setState(
          () => userPortfolio = Map<String, dynamic>.from(result as Map),
        );
      }
    } catch (exc) {
      if (mounted) setState(() => userPortfolioError = exc.toString());
    }
  }

  Widget buildUserPortfolio() {
    final portfolio = userPortfolio;
    if (portfolio == null) {
      return const Card(
        child: ListTile(
          title: Text('MÓJ PORTFEL'),
          subtitle: Text('Ładowanie...'),
        ),
      );
    }
    final balance = (portfolio['balance'] as num?)?.toDouble() ?? 0;
    final deposited = (portfolio['total_deposited'] as num?)?.toDouble() ?? 0;
    final withdrawn = (portfolio['total_withdrawn'] as num?)?.toDouble() ?? 0;
    final result = (portfolio['result'] as num?)?.toDouble() ?? 0;
    final aiProfit = (portfolio['profit_transferred'] as num?)?.toDouble() ?? 0;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'MÓJ PORTFEL',
              style: TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'Saldo: ${balance.toStringAsFixed(2)} PLN',
              style: const TextStyle(fontSize: 20),
            ),
            Text(
              'Wpłaty: ${deposited.toStringAsFixed(2)} PLN • Wypłaty: ${withdrawn.toStringAsFixed(2)} PLN',
            ),
            Text(
              'Wynik: ${result >= 0 ? '+' : ''}${result.toStringAsFixed(2)} PLN',
            ),
            Text(
              'Zysk przekazany przez AI: ${aiProfit.toStringAsFixed(2)} PLN',
            ),
            if (userPortfolioError != null)
              Text(
                userPortfolioError!,
                style: const TextStyle(color: Colors.redAccent),
              ),
            Wrap(
              spacing: 8,
              children: [
                FilledButton.tonal(
                  onPressed: () => changeUserFunds(deposit: true),
                  child: const Text('Wpłać'),
                ),
                OutlinedButton(
                  onPressed: () => changeUserFunds(deposit: false),
                  child: const Text('Wypłać'),
                ),
              ],
            ),
            const Text(
              'Ten portfel jest niezależny od portfela AI i nie składa zleceń.',
              style: TextStyle(color: Colors.white60, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> loadAi() async {
    if (aiLoading) return;
    aiLoading = true;
    final requestedSymbol = selectedSymbol;
    try {
      final result = await getJson(
        "/api/ai?symbol=${Uri.encodeQueryComponent(requestedSymbol)}",
      );
      if (!mounted) return;
      setState(() {
        if (requestedSymbol != selectedSymbol) return;
        aiData = Map<String, dynamic>.from(result as Map);
        aiError = null;
      });
      followAiAsset();
    } catch (exc) {
      if (mounted) setState(() => aiError = exc.toString());
    } finally {
      aiLoading = false;
    }
  }

  void selectAsset(String symbol, {bool fromAi = false}) {
    if (!fromAi && followAiSelection) {
      setState(() => followAiSelection = false);
    }
    if (symbol == selectedSymbol) return;
    setState(() {
      selectedSymbol = symbol;
      aiData = null;
      aiError = null;
      requestGeneration++;
      status = null;
      trades = [];
      equity = [];
      marketCandles = [];
      marketInfo = null;
      loading = true;
      error = null;
      if (!widget.liveMode) _loadTestData();
    });
    if (widget.liveMode) {
      loadData(symbol: symbol);
      loadAi();
    }
  }

  void followAiAsset() {
    if (!followAiSelection ||
        aiData?['available'] != true ||
        aiData?['stale'] == true ||
        aiError != null) {
      return;
    }
    final position = aiData?['position'] as Map?;
    final decision = aiData?['decision'] as Map?;
    final symbol = position?['symbol'] ?? decision?['symbol'];
    if (symbol is String) selectAsset(symbol, fromAi: true);
  }

  Widget buildAiPanel() => AiPanel(
    data: aiData,
    error: aiError,
    onSelectAsset: selectAsset,
    followSelection: followAiSelection,
    onFollowChanged: (value) {
      setState(() => followAiSelection = value);
      followAiAsset();
    },
  );

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
      await loadAssetOverview();
    } catch (_) {
      // The legacy BTC-only API can still drive the dashboard.
    }
  }

  bool overviewLoading = false;
  DateTime? overviewReceived;
  Future<void> loadAssetOverview() async {
    if (overviewLoading) return;
    overviewLoading = true;
    try {
      final response = await getJson('/api/assets') as List;
      overviewReceived = DateTime.now();
      if (mounted) {
        setState(() {
          assetStatuses = {
            for (final raw in response)
              if (raw is Map)
                raw['symbol'].toString(): {
                  'available': raw['state_available'] == true,
                  'stale': false,
                  'pln_available': (raw['pln'] as Map?)?['available'] == true,
                  'account': {
                    'market_price': raw['market_price'],
                    'market_price_pln': raw['market_price_pln'],
                    'net_profit': raw['net_profit'],
                    'net_profit_pln': raw['net_profit_pln'],
                    'quote_currency': raw['quote'],
                    'position': raw['position'],
                  },
                  'strategy': {
                    'asset_name': raw['name'],
                    'instrument_type': raw['instrument_type'],
                  },
                },
          };
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          assetStatuses = {
            for (final entry in assetStatuses.entries)
              entry.key: {...entry.value, 'stale': true},
          };
        });
      }
    } finally {
      overviewLoading = false;
    }
  }

  Widget buildAssetOverview() {
    if (assetStatuses.isEmpty) return const SizedBox.shrink();
    final cards = assets.map((asset) {
      final symbol = asset['symbol']?.toString() ?? '';
      final state = assetStatuses[symbol];
      final account = state?['account'] as Map?;
      final strategy = state?['strategy'] as Map?;
      final available = state?['available'] == true;
      final stale = state?['stale'] == true;
      final pnl = (account?['net_profit'] as num?)?.toDouble() ?? 0;
      final pnlPln = (account?['net_profit_pln'] as num?)?.toDouble();
      final quote = account?['quote_currency']?.toString() ?? '';
      final plnAvailable = state?['pln_available'] == true;
      return InkWell(
        onTap: available ? () => selectAsset(symbol) : null,
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  symbol,
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                Text(
                  strategy?['asset_name']?.toString() ??
                      asset['name']?.toString() ??
                      '',
                  style: const TextStyle(color: Colors.white54, fontSize: 12),
                ),
                const Spacer(),
                Text(
                  available
                      ? ((account?['market_price'] as num)
                            .toDouble()
                            .toStringAsFixed(
                              (account?['market_price'] as num) < 10 ? 5 : 2,
                            ))
                      : 'Brak danych',
                  style: const TextStyle(fontSize: 18),
                ),
                Text(
                  stale
                      ? 'Dane nieaktualne / błąd połączenia'
                      : plnAvailable && pnlPln != null
                      ? '${pnlPln >= 0 ? '+' : ''}${money(pnlPln)} PLN'
                      : '${pnl >= 0 ? '+' : ''}${money(pnl)} $quote',
                  style: TextStyle(
                    color: stale
                        ? Colors.orange
                        : (pnl >= 0 ? Colors.greenAccent : Colors.redAccent),
                  ),
                ),
                Text(
                  account?['position']?.toString() ?? 'FLAT',
                  style: const TextStyle(color: Colors.white54, fontSize: 11),
                ),
              ],
            ),
          ),
        ),
      );
    }).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        sectionTitle('WSZYSTKIE RYNKI · PAPER LIVE'),
        Text(
          'Ostatni odbiór: ${overviewReceived?.toLocal().toString().substring(11, 19) ?? 'oczekiwanie'} • sprawdzanie co 5 s',
        ),
        LayoutBuilder(
          builder: (context, constraints) => GridView.count(
            crossAxisCount: constraints.maxWidth >= 1200
                ? 5
                : constraints.maxWidth >= 700
                ? 3
                : 2,
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
            childAspectRatio: 1.55,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            children: cards,
          ),
        ),
      ],
    );
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
        marketInfo = marketData;

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
              'RYNEK PAPER',
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

                selectAsset(symbol);
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
    final quote = account['quote_currency']?.toString() ?? '';
    final unrealizedPln = (account['unrealized_profit_pln'] as num?)?.toDouble();
    final marketPricePln = (account['market_price_pln'] as num?)?.toDouble();

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
                  infoItem(
                    'Rynek',
                    marketPricePln == null
                        ? '${money(account['market_price'])} $quote'
                        : '${money(account['market_price'])} $quote · ${money(marketPricePln)} PLN',
                  ),
                  infoItem('Ilość', position['quantity'].toString()),
                  infoItem('Stop Loss', money(position['stop_loss'])),
                  infoItem('Take Profit', money(position['take_profit'])),
                  infoItem(
                    'Świece pozycji',
                    account['position_candles'].toString(),
                  ),
                  infoItem(
                    'Niezrealizowany wynik',
                    unrealizedPln == null
                        ? '${pnlPositive ? '+' : ''}${money4(unrealizedPnl)} $quote'
                        : '${unrealizedPln >= 0 ? '+' : ''}${money(unrealizedPln)} PLN',
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
                unrealizedPln == null
                    ? '${pnlPositive ? '+' : ''}${money4(unrealizedPnl)} $quote'
                    : '${unrealizedPln >= 0 ? '+' : ''}${money(unrealizedPln)} PLN',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: pnlPositive ? Colors.greenAccent : Colors.redAccent,
                ),
              ),
            ] else ...[
              infoItem(
                selectedSymbol,
                marketPricePln == null
                    ? '${money(account['market_price'])} $quote'
                    : '${money(account['market_price'])} $quote · ${money(marketPricePln)} PLN',
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget buildMarketQuality() {
    final info = marketInfo;
    if (info == null) return const SizedBox.shrink();

    final stale = info['stale'] == true;
    final age = (info['age_seconds'] as num?)?.toDouble();
    final pln = info['pln'] as Map?;
    final plnAvailable = pln?['available'] == true;
    final plnPath = pln?['path']?.toString() ?? 'realne przeliczenie';
    final provider = info['provider']?.toString() ?? '—';
    final providerSymbol = info['provider_symbol']?.toString() ?? selectedSymbol;

    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Wrap(
          spacing: 24,
          runSpacing: 8,
          children: [
            Text('Źródło: $provider · $providerSymbol'),
            Text(
              stale
                  ? 'Dane: NIEAKTUALNE'
                  : 'Dane: aktualne${age == null ? '' : ' · ${age.toStringAsFixed(0)} s'}',
              style: TextStyle(
                color: stale ? Colors.orangeAccent : Colors.greenAccent,
              ),
            ),
            Text(
              plnAvailable
                  ? 'PLN: $plnPath'
                  : 'PLN: chwilowo niedostępny',
              style: TextStyle(
                color: plnAvailable ? Colors.white70 : Colors.orangeAccent,
              ),
            ),
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

    // Market autoscaling intentionally uses candle high/low only.
    // Position overlays such as entry, stop loss or take profit must never
    // stretch the visible candle range.
    final yBounds = marketChartAxisBounds(marketCandles);

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
              minY: yBounds.minY,
              maxY: yBounds.maxY,
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
            ((point['balance_pln'] ?? point['balance']) as num).toDouble(),
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
                      equityAxisLabel(spot.y),
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
                      child: Text(equityAxisLabel(value)),
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
            final profitPln = (trade['profit_pln'] as num?)?.toDouble();
            final feePln = (trade['fee_pln'] as num?)?.toDouble();
            final quote = trade['quote_currency']?.toString() ?? '';

            return DataRow(
              cells: [
                DataCell(Text(trade['trade_number'].toString())),
                DataCell(Text(trade['side'].toString())),
                DataCell(Text(money(trade['entry_price']))),
                DataCell(Text(money(trade['exit_price']))),
                DataCell(Text(trade['exit_reason'].toString())),
                DataCell(
                  Text(
                    profitPln == null
                        ? '${money4(profit)} $quote'
                        : '${profitPln >= 0 ? '+' : ''}${money(profitPln)} PLN',
                    style: TextStyle(
                      color: profit >= 0
                          ? Colors.greenAccent
                          : Colors.redAccent,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                DataCell(
                  Text(
                    feePln == null
                        ? '${money4(trade['fee'])} $quote'
                        : '${money(feePln)} PLN',
                  ),
                ),
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
            buildAssetOverview(),
            buildUserPortfolio(),
            const SizedBox(height: 24),
            buildAiPanel(),
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
    final quote = account['quote_currency']?.toString() ?? '';
    final portfolioBalancePln = (account['balance_pln'] as num?)?.toDouble();
    final initialBalancePln = (account['initial_balance_pln'] as num?)?.toDouble();
    final earnedPln = (account['net_profit_pln'] as num?)?.toDouble();
    final drawdownPln = (account['max_drawdown_pln'] as num?)?.toDouble();
    final marketPricePln = (account['market_price_pln'] as num?)?.toDouble();
    final isEarnedPositive = (earnedPln ?? earned) >= 0;

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
            buildAssetOverview(),
            buildUserPortfolio(),

            sectionTitle('KONTO'),

            LayoutBuilder(
              builder: (context, constraints) {
                final cards = [
                  metricCard(
                    title: 'PORTFEL',
                    value: portfolioBalancePln == null
                        ? '${money(portfolioBalance)} $quote'
                        : '${money(portfolioBalancePln)} PLN',
                    subtitle: initialBalancePln == null
                        ? 'Wirtualne saldo · start ${money(initialBalance)} $quote'
                        : 'Wirtualne saldo · start ${money(initialBalancePln)} PLN',
                  ),
                  metricCard(
                    title: 'WYNIK',
                    value: earnedPln == null
                        ? '${isEarnedPositive ? '+' : ''}${money(earned)} $quote'
                        : '${isEarnedPositive ? '+' : ''}${money(earnedPln)} PLN',
                    subtitle: earnedPln == null
                        ? 'PLN chwilowo niedostępny'
                        : '${money(earned)} $quote · realne przeliczenie raportowe',
                    valueColor: isEarnedPositive
                        ? Colors.greenAccent
                        : Colors.redAccent,
                  ),
                  metricCard(
                    title: 'MAKS. OBSUNIĘCIE',
                    value: drawdownPln == null
                        ? '${money(account['max_drawdown'])} $quote'
                        : '${money(drawdownPln)} PLN',
                    subtitle: 'Ryzyko paper',
                  ),
                  metricCard(
                    title: selectedSymbol,
                    value: money(account['market_price']),
                    subtitle: marketPricePln == null
                        ? 'Cena w $quote'
                        : '${money(marketPricePln)} PLN · cena przeliczona',
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
                    value: performance['expectancy_pln'] == null
                        ? '${money4(performance['expectancy'])} $quote'
                        : '${money(performance['expectancy_pln'])} PLN',
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
                    if (strategy['execution_model'] ==
                        'INDEPENDENT_AI_PAPER') ...[
                      infoItem('MODEL', 'AI k-NN · osobny portfel'),
                      infoItem('POZYCJA', '5% testowa / 20% standardowa'),
                      infoItem('STOP / TAKE', '1% / 2%'),
                      infoItem('MAKS. CZAS', '10 świec'),
                    ] else ...[
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
                    ],
                    infoItem('PROWIZJA', strategy['trading_fee'].toString()),
                  ],
                ),
              ),
            ),

            sectionTitle(
              'RYNEK ${strategy['symbol']} · ${strategy['interval']}',
            ),
            buildMarketQuality(),
            buildMarketChart(),

            buildAiPanel(),

            sectionTitle('KRZYWA KAPITAŁU · PLN JEŚLI DOSTĘPNE'),
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
