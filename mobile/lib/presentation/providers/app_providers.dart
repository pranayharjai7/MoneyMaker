import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/config/app_config.dart';
import '../../data/repositories/auth_repository.dart';
import '../../data/repositories/subscription_repository.dart';
import '../../data/repositories/trading_repository.dart';
import '../../data/services/api_client.dart';
import '../../data/services/cache_service.dart';
import '../../data/services/notification_service.dart';
import '../../data/services/subscription_service.dart';

final supabaseClientProvider = Provider<SupabaseClient>((_) => Supabase.instance.client);

final cacheServiceProvider = Provider<CacheService>((ref) => CacheService());

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(
    config: ref.watch(appConfigProvider),
    supabase: ref.watch(supabaseClientProvider),
  );
});

final notificationServiceProvider = Provider<NotificationService>((ref) {
  final service = NotificationService();
  ref.onDispose(() {
    service.dispose();
  });
  return service;
});

final subscriptionServiceProvider = Provider<SubscriptionService>((ref) {
  return SubscriptionService();
});

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(supabaseClientProvider));
});

final tradingRepositoryProvider = Provider<TradingRepository>((ref) {
  return TradingRepository(
    supabase: ref.watch(supabaseClientProvider),
    apiClient: ref.watch(apiClientProvider),
    cache: ref.watch(cacheServiceProvider),
  );
});

final subscriptionRepositoryProvider = Provider<SubscriptionRepository>((ref) {
  return SubscriptionRepository(
    supabase: ref.watch(supabaseClientProvider),
    cache: ref.watch(cacheServiceProvider),
    subscriptionService: ref.watch(subscriptionServiceProvider),
  );
});
