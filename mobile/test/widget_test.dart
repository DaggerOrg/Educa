import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:educa_mobile/app.dart';
import 'package:educa_mobile/core/storage/token_storage.dart';

/// Avoids flutter_secure_storage's platform channel, which isn't wired up
/// in a plain widget test — this is exactly what overriding a provider in
/// tests is for.
class _FakeTokenStorage extends TokenStorage {
  @override
  Future<String?> readToken() async => null;

  @override
  Future<void> saveToken(String token) async {}

  @override
  Future<void> clearToken() async {}
}

void main() {
  testWidgets('shows the login screen when logged out', (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [tokenStorageProvider.overrideWithValue(_FakeTokenStorage())],
        child: const EducaApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Educa'), findsOneWidget);
    expect(find.text('Welcome back'), findsOneWidget);
  });
}
