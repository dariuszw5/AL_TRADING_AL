import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  final String message;
  final int? statusCode;

  const ApiException(this.message, [this.statusCode]);

  @override
  String toString() =>
      statusCode == null ? message : 'HTTP $statusCode: $message';
}

class AlTradingApi {
  AlTradingApi({String? baseUrl, http.Client? client})
    : baseUrl = (baseUrl ?? _configuredBaseUrl()).replaceAll(RegExp(r'/$'), ''),
      _client = client ?? http.Client();

  static String _configuredBaseUrl() {
    const legacy = String.fromEnvironment(
      'AL_TRADING_API_BASE_URL',
      defaultValue: '',
    );
    if (legacy.isNotEmpty) {
      return legacy;
    }
    return const String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://127.0.0.1:8000',
    );
  }

  final String baseUrl;
  final http.Client _client;

  Future<dynamic> _get(String path) async {
    final uri = Uri.parse('$baseUrl$path');

    try {
      final response = await _client
          .get(uri, headers: const {'Accept': 'application/json'})
          .timeout(const Duration(seconds: 8));

      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw ApiException(
          response.body.isEmpty ? 'Błąd odpowiedzi API' : response.body,
          response.statusCode,
        );
      }

      if (response.body.isEmpty) {
        return null;
      }

      return jsonDecode(utf8.decode(response.bodyBytes));
    } on ApiException {
      rethrow;
    } catch (error) {
      throw ApiException('Brak połączenia z $uri: $error');
    }
  }

  Future<Map<String, dynamic>> root() async =>
      Map<String, dynamic>.from(await _get('/') as Map);

  Future<Map<String, dynamic>> health(String symbol) async =>
      Map<String, dynamic>.from(
        await _get('/api/health?symbol=${Uri.encodeQueryComponent(symbol)}')
            as Map,
      );

  Future<Map<String, dynamic>> status(String symbol) async =>
      Map<String, dynamic>.from(
        await _get('/api/status?symbol=${Uri.encodeQueryComponent(symbol)}')
            as Map,
      );

  Future<List<Map<String, dynamic>>> assets() async {
    final data = await _get('/api/assets') as List<dynamic>;
    return data.map((item) => Map<String, dynamic>.from(item as Map)).toList();
  }

  Future<List<Map<String, dynamic>>> trades(String symbol) async {
    final data = await _get(
      '/api/trades?symbol=${Uri.encodeQueryComponent(symbol)}',
    ) as List<dynamic>;

    return data.map((item) => Map<String, dynamic>.from(item as Map)).toList();
  }

  Future<Map<String, dynamic>> equity(String symbol) async =>
      Map<String, dynamic>.from(
        await _get('/api/equity?symbol=${Uri.encodeQueryComponent(symbol)}')
            as Map,
      );

  Future<Map<String, dynamic>> market(String symbol) async =>
      Map<String, dynamic>.from(
        await _get('/api/market?symbol=${Uri.encodeQueryComponent(symbol)}')
            as Map,
      );

  Future<List<Map<String, dynamic>>> daily() async {
    final data = await _get('/api/daily') as List<dynamic>;
    return data.map((item) => Map<String, dynamic>.from(item as Map)).toList();
  }

  Future<Map<String, dynamic>> aiStatus() async =>
      Map<String, dynamic>.from(await _get('/api/ai') as Map);

  Future<Map<String, dynamic>> userPortfolio() async =>
      Map<String, dynamic>.from(await _get('/api/user-portfolio') as Map);

  void close() => _client.close();
}
