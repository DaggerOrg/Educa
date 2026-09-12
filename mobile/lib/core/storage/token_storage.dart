import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Persists the auth JWT in the platform keychain/keystore (not
/// SharedPreferences — a session token shouldn't sit in plaintext).
/// Single source of truth for "are we logged in": AuthController reads it
/// on startup and writes/clears it on login/signup/logout.
class TokenStorage {
  static const _tokenKey = 'educa_auth_token';

  final FlutterSecureStorage _storage;

  TokenStorage({FlutterSecureStorage? storage}) : _storage = storage ?? const FlutterSecureStorage();

  Future<String?> readToken() => _storage.read(key: _tokenKey);

  Future<void> saveToken(String token) => _storage.write(key: _tokenKey, value: token);

  Future<void> clearToken() => _storage.delete(key: _tokenKey);
}

final tokenStorageProvider = Provider<TokenStorage>((ref) => TokenStorage());
