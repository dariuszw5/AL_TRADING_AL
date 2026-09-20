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

class _ProDashboardState extends State<ProDashboard>
    with SingleTickerProviderStateMixin {
  List<Map<String, dynamic>> assets = [];
  Map<String, dynamic>? research;
  Map<String, dynamic>? ai;
  Map<String, dynamic>? userPortfolio;
  String? failure;
  DateTime? received;
  Timer? timer;
  late final AnimationController activityPulse;
  bool busy = false;
  Future<void>? refreshInFlight;
  int page = 0;
  String query = '';

  final labels = const [
    'Portfel',
    'Rynki',
    'Research TOP 10',
    'Aktywność AI',
    'Wydarzenia',
    'Historia',
  ];

  final icons = const [
    Icons.account_balance_wallet,
    Icons.candlestick_chart,
    Icons.travel_explore,
    Icons.psychology,
    Icons.newspaper,
    Icons.history,
  ];

  @override
  void initState() {
    super.initState();
    activityPulse = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
      lowerBound: 0.0,
      upperBound: 1.0,
    )..repeat(reverse: true);
    refresh();
    timer = Timer.periodic(const Duration(seconds: 5), (_) => refresh());
  }

  @override
  void dispose() {
    timer?.cancel();
    activityPulse.dispose();
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

  Future<void> refresh() {
    final active = refreshInFlight;
    if (active != null) return active;

    late Future<void> future;
    future = _refreshOnce().whenComplete(() {
      if (identical(refreshInFlight, future)) {
        refreshInFlight = null;
      }
    });
    refreshInFlight = future;
    return future;
  }

  Future<void> manualRefresh() async {
    final active = refreshInFlight;
    if (active != null) {
      await active;
    }
    if (!mounted) return;
    await refresh();
  }

  Future<void> _refreshOnce() async {
    busy = true;
    if (mounted) setState(() {});

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
      if (mounted) setState(() {});
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
    child: LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 560 && detail != null;

        final titleWidget = Text(
          title,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        );

        if (compact) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              titleWidget,
              const SizedBox(height: 5),
              Text(
                detail,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: muted,
                  fontSize: 12,
                  height: 1.35,
                ),
              ),
            ],
          );
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: titleWidget),
            if (detail != null) ...[
              const SizedBox(width: 14),
              Flexible(
                child: Text(
                  detail,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.right,
                  style: const TextStyle(
                    color: muted,
                    fontSize: 12,
                    height: 1.35,
                  ),
                ),
              ),
            ],
          ],
        );
      },
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

  Widget pnlNowCard({
    required double funded,
    required double equity,
    required double realized,
    required double unrealized,
  }) {
    final delta = equity - funded;
    final pct = funded > 0 ? delta / funded * 100 : 0.0;
    final positive = delta > 0.005;
    final negative = delta < -0.005;
    final tone = positive
        ? mint
        : negative
        ? Colors.redAccent
        : muted;
    final arrow = positive
        ? Icons.trending_up_rounded
        : negative
        ? Icons.trending_down_rounded
        : Icons.trending_flat_rounded;

    return box(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(arrow, color: tone, size: 23),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 8,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: tone.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  '${pct >= 0 ? '+' : ''}${pct.toStringAsFixed(2)}%',
                  style: TextStyle(
                    color: tone,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          const Text(
            'Zysk / strata teraz',
            style: TextStyle(color: muted),
          ),
          const SizedBox(height: 8),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(
              '${signed(delta)} PLN',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w600,
                color: tone,
              ),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Otwarty ${signed(unrealized)} • zrealizowany ${signed(realized)}',
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: muted,
              fontSize: 11,
              height: 1.35,
            ),
          ),
        ],
      ),
    );
  }

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
    final funded =
        (aiState['funded_capital'] as num?)?.toDouble() ?? initial;
    final realized = (aiState['realized_pnl'] as num?)?.toDouble() ?? 0.0;
    final unrealized = (aiState['unrealized_pnl'] as num?)?.toDouble() ?? 0.0;
    final positions = asMap(aiState['positions']);
    final pending = asList(aiState['pending'])
        .whereType<Map>()
        .map((row) => Map<String, dynamic>.from(row))
        .toList();
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
      pnlNowCard(
        funded: funded,
        equity: equity,
        realized: realized,
        unrealized: unrealized,
      ),
      positionStatusCard(
        title: 'Pozycje otwarte',
        value: positions.isEmpty ? 'BRAK' : '${positions.length} OTWARTE',
        icon: Icons.play_circle_outline_rounded,
        color: mint,
        active: positions.isNotEmpty,
        status: positions.isEmpty ? 'BRAK AKCJI' : 'AKTYWNE',
        detail: positions.isEmpty
            ? 'Brak aktywnych pozycji'
            : positions.entries.take(4).map((entry) {
                final p = asMap(entry.value);
                final pnl =
                    (p['unrealized_pnl'] as num?)?.toDouble() ?? 0.0;
                return '${entry.key} ${p['side'] ?? ''} ${signed(pnl)} PLN';
              }).join(' • '),
      ),
      positionStatusCard(
        title: 'Pozycje oczekujące',
        value: pending.isEmpty ? 'BRAK' : '${pending.length} OCZEKUJE',
        icon: Icons.hourglass_top_rounded,
        color: cyan,
        active: pending.isNotEmpty,
        status: pending.isEmpty ? 'BRAK AKCJI' : 'POTWIERDZANIE',
        detail: pending.isEmpty
            ? 'Brak sygnałów oczekujących na potwierdzenie'
            : pending.take(4).map((row) {
                return '${row['symbol'] ?? '—'} ${row['side'] ?? ''} • weryfikacja sygnału';
              }).join(' • '),
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

  String? assetLogoUrl(String symbol) {
    final upper = symbol.toUpperCase();

    if (upper.endsWith('USDT') && upper.length > 4) {
      final base = upper.substring(0, upper.length - 4).toLowerCase();
      return 'https://assets.coincap.io/assets/icons/$base@2x.png';
    }

    const companyDomains = <String, String>{
      'AAPL': 'apple.com',
      'MSFT': 'microsoft.com',
      'NVDA': 'nvidia.com',
      'AMZN': 'amazon.com',
      'META': 'meta.com',
      'GOOGL': 'google.com',
      'TSLA': 'tesla.com',
      'JPM': 'jpmorganchase.com',
      'XOM': 'exxonmobil.com',
      'SPY': 'ssga.com',
      'QQQ': 'invesco.com',
      'IWM': 'ishares.com',
      'DIA': 'ssga.com',
      'XLK': 'ssga.com',
      'XLF': 'ssga.com',
    };

    final domain = companyDomains[upper];
    if (domain != null) {
      return 'https://www.google.com/s2/favicons?domain=$domain&sz=128';
    }

    return null;
  }

  Widget assetLogo(String symbol, {double size = 28}) {
    final upper = symbol.toUpperCase();
    final url = assetLogoUrl(upper);

    Widget fallback() {
      if (upper == 'EURUSD') {
        return const Text('🇪🇺', style: TextStyle(fontSize: 17));
      }
      if (upper == 'GBPUSD') {
        return const Text('🇬🇧', style: TextStyle(fontSize: 17));
      }
      if (upper == 'USDJPY') {
        return const Text('🇯🇵', style: TextStyle(fontSize: 17));
      }
      if (upper == 'AUDUSD') {
        return const Text('🇦🇺', style: TextStyle(fontSize: 17));
      }
      if (upper == 'USDCAD') {
        return const Text('🇨🇦', style: TextStyle(fontSize: 17));
      }
      if (upper == 'USDCHF') {
        return const Text('🇨🇭', style: TextStyle(fontSize: 17));
      }
      if (upper == 'NZDUSD') {
        return const Text('🇳🇿', style: TextStyle(fontSize: 17));
      }

      final icon = upper.contains('GOLD') || upper.contains('SILVER')
          ? Icons.diamond_outlined
          : upper.contains('WTI') ||
                upper.contains('BRENT') ||
                upper.contains('NATGAS')
          ? Icons.local_gas_station_outlined
          : upper.contains('COPPER')
          ? Icons.hardware_outlined
          : upper.contains('INDEX') ||
                upper.contains('SP500') ||
                upper.contains('NASDAQ') ||
                upper.contains('DOW') ||
                upper.contains('RUSSELL') ||
                upper.contains('VIX')
          ? Icons.show_chart_rounded
          : Icons.currency_exchange_rounded;

      return Icon(icon, size: size * 0.62, color: cyan);
    }

    return Container(
      width: size,
      height: size,
      padding: EdgeInsets.all(size * 0.14),
      decoration: BoxDecoration(
        color: const Color(0xFFF4F7F9),
        shape: BoxShape.circle,
        border: Border.all(
          color: const Color(0xFF355267),
          width: 0.8,
        ),
      ),
      child: url == null
          ? Center(child: fallback())
          : ClipOval(
              child: Image.network(
                url,
                width: size,
                height: size,
                fit: BoxFit.contain,
                filterQuality: FilterQuality.high,
                errorBuilder: (_, _, _) => Center(child: fallback()),
              ),
            ),
    );
  }

  Widget activityPulseDot(Color color, {required bool active}) {
    if (!active) {
      return Container(
        width: 8,
        height: 8,
        decoration: const BoxDecoration(
          color: muted,
          shape: BoxShape.circle,
        ),
      );
    }

    return AnimatedBuilder(
      animation: activityPulse,
      builder: (context, child) {
        final scale = 0.82 + activityPulse.value * 0.30;
        final opacity = 0.55 + activityPulse.value * 0.45;
        return Transform.scale(
          scale: scale,
          child: Opacity(
            opacity: opacity,
            child: Container(
              width: 9,
              height: 9,
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: color.withValues(alpha: 0.32),
                    blurRadius: 8,
                    spreadRadius: 2,
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget positionStatusCard({
    required String title,
    required String value,
    required IconData icon,
    required Color color,
    required bool active,
    required String status,
    required String detail,
  }) {
    return box(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: active ? color : cyan, size: 23),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 8,
                  vertical: 5,
                ),
                decoration: BoxDecoration(
                  color: (active ? color : muted).withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(
                    color: (active ? color : muted).withValues(alpha: 0.22),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    activityPulseDot(color, active: active),
                    const SizedBox(width: 6),
                    Text(
                      status,
                      style: TextStyle(
                        color: active ? color : muted,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(title, style: const TextStyle(color: muted)),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w600,
              color: active ? color : muted,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            detail,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: muted,
              fontSize: 11,
              height: 1.35,
            ),
          ),
        ],
      ),
    );
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
            const SizedBox(width: 8),
            Flexible(
              child: FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerRight,
                child: Text(
                  '${number(value)} PLN • ${pct.toStringAsFixed(1)}%',
                  style: const TextStyle(fontSize: 12),
                ),
              ),
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
          LayoutBuilder(
            builder: (context, constraints) {
              final compact = constraints.maxWidth < 500;

              final chart = SizedBox(
                width: compact ? 150 : 170,
                height: compact ? 150 : 170,
                child: CustomPaint(
                  painter: FundsDonutPainter(
                    values: values,
                    colors: colors,
                  ),
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        FittedBox(
                          fit: BoxFit.scaleDown,
                          child: Text(
                            '${number(total)} PLN',
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w700,
                            ),
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
              );

              final details = Column(
                children: [
                  for (int i = 0; i < values.length; i++) legendRow(i),
                  const Divider(color: Color(0xFF294152)),
                  _miniMetric('Wpłacono do AI', funded),
                  _miniMetric('Zysk przelany', swept),
                  _miniMetric('Strata AI', loss),
                ],
              );

              if (compact) {
                return Column(
                  children: [
                    Center(child: chart),
                    const SizedBox(height: 18),
                    details,
                  ],
                );
              }

              return Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  chart,
                  const SizedBox(width: 20),
                  Expanded(child: details),
                ],
              );
            },
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
    final pendingSymbols = asList(ai?['pending'])
        .whereType<Map>()
        .map((row) => row['symbol']?.toString())
        .whereType<String>()
        .toSet();

    final rows = assets.where((asset) => asset['market_price'] is num).toList()
      ..sort((a, b) {
        final aSymbol = a['symbol']?.toString() ?? '';
        final bSymbol = b['symbol']?.toString() ?? '';
        final aOpen = (a['position']?.toString() ?? 'FLAT') != 'FLAT';
        final bOpen = (b['position']?.toString() ?? 'FLAT') != 'FLAT';
        final aPending = pendingSymbols.contains(aSymbol);
        final bPending = pendingSymbols.contains(bSymbol);

        final aPriority = aOpen ? 0 : aPending ? 1 : 2;
        final bPriority = bOpen ? 0 : bPending ? 1 : 2;
        if (aPriority != bPriority) return aPriority.compareTo(bPriority);

        final ar = opportunityRank(aSymbol) ?? 9999;
        final br = opportunityRank(bSymbol) ?? 9999;
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
                    final isOpen = position != 'FLAT';
                    final isPending = pendingSymbols.contains(symbol);
                    final accent = isOpen
                        ? mint
                        : isPending
                        ? Colors.amberAccent
                        : const Color(0xFF294152);
                    final tileColor = isOpen
                        ? mint.withValues(alpha: 0.08)
                        : isPending
                        ? Colors.amberAccent.withValues(alpha: 0.07)
                        : const Color(0xFF102534);
                    final digits =
                        price != null && price.abs() < 10 ? 5 : 2;
                    return ConstrainedBox(
                      constraints: const BoxConstraints(
                        minWidth: 132,
                        maxWidth: 190,
                      ),
                      child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: tileColor,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: accent,
                          width: isOpen || isPending ? 1.35 : 1.0,
                        ),
                        boxShadow: isOpen || isPending
                            ? [
                                BoxShadow(
                                  color: accent.withValues(alpha: 0.08),
                                  blurRadius: 10,
                                  spreadRadius: 1,
                                ),
                              ]
                            : null,
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          assetLogo(symbol, size: 28),
                          const SizedBox(width: 8),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    symbol,
                                    style: const TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  if (isOpen || isPending) ...[
                                    const SizedBox(width: 5),
                                    Container(
                                      width: 6,
                                      height: 6,
                                      decoration: BoxDecoration(
                                        color: accent,
                                        shape: BoxShape.circle,
                                      ),
                                    ),
                                  ],
                                ],
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
                        assetLogo(symbol, size: 34),
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
            for (final raw in decisions.reversed.take(30))
              if (raw is Map)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.bolt, color: cyan, size: 20),
                  title: Text(
                    '${raw['symbol'] ?? 'Gotówka'} • ${raw['action'] ?? 'DECISION'}',
                  ),
                  subtitle: Text(raw['reason']?.toString() ?? ''),
                ),
          if (errors.values.any((value) => value != null)) ...[
            const Divider(color: Color(0xFF294152)),
            const SizedBox(height: 10),
            const Text(
              'Problemy z danymi',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
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

  Widget macroEvents() {
    final macro = asList(research?['macro_events']);
    return box(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          heading(
            'Ostatnie wydarzenia',
            'Makro i informacje wykorzystywane przez warstwę research',
          ),
          const Row(
            children: [
              Icon(Icons.public, color: mint, size: 30),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Oddzielny widok wydarzeń, bez zaśmiecania głównego ekranu portfela.',
                  style: TextStyle(color: muted),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          if (macro.isEmpty)
            const Text(
              'Brak zapisanych wydarzeń.',
              style: TextStyle(color: muted),
            )
          else
            for (final raw in macro.reversed.take(30))
              if (raw is Map)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.public, color: mint, size: 20),
                  title: Text(
                    raw['title']?.toString() ?? 'Wydarzenie makro',
                  ),
                  subtitle: Text(
                    [
                      if (raw['source'] != null) raw['source'].toString(),
                      if (raw['published_at'] != null)
                        raw['published_at'].toString(),
                    ].join(' • '),
                  ),
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

  Future<void> openMobileMoreMenu() async {
    final selected = await showModalBottomSheet<int>(
      context: context,
      backgroundColor: panel,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.newspaper, color: cyan),
                title: const Text('Wydarzenia'),
                subtitle: const Text(
                  'Makro i informacje z warstwy research',
                  style: TextStyle(color: muted, fontSize: 12),
                ),
                onTap: () => Navigator.pop(context, 4),
              ),
              ListTile(
                leading: const Icon(Icons.history, color: cyan),
                title: const Text('Historia'),
                subtitle: const Text(
                  'Zamknięte transakcje AI',
                  style: TextStyle(color: muted, fontSize: 12),
                ),
                onTap: () => Navigator.pop(context, 5),
              ),
              if (widget.legacyBuilder != null)
                ListTile(
                  leading: const Icon(
                    Icons.analytics_outlined,
                    color: cyan,
                  ),
                  title: const Text('Szczegóły rynku'),
                  subtitle: const Text(
                    'Pełny techniczny widok wybranego instrumentu',
                    style: TextStyle(color: muted, fontSize: 12),
                  ),
                  onTap: () {
                    Navigator.pop(context);
                    openLegacy();
                  },
                ),
            ],
          ),
        ),
      ),
    );

    if (selected != null && mounted) {
      setState(() => page = selected);
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.sizeOf(context).width;
    final wide = screenWidth >= 1180;
    final roomy = screenWidth >= 1500;
    final researchData = research;

    return Scaffold(
      backgroundColor: ink,
      bottomNavigationBar: wide
          ? null
          : NavigationBar(
              selectedIndex: page <= 3 ? page : 4,
              backgroundColor: panel,
              onDestinationSelected: (value) {
                if (value == 4) {
                  openMobileMoreMenu();
                  return;
                }
                setState(() => page = value);
              },
              destinations: const [
                NavigationDestination(
                  icon: Icon(Icons.account_balance_wallet),
                  label: 'Portfel',
                ),
                NavigationDestination(
                  icon: Icon(Icons.candlestick_chart),
                  label: 'Rynki',
                ),
                NavigationDestination(
                  icon: Icon(Icons.travel_explore),
                  label: 'TOP 10',
                ),
                NavigationDestination(
                  icon: Icon(Icons.psychology),
                  label: 'AI',
                ),
                NavigationDestination(
                  icon: Icon(Icons.more_horiz_rounded),
                  label: 'Więcej',
                ),
              ],
            ),
      body: SafeArea(
        child: Row(
          children: [
            if (wide)
              Container(
                width: roomy ? 205 : 184,
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
                          leading: AnimatedContainer(
                            duration: const Duration(milliseconds: 180),
                            width: 34,
                            height: 34,
                            decoration: BoxDecoration(
                              color: page == i
                                  ? cyan.withValues(alpha: 0.14)
                                  : const Color(0xFF142B3D),
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(
                                color: page == i
                                    ? cyan.withValues(alpha: 0.45)
                                    : const Color(0xFF294152),
                              ),
                            ),
                            child: Icon(
                              icons[i],
                              size: 19,
                              color: page == i ? cyan : muted,
                            ),
                          ),
                          title: Text(
                            labels[i],
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: roomy ? 13 : 12,
                            ),
                          ),
                          onTap: () => setState(() => page = i),
                        ),
                      ),
                    if (widget.legacyBuilder != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: OutlinedButton.icon(
                          onPressed: openLegacy,
                          icon: const Icon(Icons.analytics_outlined, size: 18),
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
                  padding: EdgeInsets.all(
                    screenWidth >= 1500
                        ? 28
                        : screenWidth >= 900
                        ? 22
                        : 14,
                  ),
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
                        Tooltip(
                          message: stale
                              ? 'Status danych: STALE'
                              : 'Status danych: LIVE',
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 9,
                              vertical: 6,
                            ),
                            decoration: BoxDecoration(
                              color: (stale ? Colors.amber : mint)
                                  .withValues(alpha: 0.10),
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(
                                color: (stale ? Colors.amber : mint)
                                    .withValues(alpha: 0.35),
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  stale
                                      ? Icons.cloud_off_rounded
                                      : Icons.cloud_done_rounded,
                                  size: 18,
                                  color: stale ? Colors.amber : mint,
                                ),
                                const SizedBox(width: 6),
                                Text(
                                  stale ? 'STALE' : 'LIVE',
                                  style: TextStyle(
                                    color: stale ? Colors.amber : mint,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: 0.5,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        IconButton(
                          tooltip: busy
                              ? 'Odświeżanie danych…'
                              : 'Odśwież teraz',
                          onPressed: manualRefresh,
                          icon: busy
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: cyan,
                                  ),
                                )
                              : const Icon(
                                  Icons.refresh_rounded,
                                  color: cyan,
                                ),
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
                      if (roomy)
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              flex: 7,
                              child: equityChart(),
                            ),
                            const SizedBox(width: 20),
                            Expanded(
                              flex: 5,
                              child: Column(
                                children: [
                                  fundsDonut(),
                                  const SizedBox(height: 20),
                                  portfolioActions(),
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
                      ],
                    ],
                    if (page == 1) marketTable(all: true),
                    if (page == 2)
                      ResearchPanel(data: researchData, error: failure),
                    if (page == 3) activity(),
                    if (page == 4) macroEvents(),
                    if (page == 5) history(),
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
