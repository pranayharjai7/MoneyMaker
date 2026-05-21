import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:purchases_flutter/purchases_flutter.dart';

import 'app_providers.dart';

final offeringsProvider = FutureProvider<Offerings?>((ref) {
  return ref.watch(subscriptionRepositoryProvider).offerings();
});

final subscriptionControllerProvider = AsyncNotifierProvider<SubscriptionController, void>(
  SubscriptionController.new,
);

class SubscriptionController extends AsyncNotifier<void> {
  @override
  Future<void> build() async {}

  Future<void> restore() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      await ref.read(subscriptionRepositoryProvider).restorePurchases();
    });
  }

  Future<void> purchase(Package package) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      await ref.read(subscriptionRepositoryProvider).purchasePackage(package);
    });
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      await ref.read(subscriptionRepositoryProvider).refreshFromRevenueCat();
    });
  }
}
