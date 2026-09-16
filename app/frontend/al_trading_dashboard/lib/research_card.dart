// Read-only mapping of the current virtual broker response to dashboard cards.
Map<String, dynamic> researchCard(Map data, String symbol) {
  final asset = (data['assets'] as Map? ?? {})[symbol] as Map? ?? {};
  final broker = data['virtual_broker'] as Map? ?? {};
  final position = (broker['positions'] as Map? ?? {})[symbol] as Map?;
  final isPln = broker['currency'] == 'PLN';
  final price = (asset[isPln ? 'market_price_pln' : 'market_price'] as num?)
      ?.toDouble();
  final trades = (broker['trades'] as List? ?? []).where(
    (t) => t['symbol'] == symbol,
  );
  final realized = isPln
      ? ((broker['realized_by_symbol'] as Map? ?? {})[symbol] as num? ?? 0)
            .toDouble()
      : trades.fold<double>(
          0,
          (sum, t) => sum + (t['profit'] as num).toDouble(),
        );
  final unrealized = isPln
      ? (position?['unrealized_pln'] as num? ?? 0)
      : position == null || price == null
      ? 0.0
      : (position['quantity'] as num) *
            (price * (1 - 0.0005) * (1 - 0.0004) -
                (position['entry'] as num) * (1 + 0.0004));
  return {
    'available': price != null,
    'account': {
      'market_price': price,
      'net_profit': realized + unrealized,
      'position': position == null ? 'FLAT' : 'LONG',
    },
    'cycle': data['last_cycle'],
    'stale': data['stale'] == true,
  };
}
