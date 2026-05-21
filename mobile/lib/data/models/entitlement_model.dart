import '../../domain/entities/access_level.dart';

class EntitlementModel {
  const EntitlementModel({
    required this.userId,
    required this.accessLevel,
    required this.activeEntitlements,
    this.expiresAt,
    this.source = 'local',
  });

  factory EntitlementModel.free(String userId) {
    return EntitlementModel(
      userId: userId,
      accessLevel: AccessLevel.free,
      activeEntitlements: const [],
    );
  }

  factory EntitlementModel.fromJson(Map<String, dynamic> json) {
    final active = (json['active_entitlements'] as List?)
            ?.map((item) => item.toString())
            .toList() ??
        const <String>[];
    return EntitlementModel(
      userId: json['user_id']?.toString() ?? '',
      accessLevel: AccessLevel.fromString(json['access_level']?.toString()),
      activeEntitlements: active,
      expiresAt: json['expires_at'] == null ? null : DateTime.parse(json['expires_at'].toString()),
      source: json['source']?.toString() ?? 'backend',
    );
  }

  final String userId;
  final AccessLevel accessLevel;
  final List<String> activeEntitlements;
  final DateTime? expiresAt;
  final String source;

  bool get isActive => expiresAt == null || expiresAt!.isAfter(DateTime.now());
  bool get hasRealtimeSignals => isActive && accessLevel.hasRealtimeSignals;
  bool get hasAlerts => isActive && accessLevel.hasAlerts;
  bool get hasPortfolioInsights => isActive && accessLevel.hasPortfolioInsights;
  bool get hasExplainability => isActive && accessLevel.hasExplainability;

  Map<String, dynamic> toJson() => {
        'user_id': userId,
        'access_level': accessLevel.name,
        'active_entitlements': activeEntitlements,
        'expires_at': expiresAt?.toIso8601String(),
        'source': source,
      };
}
