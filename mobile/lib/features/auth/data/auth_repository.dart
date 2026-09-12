import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/app_user.dart';

class AuthSession {
  final String token;
  final AppUser user;

  const AuthSession({required this.token, required this.user});

  factory AuthSession.fromJson(Map<String, dynamic> json) =>
      AuthSession(token: json['access_token'] as String, user: AppUser.fromJson(json['user'] as Map<String, dynamic>));
}

/// Mirrors backend/app/auth/routes.py — POST /auth/signup, POST
/// /auth/login, GET /auth/me. Doesn't touch TokenStorage itself; that's
/// AuthController's job, so this stays a pure "talk to the backend" layer.
class AuthRepository {
  final ApiClient _client;

  AuthRepository(this._client);

  Future<AuthSession> signup({required String email, required String password, required String name}) => _client
      .request(
        '/auth/signup',
        method: 'POST',
        body: {'email': email, 'password': password, 'name': name},
        parse: (json) => AuthSession.fromJson(json as Map<String, dynamic>),
      );

  Future<AuthSession> login({required String email, required String password}) => _client.request(
    '/auth/login',
    method: 'POST',
    body: {'email': email, 'password': password},
    parse: (json) => AuthSession.fromJson(json as Map<String, dynamic>),
  );

  Future<AppUser> currentUser() =>
      _client.request('/auth/me', parse: (json) => AppUser.fromJson(json as Map<String, dynamic>));
}

final authRepositoryProvider = Provider<AuthRepository>((ref) => AuthRepository(ref.watch(apiClientProvider)));
