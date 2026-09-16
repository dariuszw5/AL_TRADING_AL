import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';

const cyberBg = Color(0xFF0B0E14);
const cyberPanel = Color(0xFF10151F);
const cyberLine = Color(0xFF1E232F);
const cyberGreen = Color(0xFF00FF66);
const cyberPink = Color(0xFFFF0055);
const cyberCyan = Color(0xFF00E5FF);
const cyberMuted = Color(0xFF8290A5);

class CyberDashboard extends StatefulWidget {
  final String baseUrl;
  const CyberDashboard({super.key, required this.baseUrl});

  @override
  State<CyberDashboard> createState() => _CyberDashboardState();
}

class _CyberDashboardState extends State<CyberDashboard> {
  final http.Client _client = IOClient(
    HttpClient()..findProxy = (_) => 'DIRECT',
  );
  Map<String, dynamic>? research;
  Map<String, dynamic>? manualPaper;
  List<Map<String, dynamic>> candles = [];
  String selected = 'BTCUSDT';
  String timeframe = '15m';
  int leverage = 50;
  int mobileTab = 0;
  String? error;
  Timer? timer;
  bool loading = false;

  @override
  void initState() {
    super.initState();
    refresh();
    timer = Timer.periodic(const Duration(seconds: 5), (_) => refresh());
  }

  @override
  void dispose() {
    timer?.cancel();
    _client.close();
    super.dispose();
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final response = await _client
        .get(
          Uri.parse('${widget.baseUrl}$path'),
          headers: const {'Cache-Control': 'no-cache'},
        )
        .timeout(const Duration(seconds: 12));
    if (response.statusCode != 200) {
      throw Exception('HTTP ${response.statusCode}');
    }
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> _post(
    String path,
    Map<String, dynamic> body,
  ) async {
    final response = await _client
        .post(
          Uri.parse('${widget.baseUrl}$path'),
          headers: const {'Content-Type': 'application/json'},
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 12));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        jsonDecode(response.body)['detail'] ?? 'HTTP ${response.statusCode}',
      );
    }
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<void> refresh() async {
    if (loading) {
      return;
    }
    loading = true;
    try {
      // A missing optional endpoint must never hide available market candles.
      final researchFuture = _get('/api/ai-research')
          .catchError((_) => <String, dynamic>{});
      final manualFuture = _get('/api/paper/manual')
          .catchError((_) => <String, dynamic>{});
      final market = await _get('/api/market?symbol=$selected');
      final researchValue = await researchFuture;
      final manualValue = await manualFuture;
      if (!mounted) {
        return;
      }
      setState(() {
        research = researchValue;
        manualPaper = manualValue.isEmpty ? manualPaper : manualValue;
        candles = (market['points'] as List? ?? [])
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList();
        error = market['available'] == false
            ? 'Brak świec dla $selected'
            : null;
      });
    } catch (exception) {
      if (mounted) {
        setState(() => error = 'Połączenie danych: $exception');
      }
    } finally {
      loading = false;
    }
  }

  Map get broker => research?['virtual_broker'] as Map? ?? {};
  Map get assets => research?['assets'] as Map? ?? {};
  Map get selectedAsset => assets[selected] as Map? ?? {};
  Map get selectedBest => selectedAsset['best'] as Map? ?? {};
  Map get manualPositions => manualPaper?['positions'] as Map? ?? {};
  bool get isPln => broker['currency'] == 'PLN';
  String money(Object? value, [int decimals = 2]) =>
      value is num ? value.toStringAsFixed(decimals) : '—';

  Future<void> manualOrder(String side) async {
    try {
      final data = await _post('/api/paper/open', {
        'symbol': selected,
        'side': side,
        'amount_pln': 100,
        'leverage': leverage,
      });
      if (!mounted) return;
      setState(() => manualPaper = data);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Otwarta pozycje $side dla $selected w portfelu testowym.',
          ),
        ),
      );
    } catch (exception) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Nie otwarto pozycji: $exception')),
        );
    }
  }

  Future<void> closeManualOrder() async {
    try {
      final data = await _post('/api/paper/close', {'symbol': selected});
      if (!mounted) return;
      setState(() => manualPaper = data);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pozycja testowa zostala zamknieta.')),
      );
    } catch (exception) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Nie zamknieto pozycji: $exception')),
        );
    }
  }

  Widget card(Widget child, {EdgeInsets padding = const EdgeInsets.all(18)}) =>
      Container(
        padding: padding,
        decoration: BoxDecoration(
          color: cyberPanel,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: cyberLine),
          boxShadow: const [
            BoxShadow(color: Color(0x3300E5FF), blurRadius: 10),
          ],
        ),
        child: child,
      );

  Widget badge(String label, Color color) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
    decoration: BoxDecoration(
      border: Border.all(color: color.withValues(alpha: .7)),
      borderRadius: BorderRadius.circular(4),
      color: color.withValues(alpha: .08),
    ),
    child: Text(
      label,
      style: TextStyle(color: color, fontSize: 11, letterSpacing: .7),
    ),
  );

  Widget metric(
    String label,
    String value,
    IconData icon, {
    Color color = cyberCyan,
  }) => card(
    Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: color, size: 19),
        const SizedBox(height: 14),
        Text(
          label.toUpperCase(),
          style: const TextStyle(
            color: cyberMuted,
            fontSize: 10,
            letterSpacing: 1,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          value,
          style: TextStyle(
            color: color,
            fontSize: 22,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    ),
  );

  Widget header() => Row(
    children: [
      const Text(
        'AL//',
        style: TextStyle(
          color: cyberCyan,
          fontSize: 23,
          fontWeight: FontWeight.w900,
        ),
      ),
      const Text(
        'TERMINAL',
        style: TextStyle(
          fontSize: 23,
          fontWeight: FontWeight.w800,
          letterSpacing: 1,
        ),
      ),
      const Spacer(),
      badge('PAPER ONLY', cyberGreen),
      const SizedBox(width: 10),
      IconButton(
        onPressed: refresh,
        icon: const Icon(Icons.refresh, color: cyberCyan),
        tooltip: 'Odśwież dane',
      ),
    ],
  );

  Widget selector() => card(
    Row(
      children: [
        const Icon(Icons.candlestick_chart, color: cyberCyan),
        const SizedBox(width: 12),
        const Text(
          'RYNEK',
          style: TextStyle(color: cyberMuted, fontSize: 11, letterSpacing: 1),
        ),
        const SizedBox(width: 12),
        DropdownButton<String>(
          value: assets.containsKey(selected) ? selected : null,
          dropdownColor: cyberPanel,
          underline: Container(height: 1, color: cyberCyan),
          items: assets.keys
              .map(
                (symbol) => DropdownMenuItem(
                  value: symbol.toString(),
                  child: Text(symbol.toString()),
                ),
              )
              .toList(),
          onChanged: (value) {
            if (value == null) {
              return;
            }
            setState(() => selected = value);
            refresh();
          },
        ),
        const Spacer(),
        for (final interval in const ['1m', '5m', '15m', '1h', '4h', '1d'])
          Padding(
            padding: const EdgeInsets.only(left: 8),
            child: InkWell(
              onTap: () => setState(() => timeframe = interval),
              child: badge(
                interval,
                interval == timeframe ? cyberGreen : cyberMuted,
              ),
            ),
          ),
      ],
    ),
  );

  Widget chartPanel() {
    final closes = candles
        .map((point) => (point['close'] as num?)?.toDouble())
        .whereType<double>()
        .toList();
    final rsi = _rsi(closes);
    final macd = _macd(closes);
    final bollinger = _bollinger(closes);
    final probability = selectedBest['profit_probability_lower'];
    return card(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                '$selected / ${isPln ? 'PLN' : 'QUOTE'}',
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 18,
                ),
              ),
              const SizedBox(width: 12),
              badge(
                selectedAsset['recommendation'] == 'OBSERVE_SIGNAL'
                    ? 'AI SIGNAL'
                    : 'AI OBSERVE',
                selectedAsset['recommendation'] == 'OBSERVE_SIGNAL'
                    ? cyberGreen
                    : cyberMuted,
              ),
              const Spacer(),
              Text(
                'RSI ${rsi == null ? '—' : rsi.toStringAsFixed(1)}',
                style: const TextStyle(color: cyberMuted),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            children: [
              _IndicatorChip(
                rsi == null ? 'RSI —' : 'RSI ${rsi.toStringAsFixed(1)}',
              ),
              _IndicatorChip(
                macd == null ? 'MACD —' : 'MACD ${macd.toStringAsFixed(2)}',
              ),
              _IndicatorChip(
                bollinger == null
                    ? 'BB —'
                    : 'BB ${bollinger[0].toStringAsFixed(2)} / ${bollinger[2].toStringAsFixed(2)}',
              ),
            ],
          ),
          const SizedBox(height: 14),
          SizedBox(
            height: 330,
            child: candles.isEmpty
                ? const Center(
                    child: Text(
                      'Oczekiwanie na rzeczywiste świece OHLC',
                      style: TextStyle(color: cyberMuted),
                    ),
                  )
                : CustomPaint(
                    painter: CandlePainter(
                      candles,
                      signal:
                          selectedAsset['recommendation'] == 'OBSERVE_SIGNAL',
                    ),
                  ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Text(
                'WOLUMEN • ${candles.isEmpty ? '—' : money(candles.last['volume'], 0)}',
                style: const TextStyle(color: cyberMuted, fontSize: 11),
              ),
              const Spacer(),
              if (probability is num)
                Text(
                  'P(zysk) ≥ ${(probability * 100).toStringAsFixed(1)}%',
                  style: const TextStyle(color: cyberGreen, fontSize: 12),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget depthPanel() => card(
    Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'LEVEL 2 • GŁĘBOKOŚĆ',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 16),
        const _DepthRow('ASKS', cyberPink),
        const SizedBox(height: 8),
        const _DepthRow('BIDS', cyberGreen),
        const Divider(color: cyberLine, height: 28),
        const Text(
          'LIVE TICKER',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 10),
        const Text(
          'Brak danych order book w API. Panel nie symuluje ofert ani transakcji.',
          style: TextStyle(color: cyberMuted, height: 1.5, fontSize: 12),
        ),
      ],
    ),
  );

  Widget executionPanel() => card(
    Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'PANEL EGZEKUCJI',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 14),
        const Text(
          'DŹWIGNIA',
          style: TextStyle(color: cyberMuted, fontSize: 11),
        ),
        const SizedBox(height: 4),
        const Row(
          children: [
            Text(
              '1×',
              style: TextStyle(color: cyberCyan, fontWeight: FontWeight.bold),
            ),
            Spacer(),
            Text(
              'WYŁĄCZONA',
              style: TextStyle(color: cyberMuted, fontSize: 11),
            ),
          ],
        ),
        Slider(
          value: 1,
          min: 1,
          max: 100,
          activeColor: cyberCyan,
          inactiveColor: cyberLine,
          onChanged: null,
        ),
        const Divider(color: cyberLine),
        const Text(
          'SENTYMENT MODELU',
          style: TextStyle(color: cyberMuted, fontSize: 11),
        ),
        const SizedBox(height: 8),
        LinearProgressIndicator(
          value: selectedAsset['recommendation'] == 'OBSERVE_SIGNAL'
              ? .62
              : .35,
          color: cyberCyan,
          backgroundColor: cyberLine,
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: FilledButton(
                onPressed: null,
                style: FilledButton.styleFrom(
                  backgroundColor: cyberGreen,
                  disabledBackgroundColor: cyberGreen.withValues(alpha: .25),
                ),
                child: const Text('MARKET BUY'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton(
                onPressed: null,
                style: FilledButton.styleFrom(
                  backgroundColor: cyberPink,
                  disabledBackgroundColor: cyberPink.withValues(alpha: .25),
                ),
                child: const Text('INSTANT SHORT'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        const Text(
          'Zlecenia zablokowane: tryb paper research.',
          style: TextStyle(color: cyberMuted, fontSize: 11),
        ),
        if (manualPositions.containsKey(selected)) ...[
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: closeManualOrder,
            style: OutlinedButton.styleFrom(
              foregroundColor: cyberCyan,
              side: const BorderSide(color: cyberCyan),
            ),
            child: const Text('ZAMKNIJ POZYCJE TESTOWA'),
          ),
        ],
      ],
    ),
  );

  Widget portfolioPanel() {
    final equity = broker['equity'];
    final positions = broker['positions'] as Map? ?? {};
    final top = research?['top_10'] as List? ?? [];
    return card(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'PORTFEL AI • TOP 10',
            style: TextStyle(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 12),
          Text(
            'WARTOŚĆ ${money(equity)} ${isPln ? 'zł' : 'jedn.'}',
            style: const TextStyle(
              color: cyberCyan,
              fontSize: 24,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 12),
          for (final raw in top.take(10))
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 5),
              child: Row(
                children: [
                  Text(
                    '#${raw['rank']}',
                    style: const TextStyle(
                      color: cyberMuted,
                      fontFamily: 'monospace',
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(child: Text(raw['symbol']?.toString() ?? '—')),
                  Text(
                    positions.containsKey(raw['symbol']) ? 'OPEN' : 'WATCH',
                    style: TextStyle(
                      color: positions.containsKey(raw['symbol'])
                          ? cyberGreen
                          : cyberMuted,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  List<Map<String, dynamic>> get rankedAssets {
    final top = research?['top_10'] as List? ?? const [];
    if (top.isNotEmpty) {
      return top
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();
    }
    return assets.keys
        .take(10)
        .toList()
        .asMap()
        .entries
        .map(
          (entry) => <String, dynamic>{
            'rank': entry.key + 1,
            'symbol': entry.value.toString(),
          },
        )
        .toList();
  }

  Widget assetPortfolioPanel() => card(
    Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'PORTFOLIO & ASSETS',
          style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12),
        ),
        const SizedBox(height: 8),
        const Text(
          'TOP 10 MODELU',
          style: TextStyle(color: cyberCyan, fontSize: 10),
        ),
        const Divider(color: cyberLine),
        for (final asset in rankedAssets.take(10))
          InkWell(
            onTap: () {
              setState(() => selected = asset['symbol'].toString());
              refresh();
            },
            child: Container(
              margin: const EdgeInsets.symmetric(vertical: 3),
              padding: const EdgeInsets.symmetric(vertical: 7, horizontal: 6),
              decoration: BoxDecoration(
                color: selected == asset['symbol']
                    ? cyberCyan.withValues(alpha: .10)
                    : Colors.transparent,
                border: Border(
                  left: BorderSide(
                    color: selected == asset['symbol']
                        ? cyberCyan
                        : Colors.transparent,
                    width: 2,
                  ),
                ),
              ),
              child: Row(
                children: [
                  Text(
                    '#${asset['rank']}',
                    style: const TextStyle(color: cyberMuted, fontSize: 10),
                  ),
                  const SizedBox(width: 7),
                  Expanded(
                    child: Text(
                      asset['symbol'].toString(),
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  Text(
                    asset['profit_probability_lower'] is num
                        ? '${((asset['profit_probability_lower'] as num) * 100).toStringAsFixed(0)}%'
                        : 'WATCH',
                    style: TextStyle(
                      color: asset['symbol'] == selected
                          ? cyberGreen
                          : cyberMuted,
                      fontSize: 10,
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    ),
  );

  Widget leveragePanel(BuildContext context) => card(
    Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text(
              'ORDER EXECUTION',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13),
            ),
            const Spacer(),
            badge('PAPER ONLY', cyberGreen),
          ],
        ),
        const Divider(color: cyberLine, height: 25),
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: const Color(0xFF141924),
            border: Border.all(color: cyberLine),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Column(
            children: [
              Row(
                children: [
                  const Text(
                    'DZWIGNIA',
                    style: TextStyle(color: cyberMuted, fontSize: 11),
                  ),
                  const Spacer(),
                  Text(
                    '${leverage}x',
                    style: const TextStyle(
                      color: cyberCyan,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
              Slider(
                value: leverage.toDouble(),
                min: 1,
                max: 100,
                divisions: 99,
                activeColor: cyberCyan,
                inactiveColor: cyberLine,
                onChanged: (value) => setState(() => leverage = value.round()),
              ),
              const Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('1x', style: TextStyle(color: cyberMuted, fontSize: 10)),
                  Text(
                    '50x',
                    style: TextStyle(color: cyberMuted, fontSize: 10),
                  ),
                  Text(
                    '100x MAX',
                    style: TextStyle(color: cyberPink, fontSize: 10),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        const Text(
          'KWOTA (PLN)',
          style: TextStyle(color: cyberMuted, fontSize: 10),
        ),
        const SizedBox(height: 5),
        const _PaperInput('1 000.00', 'PLN'),
        const SizedBox(height: 11),
        const Text(
          'STOP LOSS / TAKE PROFIT',
          style: TextStyle(color: cyberMuted, fontSize: 10),
        ),
        const SizedBox(height: 5),
        const Row(
          children: [
            Expanded(child: _PaperInput('SL: auto', '')),
            SizedBox(width: 7),
            Expanded(child: _PaperInput('TP: auto', '')),
          ],
        ),
        const SizedBox(height: 15),
        const Text(
          'SILA RYNKU (BUY / SELL)',
          style: TextStyle(color: cyberMuted, fontSize: 10),
        ),
        const SizedBox(height: 6),
        Container(
          height: 8,
          decoration: BoxDecoration(
            color: cyberPink,
            borderRadius: BorderRadius.circular(5),
          ),
          child: FractionallySizedBox(
            widthFactor: selectedAsset['recommendation'] == 'OBSERVE_SIGNAL'
                ? .68
                : .45,
            alignment: Alignment.centerLeft,
            child: Container(
              decoration: BoxDecoration(
                color: cyberGreen,
                borderRadius: BorderRadius.circular(5),
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: FilledButton(
                onPressed: () => manualOrder('LONG'),
                style: FilledButton.styleFrom(
                  backgroundColor: cyberGreen,
                  foregroundColor: Colors.black,
                ),
                child: const Text('KUP TESTOWO'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: FilledButton(
                onPressed: () => manualOrder('SHORT'),
                style: FilledButton.styleFrom(
                  backgroundColor: cyberPink,
                  foregroundColor: Colors.white,
                ),
                child: const Text('SHORT TESTOWO'),
              ),
            ),
          ],
        ),
        if (manualPositions.containsKey(selected)) ...[
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: closeManualOrder,
            style: OutlinedButton.styleFrom(
              foregroundColor: cyberCyan,
              side: const BorderSide(color: cyberCyan),
            ),
            child: const Text('ZAMKNIJ POZYCJE TESTOWA'),
          ),
        ],
      ],
    ),
  );

  Widget activityPanel() {
    final decisions = research?['decisions'] as List? ?? const [];
    final trades = broker['trades'] as List? ?? const [];
    final rows = [...trades.reversed.take(5), ...decisions.reversed.take(5)];
    return card(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'AKTYWNOSC AI I HISTORIA',
            style: TextStyle(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          if (rows.isEmpty)
            const Text(
              'Brak zapisanych decyzji lub zamknietych pozycji.',
              style: TextStyle(color: cyberMuted),
            )
          else
            for (final row in rows)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Row(
                  children: [
                    Icon(
                      row['profit'] is num && (row['profit'] as num) < 0
                          ? Icons.south_east
                          : Icons.auto_graph,
                      color: row['profit'] is num && (row['profit'] as num) < 0
                          ? cyberPink
                          : cyberGreen,
                      size: 15,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${row['symbol'] ?? 'AI'}  ${row['reason'] ?? row['exit_reason'] ?? row['action'] ?? 'analiza'}',
                        style: const TextStyle(fontSize: 12),
                      ),
                    ),
                    if (row['profit'] is num)
                      Text(
                        '${(row['profit'] as num) >= 0 ? '+' : ''}${money(row['profit'])} zl',
                        style: TextStyle(
                          color: (row['profit'] as num) >= 0
                              ? cyberGreen
                              : cyberPink,
                          fontSize: 11,
                        ),
                      ),
                  ],
                ),
              ),
        ],
      ),
    );
  }

  Widget desktopRail() => Container(
    width: 54,
    decoration: const BoxDecoration(
      border: Border(right: BorderSide(color: cyberLine)),
    ),
    child: const Column(
      children: [
        SizedBox(height: 24),
        Icon(Icons.bolt, color: cyberGreen),
        SizedBox(height: 35),
        Icon(Icons.account_balance_wallet_outlined, color: cyberCyan),
        SizedBox(height: 28),
        Icon(Icons.bar_chart_outlined, color: cyberMuted),
        SizedBox(height: 28),
        Icon(Icons.psychology_outlined, color: cyberMuted),
        SizedBox(height: 28),
        Icon(Icons.history_outlined, color: cyberMuted),
      ],
    ),
  );

  Widget desktopTopBar(BuildContext context) => Container(
    height: 56,
    padding: const EdgeInsets.symmetric(horizontal: 16),
    decoration: const BoxDecoration(
      color: Color(0xFF0D121C),
      border: Border(bottom: BorderSide(color: cyberLine)),
    ),
    child: Row(
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: const BoxDecoration(
            color: cyberGreen,
            shape: BoxShape.circle,
            boxShadow: [BoxShadow(color: cyberGreen, blurRadius: 10)],
          ),
        ),
        const SizedBox(width: 9),
        const Text(
          'CYBER',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w900,
            letterSpacing: 1,
          ),
        ),
        const Text(
          'PRO',
          style: TextStyle(
            color: cyberGreen,
            fontSize: 17,
            fontWeight: FontWeight.w900,
            letterSpacing: 1,
          ),
        ),
        const Text(
          ' // TRADER',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w900,
            letterSpacing: 1,
          ),
        ),
        const SizedBox(width: 26),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
          decoration: BoxDecoration(
            color: const Color(0xFF171D2A),
            border: Border.all(color: cyberCyan.withValues(alpha: .30)),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(
            '$selected PERP',
            style: const TextStyle(
              color: cyberCyan,
              fontSize: 11,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        const SizedBox(width: 14),
        Text(
          'Mark: ${money(selectedAsset['market_price'])}',
          style: const TextStyle(
            color: cyberGreen,
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
        ),
        const Spacer(),
        badge(
          selectedAsset['recommendation'] == 'OBSERVE_SIGNAL'
              ? 'AI SIGNAL: BULLISH'
              : 'AI SIGNAL: OBSERVE',
          selectedAsset['recommendation'] == 'OBSERVE_SIGNAL'
              ? cyberGreen
              : cyberCyan,
        ),
        const SizedBox(width: 14),
        FilledButton(
          onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Portfel dziala w trybie Paper Trading.'),
            ),
          ),
          style: FilledButton.styleFrom(
            backgroundColor: cyberGreen,
            foregroundColor: Colors.black,
          ),
          child: const Text('CONNECT WALLET'),
        ),
      ],
    ),
  );

  Widget desktopTerminal(BuildContext context) => Scaffold(
    backgroundColor: cyberBg,
    body: SafeArea(
      child: Row(
        children: [
          desktopRail(),
          Expanded(
            child: Column(
              children: [
                desktopTopBar(context),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(
                          width: 248,
                          child: ListView(
                            children: [
                              depthPanel(),
                              const SizedBox(height: 12),
                              assetPortfolioPanel(),
                            ],
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: ListView(
                            children: [
                              selector(),
                              const SizedBox(height: 12),
                              chartPanel(),
                              const SizedBox(height: 12),
                              executionPanel(),
                              const SizedBox(height: 12),
                              activityPanel(),
                            ],
                          ),
                        ),
                        const SizedBox(width: 14),
                        SizedBox(width: 298, child: leveragePanel(context)),
                      ],
                    ),
                  ),
                ),
                Container(
                  height: 30,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: const BoxDecoration(
                    color: Color(0xFF0E121B),
                    border: Border(top: BorderSide(color: cyberLine)),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.circle, color: cyberGreen, size: 8),
                      SizedBox(width: 5),
                      Text(
                        'SYSTEM ONLINE',
                        style: TextStyle(color: cyberGreen, fontSize: 10),
                      ),
                      SizedBox(width: 18),
                      Text(
                        'ENGINE: PAPER-RESEARCH',
                        style: TextStyle(color: cyberCyan, fontSize: 10),
                      ),
                      Spacer(),
                      Text(
                        'PRO-TRADING TERMINAL v2.4',
                        style: TextStyle(color: cyberMuted, fontSize: 10),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 1050;
    if (wide) {
      return desktopTerminal(context);
    }
    final equity = broker['equity'] ?? broker['balance'];
    final pnl = equity is num
        ? equity - ((broker['initial_balance'] as num?) ?? 1000)
        : null;
    return Scaffold(
      backgroundColor: cyberBg,
      body: SafeArea(
        child: Row(
          children: [
            if (wide) desktopRail(),
            Expanded(
              child: ListView(
                padding: EdgeInsets.all(wide ? 24 : 14),
                children: [
                  header(),
                  const SizedBox(height: 18),
                  selector(),
                  if (error != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: Text(
                        error!,
                        style: const TextStyle(color: cyberPink),
                      ),
                    ),
                  const SizedBox(height: 14),
                  LayoutBuilder(
                    builder: (context, box) {
                      final cards = [
                        metric(
                          'Kapitał AI',
                          '${money(equity)} ${isPln ? 'zł' : ''}',
                          Icons.account_balance_wallet_outlined,
                        ),
                        metric(
                          'Wynik',
                          pnl == null
                              ? '—'
                              : '${pnl >= 0 ? '+' : ''}${money(pnl)} zł',
                          Icons.trending_up,
                          color: pnl != null && pnl < 0
                              ? cyberPink
                              : cyberGreen,
                        ),
                        metric(
                          'Otwarte pozycje',
                          '${(broker['positions'] as Map? ?? {}).length}',
                          Icons.layers_outlined,
                        ),
                        metric(
                          'Tryb',
                          'PAPER',
                          Icons.shield_outlined,
                          color: cyberGreen,
                        ),
                      ];
                      return Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: cards
                            .map(
                              (item) => SizedBox(
                                width: math
                                    .max(160.0, (box.maxWidth - 36) / 4)
                                    .toDouble(),
                                child: item,
                              ),
                            )
                            .toList(),
                      );
                    },
                  ),
                  const SizedBox(height: 14),
                  if (wide)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(
                          width: 245,
                          child: Column(
                            children: [
                              assetPortfolioPanel(),
                              const SizedBox(height: 14),
                              leveragePanel(context),
                            ],
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(flex: 6, child: chartPanel()),
                        const SizedBox(width: 14),
                        SizedBox(
                          width: 300,
                          child: Column(
                            children: [
                              depthPanel(),
                              const SizedBox(height: 14),
                              executionPanel(),
                            ],
                          ),
                        ),
                      ],
                    )
                  else ...[
                    chartPanel(),
                    const SizedBox(height: 14),
                    depthPanel(),
                    const SizedBox(height: 14),
                    executionPanel(),
                  ],
                  const SizedBox(height: 14),
                  if (!wide) portfolioPanel(),
                  if (!wide) const SizedBox(height: 14),
                  activityPanel(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PaperInput extends StatelessWidget {
  final String value;
  final String suffix;
  const _PaperInput(this.value, this.suffix);

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 10),
    decoration: BoxDecoration(
      color: const Color(0xFF141924),
      border: Border.all(color: cyberLine),
      borderRadius: BorderRadius.circular(4),
    ),
    child: Row(
      children: [
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontSize: 11, color: Color(0xFFE7EDF7)),
          ),
        ),
        if (suffix.isNotEmpty)
          Text(suffix, style: const TextStyle(fontSize: 10, color: cyberMuted)),
      ],
    ),
  );
}

class _IndicatorChip extends StatelessWidget {
  final String text;
  const _IndicatorChip(this.text);
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    decoration: BoxDecoration(
      border: Border.all(color: cyberLine),
      borderRadius: BorderRadius.circular(3),
    ),
    child: Text(text, style: const TextStyle(color: cyberMuted, fontSize: 10)),
  );
}

class _DepthRow extends StatelessWidget {
  final String label;
  final Color color;
  const _DepthRow(this.label, this.color);
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        label,
        style: TextStyle(color: color, fontSize: 11, letterSpacing: 1),
      ),
      const SizedBox(height: 6),
      Container(
        height: 6,
        width: double.infinity,
        color: color.withValues(alpha: .25),
      ),
    ],
  );
}

double? _macd(List<double> closes) {
  if (closes.length < 26) {
    return null;
  }
  return _ema(closes, 12) - _ema(closes, 26);
}

double _ema(List<double> values, int period) {
  final multiplier = 2 / (period + 1);
  var value = values.take(period).reduce((sum, item) => sum + item) / period;
  for (final item in values.skip(period)) {
    value = (item - value) * multiplier + value;
  }
  return value;
}

List<double>? _bollinger(List<double> closes) {
  if (closes.length < 20) {
    return null;
  }
  final window = closes.sublist(closes.length - 20);
  final middle = window.reduce((sum, item) => sum + item) / window.length;
  final variance =
      window
          .map((item) => math.pow(item - middle, 2))
          .reduce((sum, item) => sum + item) /
      window.length;
  final deviation = math.sqrt(variance);
  return [middle - 2 * deviation, middle, middle + 2 * deviation];
}

double? _rsi(List<double> closes) {
  if (closes.length < 15) {
    return null;
  }
  var gains = 0.0, losses = 0.0;
  for (var i = closes.length - 14; i < closes.length; i++) {
    final change = closes[i] - closes[i - 1];
    if (change >= 0)
      gains += change;
    else
      losses -= change;
  }
  if (losses == 0) {
    return 100;
  }
  final rs = gains / losses;
  return 100 - (100 / (1 + rs));
}

class CandlePainter extends CustomPainter {
  final List<Map<String, dynamic>> points;
  final bool signal;
  CandlePainter(this.points, {required this.signal});
  @override
  void paint(Canvas canvas, Size size) {
    if (points.isEmpty) {
      return;
    }
    final lows = points.map((p) => (p['low'] as num).toDouble()).toList();
    final highs = points.map((p) => (p['high'] as num).toDouble()).toList();
    final minY = lows.reduce(math.min).toDouble();
    final maxY = highs.reduce(math.max).toDouble();
    final span = math.max(maxY - minY, maxY.abs() * .001).toDouble();
    final plotHeight = size.height * .78;
    final grid = Paint()
      ..color = cyberLine
      ..strokeWidth = 1;
    for (var i = 0; i < 5; i++) {
      final y = plotHeight * i / 4;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }
    final width = size.width / points.length;
    double y(double value) => plotHeight * (1 - (value - minY) / span);
    for (var i = 0; i < points.length; i++) {
      final p = points[i];
      final open = (p['open'] as num).toDouble(),
          close = (p['close'] as num).toDouble();
      final high = (p['high'] as num).toDouble(),
          low = (p['low'] as num).toDouble();
      final color = close >= open ? cyberGreen : cyberPink;
      final paint = Paint()..color = color;
      final x = i * width + width / 2;
      canvas.drawLine(
        Offset(x, y(high)),
        Offset(x, y(low)),
        paint..strokeWidth = 1,
      );
      final top = math.min(y(open), y(close)).toDouble();
      final height = math.max(1.0, (y(open) - y(close)).abs()).toDouble();
      canvas.drawRect(
        Rect.fromLTWH(
          x - width * .28,
          top,
          math.max(1.0, width * .56).toDouble(),
          height,
        ),
        paint,
      );
      final volume = ((p['volume'] as num?)?.toDouble() ?? 0);
      final maxVolume = points
          .map((q) => ((q['volume'] as num?)?.toDouble() ?? 0))
          .reduce(math.max)
          .toDouble();
      final volumeHeight = maxVolume == 0
          ? 0.0
          : volume / maxVolume * size.height * .16;
      canvas.drawRect(
        Rect.fromLTWH(
          x - width * .28,
          size.height - volumeHeight,
          math.max(1.0, width * .56).toDouble(),
          volumeHeight,
        ),
        Paint()..color = color.withValues(alpha: .35),
      );
    }
    if (signal) {
      canvas.drawCircle(
        Offset(
          size.width - width / 2,
          y((points.last['close'] as num).toDouble()),
        ),
        5,
        Paint()..color = cyberCyan,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CandlePainter oldDelegate) =>
      oldDelegate.points != points || oldDelegate.signal != signal;
}
