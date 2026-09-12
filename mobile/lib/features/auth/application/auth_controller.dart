import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/storage/token_storage.dart';
import '../../course/application/course_controller.dart';
import '../data/auth_repository.dart';
import '../domain/app_user.dart';

class AuthState {
  final AppUser? user;

  const AuthState({this.user});

  bool get isAuthenticated => user != null;
}

/// The app's session state. `build()` runs once at startup: is there a
/// stored token, and if so is it still valid? The router (core/router)
/// watches this to decide between the auth screens and the course
/// screens — nothing else needs to know about tokens.
class AuthController extends AsyncNotifier<AuthState> {
  @override
  Future<AuthState> build() async {
    final token = await ref.read(tokenStorageProvider).readToken();
    if (token == null) return const AuthState();
    try {
      final user = await ref.read(authRepositoryProvider).currentUser();
      return AuthState(user: user);
    } catch (_) {
      // Stored token is expired/invalid — drop it rather than looping the
      // user into a broken "logged in but every call 401s" state.
      await ref.read(tokenStorageProvider).clearToken();
      return const AuthState();
    }
  }

  Future<void> login(String email, String password) async {
    state = const AsyncLoading<AuthState>().copyWithPrevious(state);
    state = await AsyncValue.guard(() async {
      final session = await ref.read(authRepositoryProvider).login(email: email, password: password);
      await ref.read(tokenStorageProvider).saveToken(session.token);
      return AuthState(user: session.user);
    });
  }

  Future<void> signup({required String email, required String password, required String name}) async {
    state = const AsyncLoading<AuthState>().copyWithPrevious(state);
    state = await AsyncValue.guard(() async {
      final session = await ref.read(authRepositoryProvider).signup(email: email, password: password, name: name);
      await ref.read(tokenStorageProvider).saveToken(session.token);
      return AuthState(user: session.user);
    });
  }

  Future<void> logout() async {
    await ref.read(tokenStorageProvider).clearToken();
    ref.invalidate(courseControllerProvider);
    state = const AsyncData(AuthState());
  }
}

final authControllerProvider = AsyncNotifierProvider<AuthController, AuthState>(AuthController.new);
