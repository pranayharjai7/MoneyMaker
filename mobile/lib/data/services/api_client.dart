import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/config/app_config.dart';

class ApiClient {
  const ApiClient({
    required AppConfig config,
    required SupabaseClient supabase,
    http.Client? httpClient,
  })  : _config = config,
        _supabase = supabase,
        _httpClient = httpClient;

  final AppConfig _config;
  final SupabaseClient _supabase;
  final http.Client? _httpClient;

  http.Client get _client => _httpClient ?? http.Client();

  Future<List<Map<String, dynamic>>> getList(String path) async {
    final response = await _client.get(_uri(path), headers: await _headers());
    _throwIfNeeded(response);
    final decoded = jsonDecode(response.body);
    if (decoded is! List) {
      return const [];
    }
    return decoded
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList(growable: false);
  }

  Future<Map<String, dynamic>> getMap(String path) async {
    final response = await _client.get(_uri(path), headers: await _headers());
    _throwIfNeeded(response);
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> postMap(
    String path, {
    required Map<String, dynamic> body,
  }) async {
    final response = await _client.post(
      _uri(path),
      headers: await _headers(),
      body: jsonEncode(body),
    );
    _throwIfNeeded(response);
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<List<Map<String, dynamic>>> postList(
    String path, {
    required Map<String, dynamic> body,
  }) async {
    final response = await _client.post(
      _uri(path),
      headers: await _headers(),
      body: jsonEncode(body),
    );
    _throwIfNeeded(response);
    final decoded = jsonDecode(response.body);
    if (decoded is! List) {
      return const [];
    }
    return decoded
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList(growable: false);
  }

  Uri _uri(String path) {
    final normalizedBase = _config.apiBaseUrl.endsWith('/')
        ? _config.apiBaseUrl.substring(0, _config.apiBaseUrl.length - 1)
        : _config.apiBaseUrl;
    final normalizedPath = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$normalizedBase$normalizedPath');
  }

  Future<Map<String, String>> _headers() async {
    final token = _supabase.auth.currentSession?.accessToken;
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  void _throwIfNeeded(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return;
    }
    throw ApiException(
      statusCode: response.statusCode,
      message: response.body,
    );
  }
}

class ApiException implements Exception {
  const ApiException({
    required this.statusCode,
    required this.message,
  });

  final int statusCode;
  final String message;

  @override
  String toString() => 'ApiException($statusCode): $message';
}
