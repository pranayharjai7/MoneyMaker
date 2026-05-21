import 'stock_model.dart';

class PortfolioHoldingModel {
  const PortfolioHoldingModel({
    required this.id,
    required this.userId,
    required this.stockId,
    required this.shares,
    required this.averagePrice,
    required this.createdAt,
    this.stock,
  });

  factory PortfolioHoldingModel.fromJson(Map<String, dynamic> json) {
    return PortfolioHoldingModel(
      id: json['id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      stockId: json['stock_id']?.toString() ?? '',
      shares: (json['shares'] as num?)?.toDouble() ?? 0,
      averagePrice: (json['average_price'] as num?)?.toDouble() ?? 0,
      createdAt: DateTime.parse(json['created_at'].toString()),
      stock: _stockFromJson(json),
    );
  }

  final String id;
  final String userId;
  final String stockId;
  final double shares;
  final double averagePrice;
  final DateTime createdAt;
  final StockModel? stock;

  String get ticker => stock?.ticker ?? stockId;
  double get costBasis => shares * averagePrice;

  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'stock_id': stockId,
        'shares': shares,
        'average_price': averagePrice,
        'created_at': createdAt.toIso8601String(),
        'stock': stock?.toJson(),
      };
}

class PortfolioWeightModel {
  const PortfolioWeightModel({
    required this.id,
    required this.stockId,
    required this.ticker,
    required this.allocation,
    required this.expectedReturn,
    required this.riskScore,
    required this.volatility,
    required this.signalTimestamp,
    this.sector,
    this.rationale = const {},
  });

  factory PortfolioWeightModel.fromJson(Map<String, dynamic> json) {
    return PortfolioWeightModel(
      id: json['id']?.toString() ?? '',
      stockId: json['stock_id']?.toString() ?? '',
      ticker: json['ticker']?.toString() ?? _stockFromJson(json)?.ticker ?? '',
      sector: json['sector']?.toString() ?? _stockFromJson(json)?.sector,
      allocation: (json['allocation'] as num?)?.toDouble() ?? 0,
      expectedReturn: (json['expected_return'] as num?)?.toDouble() ?? 0,
      riskScore: (json['risk_score'] as num?)?.toDouble() ?? 1,
      volatility: (json['volatility'] as num?)?.toDouble() ?? 0,
      signalTimestamp: DateTime.parse(json['signal_timestamp'].toString()),
      rationale: Map<String, dynamic>.from((json['rationale'] as Map?) ?? {}),
    );
  }

  final String id;
  final String stockId;
  final String ticker;
  final String? sector;
  final double allocation;
  final double expectedReturn;
  final double riskScore;
  final double volatility;
  final DateTime signalTimestamp;
  final Map<String, dynamic> rationale;

  Map<String, dynamic> toJson() => {
        'id': id,
        'stock_id': stockId,
        'ticker': ticker,
        'sector': sector,
        'allocation': allocation,
        'expected_return': expectedReturn,
        'risk_score': riskScore,
        'volatility': volatility,
        'signal_timestamp': signalTimestamp.toIso8601String(),
        'rationale': rationale,
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
