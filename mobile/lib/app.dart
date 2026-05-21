import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/routing/app_router.dart';
import 'core/theme/app_theme.dart';
import 'presentation/providers/app_startup_provider.dart';

class MoneyMakerApp extends ConsumerWidget {
  const MoneyMakerApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(appStartupProvider);
    final router = ref.watch(appRouterProvider);

    return MaterialApp.router(
      title: 'MoneyMaker AI',
      themeMode: ThemeMode.dark,
      darkTheme: AppTheme.dark(),
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}
