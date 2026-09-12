import 'dart:convert';
import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

import '../storage/token_storage.dart';
import 'api_exception.dart';

/// Thin shared HTTP layer every feature repository goes through — one
/// place that knows the backend's base URL, attaches the bearer token,
/// and turns FastAPI's `{"detail": "..."}` error bodies into
/// [ApiException]. Feature repositories (AuthRepository, CourseRepository)
/// stay focused on their own endpoints and response shapes.
class ApiClient {
  final String baseUrl;
  final TokenStorage _tokenStorage;

  ApiClient({required TokenStorage tokenStorage, String? baseUrl})
    : _tokenStorage = tokenStorage,
      baseUrl = baseUrl ?? _defaultBaseUrl();

  /// The backend's CORS allowlist is currently just localhost:5173 (see
  /// backend/app/main.py) — a web build of this app will need that origin
  /// added there. Native builds aren't affected by CORS.
  static String _defaultBaseUrl() {
    const fromEnv = String.fromEnvironment('API_BASE');
    if (fromEnv.isNotEmpty) return fromEnv;
    if (!kIsWeb && Platform.isAndroid) {
      // 10.0.2.2 is the Android emulator's alias for the host machine.
      return 'http://10.0.2.2:8000/api';
    }
    return 'http://localhost:8000/api';
  }

  Future<T> request<T>(
    String path, {
    String method = 'GET',
    Map<String, dynamic>? body,
    required T Function(dynamic json) parse,
  }) async {
    final uri = Uri.parse('$baseUrl$path');
    final token = await _tokenStorage.readToken();
    final headers = {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };

    late http.Response res;
    switch (method) {
      case 'PATCH':
        res = await http.patch(uri, headers: headers, body: jsonEncode(body));
      case 'POST':
        res = await http.post(uri, headers: headers, body: body == null ? null : jsonEncode(body));
      default:
        res = await http.get(uri, headers: headers);
    }

    if (res.statusCode < 200 || res.statusCode >= 300) {
      String message = res.reasonPhrase ?? 'Request failed';
      try {
        final decoded = jsonDecode(res.body) as Map<String, dynamic>;
        if (decoded['detail'] is String) message = decoded['detail'] as String;
      } catch (_) {
        // Body wasn't JSON — fall back to the status reason phrase.
      }
      throw ApiException(message, res.statusCode);
    }
    if (res.statusCode == 204 || res.body.isEmpty) {
      return parse(null);
    }
    return parse(jsonDecode(res.body));
  }
}

final apiClientProvider = Provider<ApiClient>(
  (ref) => ApiClient(tokenStorage: ref.watch(tokenStorageProvider)),
);
