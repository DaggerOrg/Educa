import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:educa_mobile/app.dart';
import 'package:educa_mobile/core/network/api_client.dart';
import 'package:educa_mobile/core/storage/token_storage.dart';
import 'package:educa_mobile/features/auth/data/auth_repository.dart';
import 'package:educa_mobile/features/auth/domain/app_user.dart';
import 'package:educa_mobile/features/course/data/course_repository.dart';
import 'package:educa_mobile/features/course/domain/course.dart';

/// In-memory stand-in for flutter_secure_storage, which has no platform
/// channel wired up under `flutter test`.
class _FakeTokenStorage extends TokenStorage {
  String? _token;

  @override
  Future<String?> readToken() async => _token;

  @override
  Future<void> saveToken(String token) async => _token = token;

  @override
  Future<void> clearToken() async => _token = null;
}

const _fakeUser = AppUser(id: 'user_1', email: 'teacher@example.com', name: 'Ada');

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository() : super(ApiClient(tokenStorage: _FakeTokenStorage()));

  @override
  Future<AuthSession> login({required String email, required String password}) async =>
      const AuthSession(token: 'fake-token', user: _fakeUser);

  @override
  Future<AuthSession> signup({required String email, required String password, required String name}) async =>
      const AuthSession(token: 'fake-token', user: _fakeUser);

  @override
  Future<AppUser> currentUser() async => _fakeUser;
}

class _FakeCourseRepository extends CourseRepository {
  _FakeCourseRepository() : super(ApiClient(tokenStorage: _FakeTokenStorage()));

  @override
  Future<Course> fetchCourse() async =>
      const Course(id: 'demo-course', title: 'Intro to Python', audience: '14-year-olds', weeks: []);
}

void main() {
  testWidgets('logging in navigates from the login screen to the course screen', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStorageProvider.overrideWithValue(_FakeTokenStorage()),
          authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
          courseRepositoryProvider.overrideWithValue(_FakeCourseRepository()),
        ],
        child: const EducaApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Welcome back'), findsOneWidget);

    await tester.enterText(find.byType(TextFormField).at(0), 'teacher@example.com');
    await tester.enterText(find.byType(TextFormField).at(1), 'hunter22!!');
    await tester.tap(find.widgetWithText(FilledButton, 'Log in'));
    await tester.pumpAndSettle();

    expect(find.text('Intro to Python'), findsOneWidget);
    expect(find.text('Welcome back'), findsNothing);
  });
}
