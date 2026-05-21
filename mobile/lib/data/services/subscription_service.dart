import 'package:flutter/foundation.dart';
import 'package:purchases_flutter/purchases_flutter.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/config/app_config.dart';
import '../../domain/entities/access_level.dart';
import '../models/entitlement_model.dart';

class SubscriptionService {
  SubscriptionService({
    Purchases? purchases,
  });

  bool _configured = false;

  Future<void> configure({
    required AppConfig config,
    required SupabaseClient supabase,
  }) async {
    if (_configured ||
        !config.hasRevenueCatKeys ||
        defaultTargetPlatform == TargetPlatform.windows ||
        defaultTargetPlatform == TargetPlatform.linux) {
      return;
    }
    final apiKey = defaultTargetPlatform == TargetPlatform.iOS
        ? config.revenueCatIosApiKey
        : config.revenueCatAndroidApiKey;
    if (apiKey.isEmpty) {
      return;
    }
    final userId = supabase.auth.currentUser?.id;
    final purchasesConfig = PurchasesConfiguration(apiKey);
    if (userId != null) {
      purchasesConfig.appUserID = userId;
    }
    await Purchases.configure(purchasesConfig);
    _configured = true;
    if (userId != null) {
      await Purchases.logIn(userId);
    }
  }

  Future<EntitlementModel> customerInfoEntitlement(String userId) async {
    if (!_configured) {
      return EntitlementModel.free(userId);
    }
    final info = await Purchases.getCustomerInfo();
    return _mapCustomerInfo(userId, info);
  }

  Future<Offerings?> offerings() async {
    if (!_configured) {
      return null;
    }
    return Purchases.getOfferings();
  }

  Future<EntitlementModel> purchasePackage(String userId, Package package) async {
    final result = await Purchases.purchase(PurchaseParams.package(package));
    return _mapCustomerInfo(userId, result.customerInfo);
  }

  Future<EntitlementModel> restorePurchases(String userId) async {
    if (!_configured) {
      return EntitlementModel.free(userId);
    }
    final info = await Purchases.restorePurchases();
    return _mapCustomerInfo(userId, info);
  }

  EntitlementModel _mapCustomerInfo(String userId, CustomerInfo info) {
    final active = info.entitlements.active.keys.toList(growable: false);
    final level = active.contains('elite')
        ? AccessLevel.elite
        : active.contains('pro')
            ? AccessLevel.pro
            : AccessLevel.free;
    DateTime? latestExpiration;
    for (final entitlement in info.entitlements.active.values) {
      final expiration = entitlement.expirationDate;
      if (expiration == null) {
        latestExpiration = null;
        break;
      }
      final parsed = DateTime.tryParse(expiration);
      if (parsed != null && (latestExpiration == null || parsed.isAfter(latestExpiration))) {
        latestExpiration = parsed;
      }
    }
    return EntitlementModel(
      userId: userId,
      accessLevel: level,
      activeEntitlements: active,
      expiresAt: latestExpiration,
      source: 'revenuecat',
    );
  }
}
