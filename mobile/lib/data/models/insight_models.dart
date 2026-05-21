class MarketRegimeModel {
  const MarketRegimeModel({
    required this.timestamp,
    required this.currentRegime,
    required this.confidence,
    required this.spxTrend,
    required this.volatilityProxy,
    required this.movingAverageSpread,
    required this.sectorCorrelationShift,
    required this.liquidityScore,
    this.featurePayload = const {},
  });

  factory MarketRegimeModel.fromJson(Map<String, dynamic> json) {
    return MarketRegimeModel(
      timestamp: DateTime.parse(json['timestamp'].toString()),
      currentRegime: json['current_regime']?.toString() ?? 'UNKNOWN',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      spxTrend: (json['spx_trend'] as num?)?.toDouble() ?? 0,
      volatilityProxy: (json['volatility_proxy'] as num?)?.toDouble() ?? 0,
      movingAverageSpread: (json['moving_average_spread'] as num?)?.toDouble() ?? 0,
      sectorCorrelationShift: (json['sector_correlation_shift'] as num?)?.toDouble() ?? 0,
      liquidityScore: (json['liquidity_score'] as num?)?.toDouble() ?? 0,
      featurePayload: Map<String, dynamic>.from((json['feature_payload'] as Map?) ?? {}),
    );
  }

  final DateTime timestamp;
  final String currentRegime;
  final double confidence;
  final double spxTrend;
  final double volatilityProxy;
  final double movingAverageSpread;
  final double sectorCorrelationShift;
  final double liquidityScore;
  final Map<String, dynamic> featurePayload;

  Map<String, dynamic> toJson() => {
        'timestamp': timestamp.toIso8601String(),
        'current_regime': currentRegime,
        'confidence': confidence,
        'spx_trend': spxTrend,
        'volatility_proxy': volatilityProxy,
        'moving_average_spread': movingAverageSpread,
        'sector_correlation_shift': sectorCorrelationShift,
        'liquidity_score': liquidityScore,
        'feature_payload': featurePayload,
      };
}

class ModelPerformanceModel {
  const ModelPerformanceModel({
    required this.modelName,
    required this.accuracy,
    required this.brierScore,
    required this.calibrationError,
    required this.sharpeContribution,
    required this.sampleSize,
    required this.windowDays,
    this.updatedAt,
  });

  factory ModelPerformanceModel.fromJson(Map<String, dynamic> json) {
    return ModelPerformanceModel(
      modelName: json['model_name']?.toString() ?? '',
      accuracy: (json['accuracy'] as num?)?.toDouble() ?? 0,
      brierScore: (json['brier_score'] as num?)?.toDouble() ?? 0,
      calibrationError: (json['calibration_error'] as num?)?.toDouble() ?? 0,
      sharpeContribution: (json['sharpe_contribution'] as num?)?.toDouble() ?? 0,
      sampleSize: (json['sample_size'] as num?)?.toInt() ?? 0,
      windowDays: (json['window_days'] as num?)?.toInt() ?? 90,
      updatedAt: json['updated_at'] == null ? null : DateTime.parse(json['updated_at'].toString()),
    );
  }

  final String modelName;
  final double accuracy;
  final double brierScore;
  final double calibrationError;
  final double sharpeContribution;
  final int sampleSize;
  final int windowDays;
  final DateTime? updatedAt;

  Map<String, dynamic> toJson() => {
        'model_name': modelName,
        'accuracy': accuracy,
        'brier_score': brierScore,
        'calibration_error': calibrationError,
        'sharpe_contribution': sharpeContribution,
        'sample_size': sampleSize,
        'window_days': windowDays,
        'updated_at': updatedAt?.toIso8601String(),
      };
}

class CalibrationStatusModel {
  const CalibrationStatusModel({
    required this.status,
    required this.windowDays,
    required this.models,
    this.latestCalibratedAt,
  });

  factory CalibrationStatusModel.fromJson(Map<String, dynamic> json) {
    final rawModels = (json['models'] as List?) ?? const [];
    return CalibrationStatusModel(
      status: json['status']?.toString() ?? 'unknown',
      windowDays: (json['window_days'] as num?)?.toInt() ?? 90,
      latestCalibratedAt: json['latest_calibrated_at'] == null
          ? null
          : DateTime.parse(json['latest_calibrated_at'].toString()),
      models: rawModels
          .whereType<Map>()
          .map((item) => CalibrationModelStatus.fromJson(Map<String, dynamic>.from(item)))
          .toList(),
    );
  }

  final String status;
  final int windowDays;
  final DateTime? latestCalibratedAt;
  final List<CalibrationModelStatus> models;

  double get averageCalibrationError {
    if (models.isEmpty) {
      return 0;
    }
    return models.map((model) => model.calibrationError).reduce((a, b) => a + b) / models.length;
  }

  String get qualityLabel {
    if (averageCalibrationError <= 0.05) {
      return 'GOOD';
    }
    if (averageCalibrationError <= 0.12) {
      return 'WATCH';
    }
    return 'WEAK';
  }

  Map<String, dynamic> toJson() => {
        'status': status,
        'window_days': windowDays,
        'latest_calibrated_at': latestCalibratedAt?.toIso8601String(),
        'models': models.map((model) => model.toJson()).toList(),
      };
}

class CalibrationModelStatus {
  const CalibrationModelStatus({
    required this.modelName,
    required this.calibrationMethod,
    required this.sampleSize,
    required this.calibrationError,
  });

  factory CalibrationModelStatus.fromJson(Map<String, dynamic> json) {
    return CalibrationModelStatus(
      modelName: json['model_name']?.toString() ?? '',
      calibrationMethod: json['calibration_method']?.toString() ?? '',
      sampleSize: (json['sample_size'] as num?)?.toInt() ?? 0,
      calibrationError: (json['calibration_error'] as num?)?.toDouble() ?? 0,
    );
  }

  final String modelName;
  final String calibrationMethod;
  final int sampleSize;
  final double calibrationError;

  Map<String, dynamic> toJson() => {
        'model_name': modelName,
        'calibration_method': calibrationMethod,
        'sample_size': sampleSize,
        'calibration_error': calibrationError,
      };
}
