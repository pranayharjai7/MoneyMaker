import 'dart:async';

import 'package:purchases_flutter/purchases_flutter.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/constants/app_constants.dart';
import '../models/entitlement_model.dart';
import '../services/cache_service.dart';
import '../services/subscription_service.dart';

class SubscriptionRepository {
  const SubscriptionRepository({
    required SupabaseClient supabase,
    required CacheService cache,
    required SubscriptionService subscriptionService,
  })  : _supabase = supabase,
        _cache = cache,
        _subscriptionService = subscriptionService;

  final SupabaseClient _supabase;
  final CacheService _cache;
  final SubscriptionService _subscriptionService;

  Stream<EntitlementModel> watchEntitlement() async* {
    final user = _supabase.auth.currentUser;
    if (user == null) {
      return;
    }
    final cached = await _cache.readMap(AppConstants.entitlementCacheKey);
    if (cached != null) {
      yield EntitlementModel.fromJson(cached);
    } else {
      yield EntitlementModel.free(user.id);
    }

    await for (final rows in _supabase
        .from('user_entitlements')
        .stream(primaryKey: ['user_id'])
        .eq('user_id', user.id)
        .limit(1)) {
      final entitlement = rows.isEmpty
          ? EntitlementModel.free(user.id)
          : EntitlementModel.fromJson(Map<String, dynamic>.from(rows.first));
      await _cache.writeMap(AppConstants.entitlementCacheKey, entitlement.toJson());
      yield entitlement;
    }
  }

  Future<EntitlementModel> refreshFromRevenueCat() async {
    final user = _supabase.auth.currentUser;
    if (user == null) {
      throw StateError('No signed-in user.');
    }
    final entitlement = await _subscriptionService.customerInfoEntitlement(user.id);
    await _cache.writeMap(AppConstants.entitlementCacheKey, entitlement.toJson());
    return entitlement;
  }

  Future<EntitlementModel> restorePurchases() async {
    final user = _supabase.auth.currentUser;
    if (user == null) {
      throw StateError('No signed-in user.');
    }
    final entitlement = await _subscriptionService.restorePurchases(user.id);
    await _cache.writeMap(AppConstants.entitlementCacheKey, entitlement.toJson());
    return entitlement;
  }

  Future<Offerings?> offerings() {
    return _subscriptionService.offerings();
  }

  Future<EntitlementModel> purchasePackage(Package package) async {
    final user = _supabase.auth.currentUser;
    if (user == null) {
      throw StateError('No signed-in user.');
    }
    final entitlement = await _subscriptionService.purchasePackage(user.id, package);
    await _cache.writeMap(AppConstants.entitlementCacheKey, entitlement.toJson());
    return entitlement;
  }
}
