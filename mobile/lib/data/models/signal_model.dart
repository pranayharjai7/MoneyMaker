import '../../domain/entities/risk_level.dart';
import 'stock_model.dart';

class SignalModel {
  const SignalModel({
    required this.id,
    required this.stockId,
    required this.timestamp,
    required this.buyProbability,
    required this.sellProbability,
    required this.expectedReturn,
    required this.riskScore,
    required this.suggestedHoldDays,
    required this.signalType,
    this.stock,
  });

  factory SignalModel.fromJson(Map<String, dynamic> json) {
    return SignalModel(
      id: json['id']?.toString() ?? '${json['stock_id']}-${json['timestamp']}',
      stockId: json['stock_id']?.toString() ?? '',
      timestamp: DateTime.parse(json['timestamp'].toString()),
      buyProbability: (json['buy_probability'] as num?)?.toDouble() ?? 0.5,
      sellProbability: (json['sell_probability'] as num?)?.toDouble() ?? 0.5,
      expectedReturn: (json['expected_return'] as num?)?.toDouble() ?? 0,
      riskScore: (json['risk_score'] as num?)?.toDouble() ?? 1,
      suggestedHoldDays: (json['suggested_hold_days'] as num?)?.toInt() ?? 1,
      signalType: json['signal_type']?.toString() ?? 'neutral',
      stock: _stockFromJson(json),
    );
  }

  final String id;
  final String stockId;
  final DateTime timestamp;
  final double buyProbability;
  final double sellProbability;
  final double expectedReturn;
  final double riskScore;
  final int suggestedHoldDays;
  final String signalType;
  final StockModel? stock;

  String get ticker => stock?.ticker ?? stockId;
  RiskLevel get riskLevel => RiskLevel.fromScore(riskScore);
  bool get isBuy => signalType.toLowerCase() == 'buy';
  bool get isSell => signalType.toLowerCase() == 'sell';

  Map<String, dynamic> toJson() => {
        'id': id,
        'stock_id': stockId,
        'timestamp': timestamp.toIso8601String(),
        'buy_probability': buyProbability,
        'sell_probability': sellProbability,
        'expected_return': expectedReturn,
        'risk_score': riskScore,
        'suggested_hold_days': suggestedHoldDays,
        'signal_type': signalType,
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
