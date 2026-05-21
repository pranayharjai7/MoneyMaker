import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/config/app_config.dart';
import 'app_providers.dart';

final appStartupProvider = FutureProvider<void>((ref) async {
  final cache = ref.watch(cacheServiceProvider);
  await cache.init();

  final config = ref.watch(appConfigProvider);
  final supabase = ref.watch(supabaseClientProvider);

  await ref.watch(notificationServiceProvider).initialize(
        config: config,
        supabase: supabase,
      );
  await ref.watch(subscriptionServiceProvider).configure(
        config: config,
        supabase: supabase,
      );
});
