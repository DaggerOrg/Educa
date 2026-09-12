import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router/app_router.dart';
import 'core/theme/studio_theme.dart';

class EducaApp extends ConsumerWidget {
  const EducaApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: 'Educa',
      debugShowCheckedModeBanner: false,
      theme: studioLightTheme,
      darkTheme: studioDarkTheme,
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
