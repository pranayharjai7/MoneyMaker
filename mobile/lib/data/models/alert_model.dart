import '../../domain/entities/risk_level.dart';
import 'stock_model.dart';

class AlertModel {
  const AlertModel({
    required this.id,
    required this.userId,
    required this.stockId,
    required this.alertType,
    required this.probability,
    required this.expectedReturn,
    required this.riskScore,
    required this.createdAt,
    required this.isRead,
    this.stock,
  });

  factory AlertModel.fromJson(Map<String, dynamic> json) {
    return AlertModel(
      id: json['id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      stockId: json['stock_id']?.toString() ?? '',
      alertType: json['alert_type']?.toString() ?? 'neutral',
      probability: (json['probability'] as num?)?.toDouble() ?? 0,
      expectedReturn: (json['expected_return'] as num?)?.toDouble() ?? 0,
      riskScore: (json['risk_score'] as num?)?.toDouble() ?? 1,
      createdAt: DateTime.parse(json['created_at'].toString()),
      isRead: json['is_read'] == true,
      stock: _stockFromJson(json),
    );
  }

  final String id;
  final String userId;
  final String stockId;
  final String alertType;
  final double probability;
  final double expectedReturn;
  final double riskScore;
  final DateTime createdAt;
  final bool isRead;
  final StockModel? stock;

  String get ticker => stock?.ticker ?? stockId;
  RiskLevel get riskLevel => RiskLevel.fromScore(riskScore);

  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'stock_id': stockId,
        'alert_type': alertType,
        'probability': probability,
        'expected_return': expectedReturn,
        'risk_score': riskScore,
        'created_at': createdAt.toIso8601String(),
        'is_read': isRead,
        'stock': stock?.toJson(),
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
