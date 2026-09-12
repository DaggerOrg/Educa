import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/application/auth_controller.dart';
import '../../features/auth/presentation/screens/login_screen.dart';
import '../../features/auth/presentation/screens/signup_screen.dart';
import '../../features/course/presentation/screens/course_screen.dart';
import '../../features/course/presentation/screens/lesson_screen.dart';

/// Rebuilt (new GoRouter instance) whenever [authControllerProvider]'s
/// value changes — simplest correct way to keep routing and auth state in
/// sync without a separate ChangeNotifier bridge. The instance swap only
/// happens at the auth boundary (logged in <-> logged out), so it doesn't
/// disturb in-app navigation.
final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authControllerProvider);
  final isAuthenticated = authState.valueOrNull?.isAuthenticated ?? false;
  // Only the very first load counts as "resolving" — an error (e.g. secure
  // storage unavailable) must fall through to the login screen rather than
  // stall on the splash screen forever, since it never produces a value.
  final isResolving = authState.isLoading && !authState.hasValue;

  return GoRouter(
    initialLocation: '/',
    redirect: (context, state) {
      final loc = state.matchedLocation;
      if (isResolving) {
        return loc == '/splash' ? null : '/splash';
      }
      final onAuthScreen = loc == '/login' || loc == '/signup';
      if (!isAuthenticated) {
        return onAuthScreen ? null : '/login';
      }
      if (onAuthScreen || loc == '/splash') return '/';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (context, state) => const _SplashScreen()),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(path: '/signup', builder: (context, state) => const SignupScreen()),
      GoRoute(path: '/', builder: (context, state) => const CourseScreen()),
      GoRoute(
        path: '/lesson/:lessonId',
        builder: (context, state) => LessonScreen(lessonId: state.pathParameters['lessonId']!),
      ),
    ],
  );
});

class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}
