import 'package:flutter/material.dart';

import 'pro_dashboard.dart';

/// One autonomous multi-market AI account is the source of portfolio truth.
/// The former per-symbol legacy paper-live dashboard is deliberately not
/// exposed as an alternative account in the production application.
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
    if (low < minLow) minLow = low;
    if (high > maxHigh) maxHigh = high;
  }

  final range = maxHigh - minLow;
  final padding = range > 0 ? range * 0.08 : 10.0;
  return ChartAxisBounds(minY: minLow - padding, maxY: maxHigh + padding);
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
      home: const ProDashboard(baseUrl: apiBaseUrl),
    );
  }
}
