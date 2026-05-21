import 'stock_model.dart';

class WatchlistItemModel {
  const WatchlistItemModel({
    required this.id,
    required this.userId,
    required this.stockId,
    required this.createdAt,
    this.stock,
    this.latestProbability,
    this.alertsEnabled = true,
  });

  factory WatchlistItemModel.fromJson(Map<String, dynamic> json) {
    return WatchlistItemModel(
      id: json['id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      stockId: json['stock_id']?.toString() ?? '',
      createdAt: DateTime.parse(json['created_at'].toString()),
      stock: _stockFromJson(json),
      latestProbability: (json['latest_probability'] as num?)?.toDouble(),
      alertsEnabled: json['alerts_enabled'] != false,
    );
  }

  final String id;
  final String userId;
  final String stockId;
  final DateTime createdAt;
  final StockModel? stock;
  final double? latestProbability;
  final bool alertsEnabled;

  String get ticker => stock?.ticker ?? stockId;

  WatchlistItemModel copyWith({
    double? latestProbability,
    bool? alertsEnabled,
  }) {
    return WatchlistItemModel(
      id: id,
      userId: userId,
      stockId: stockId,
      createdAt: createdAt,
      stock: stock,
      latestProbability: latestProbability ?? this.latestProbability,
      alertsEnabled: alertsEnabled ?? this.alertsEnabled,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'stock_id': stockId,
        'created_at': createdAt.toIso8601String(),
        'stock': stock?.toJson(),
        'latest_probability': latestProbability,
        'alerts_enabled': alertsEnabled,
      };
}

StockModel? _stockFromJson(Map<String, dynamic> json) {
  final raw = json['stock'] ?? json['stocks'];
  if (raw is Map<String, dynamic>) {
    return StockModel.fromJson(raw);
  }
  if (raw is Map) {
    return StockModel.fromJson(Map<String, dynamic>.from(raw));
  }
  return null;
}
