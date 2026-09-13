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
  Map<String, dynamic>? aiData;
  String? aiError;
  bool aiLoading = false;
  Map<String, dynamic>? userPortfolio;
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
      loadData();
      loadAi();
      loadUserPortfolio();

      timer = Timer.periodic(const Duration(seconds: 5), (_) {
        loadData();
        loadAi();
        loadUserPortfolio();
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

  Future<dynamic> postJson(String endpoint, double amount) async {
    final response = await http.post(
      Uri.parse('$apiBaseUrl$endpoint'),
      headers: {'content-type': 'application/json'},
      body: jsonEncode({'amount': amount}),
    ).timeout(const Duration(seconds: 5));
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
        title: Text(deposit ? 'Wpłata do mojego portfela' : 'Wypłata z mojego portfela'),
        content: TextField(
          controller: controller,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Kwota PLN'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Anuluj')),
          FilledButton(
            onPressed: () => Navigator.pop(context, double.tryParse(
              controller.text.replaceAll(',', '.'),
            )),
            child: const Text('Zapisz'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (amount == null || amount <= 0) return;
    try {
      final result = await postJson(
        deposit ? '/api/user-portfolio/deposit' : '/api/user-portfolio/withdraw',
        amount,
      );
      if (mounted) setState(() => userPortfolio = Map<String, dynamic>.from(result as Map));
    } catch (exc) {
      if (mounted) setState(() => userPortfolioError = exc.toString());
    }
  }

  Widget buildUserPortfolio() {
    final portfolio = userPortfolio;
    if (portfolio == null) {
      return const Card(child: ListTile(title: Text('MÓJ PORTFEL'), subtitle: Text('Ładowanie...')));
    }
    final balance = (portfolio['balance'] as num?)?.toDouble() ?? 0;
    final deposited = (portfolio['total_deposited'] as num?)?.toDouble() ?? 0;
    final withdrawn = (portfolio['total_withdrawn'] as num?)?.toDouble() ?? 0;
    final result = (portfolio['result'] as num?)?.toDouble() ?? 0;
    final aiProfit = (portfolio['profit_transferred'] as num?)?.toDouble() ?? 0;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('MÓJ PORTFEL', style: TextStyle(fontSize: 19, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text('Saldo: ${balance.toStringAsFixed(2)} PLN', style: const TextStyle(fontSize: 20)),
          Text('Wpłaty: ${deposited.toStringAsFixed(2)} PLN • Wypłaty: ${withdrawn.toStringAsFixed(2)} PLN'),
          Text('Wynik: ${result >= 0 ? '+' : ''}${result.toStringAsFixed(2)} PLN'),
          Text('Zysk przekazany przez AI: ${aiProfit.toStringAsFixed(2)} PLN'),
          if (userPortfolioError != null)
            Text(userPortfolioError!, style: const TextStyle(color: Colors.redAccent)),
          Wrap(spacing: 8, children: [
            FilledButton.tonal(onPressed: () => changeUserFunds(deposit: true), child: const Text('Wpłać')),
            OutlinedButton(onPressed: () => changeUserFunds(deposit: false), child: const Text('Wypłać')),
          ]),
          const Text('Ten portfel jest niezależny od portfela AI i nie składa zleceń.', style: TextStyle(color: Colors.white60, fontSize: 12)),
        ]),
      ),
    );
  }

  Future<void> loadAi() async {
    if (aiLoading) return;
    aiLoading = true;
    try {
      final result = await getJson('/api/ai');
      if (!mounted) return;
      setState(() {
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
      requestGeneration++;
      status = null;
      trades = [];
      equity = [];
      marketCandles = [];
      loading = true;
      error = null;
      if (!widget.liveMode) _loadTestData();
    });
    if (widget.liveMode) loadData(symbol: symbol);
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
    return '${number.toString…6028 tokens truncated…nt, execution and safeguards

- Initial account: 1000 **simulation units**, not PLN. Assets are fractional
  price-return indices. USD and USDT are treated as equivalent for this exercise;
  FX conversion and USDT depegging are not modeled.
- Gold `XAUUSD` uses the existing `GC=F` futures price proxy; WTI uses `CL=F`.
  These are not spot gold, executable futures contracts or broker fills.
  Futures multipliers, rolls, financing, stock splits and dividends are not
  modeled. The registry currently contains one FX pair and one stock (AAPL).
- At most one long position, 20% of current balance committed, no leverage.
- Stop 1%, take profit 2%, maximum ten one-minute bars. The symbol/strategy is
  fixed until the position closes; afterwards the selector may choose another.
- Each side assumes a fee of 0.04% and slippage of 0.05%. These are test
  assumptions, not verified instrument-specific trading costs.
- A decision schedules the next not-yet-started bar's open. It is simulated
  only after that bar closes. Gap stops use the worse open; when both stop and
  take-profit occur in one bar the stop is assumed first.
- A stale/closed market (last closed bar over two minutes old) cannot receive
  new allocation. Delayed feeds may therefore be excluded. The current position
  is retained when its data is unavailable, with the problem shown in the panel.
- A cumulative realized loss of 20 units blocks new allocations for the UTC day.
  A 5% equity drawdown latches a halt across restarts. Outstanding positions
  continue receiving exit management when data becomes available. Stops and
  limits may be exceeded by gaps, latency and unavailable data.

State is atomically saved to ignored `data/live_state/ai_paper.json`. The last
300 decisions and trades are retained; failures roll back the in-memory cycle.
The model is rebuilt deterministically from fetched history, not serialized.
Only one `run_paper_live.py` process may write this account at a time.

## Running and dashboard

The existing `scripts/run_paper_live.py` runs an AI cycle after each baseline
multi-asset cycle, followed by the existing 60-second delay. Fetches use at most
three workers, each failure is reported per asset. Actual period includes
network/model time; a cycle older than 180 seconds is marked stale by `/api/ai`.

The read-only `GET /api/ai` endpoint returns decisions, rankings, per-market data
issues, account limits and trades. There are no order-execution HTTP endpoints.
The separate `user_portfolio.json` ledger accepts only manual paper deposits and
withdrawals. Realized AI profit above the 1000-unit base is swept into that
ledger as a PLN exercise result; the AI keeps its base for continued training.
This is accounting for the game and does not transfer real money.
The Flutter **AI · PORTFEL TRENINGOWY** panel is below the market chart. It shows
the separate AI account, rationale and audit history. Enable **Śledź wybór AI na
wykresie** to follow its selected symbol; manually selecting an asset disables
following. This controls the viewed chart, not the model's execution logic.
Missing or stale AI state is displayed explicitly; baseline API data remains
usable without the new endpoint.

## Verification and deployment

Run `python -m pytest tests/test_ai_manager.py` in the repository's virtual
environment. Tests cover leakage boundaries, costs, stale feeds, selection,
next-open execution, single allocation, gaps, switching, state restore and
persistence failure. Synthetic data verifies behavior, not expected profits.

In the Flutter directory run:

```text
dart format lib/main.dart lib/ai_panel.dart test/widget_test.dart
flutter analyze
flutter test test/widget_test.dart --reporter expanded
```

After verification and pushing an approved commit, update the repository **on
the VM**, restart `al-api` and `al-paper-live`, and check `/api/ai` after a full
cycle. Copying only the Flutter code does not deploy the AI on the VM.

Algorithm references (the project implements its own small Python version):
- https://sklearn.org/stable/modules/generated/sklearn.neighbors.KNeighborsRegressor.html
- https://sklearn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
