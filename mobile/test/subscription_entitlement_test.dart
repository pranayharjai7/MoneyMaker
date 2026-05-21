import 'package:flutter_test/flutter_test.dart';
import 'package:moneymaker_mobile/data/models/entitlement_model.dart';
import 'package:moneymaker_mobile/domain/entities/access_level.dart';

void main() {
  test('pro entitlement unlocks realtime signals and alerts', () {
    final entitlement = EntitlementModel(
      userId: 'user-1',
      accessLevel: AccessLevel.pro,
      activeEntitlements: const ['pro'],
      expiresAt: DateTime.now().add(const Duration(days: 7)),
    );

    expect(entitlement.hasRealtimeSignals, isTrue);
    expect(entitlement.hasAlerts, isTrue);
    expect(entitlement.hasExplainability, isFalse);
  });

  test('elite entitlement unlocks explainability', () {
    final entitlement = EntitlementModel(
      userId: 'user-1',
      accessLevel: AccessLevel.elite,
      activeEntitlements: const ['elite'],
      expiresAt: DateTime.now().add(const Duration(days: 7)),
    );

    expect(entitlement.hasExplainability, isTrue);
    expect(entitlement.accessLevel.watchlistLimit, 250);
  });
}
