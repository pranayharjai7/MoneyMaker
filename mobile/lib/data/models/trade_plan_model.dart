import 'package:flutter/foundation.dart';

import 'stock_model.dart';

@immutable
class TradeTargetModel {
  const TradeTargetModel({
    required this.targetLabel,
    required this.price,
    required this.probability,
  });

  final String targetLabel;
  final double price;
  final double probability;

  factory TradeTargetModel.fromJson(Map<String, dynamic> json) {
    return TradeTargetModel(
      targetLabel: json['target_label'] as String,
      price: (json['price'] as num).toDouble(),
      probability: (json['probability'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {
        'target_label': targetLabel,
        'price': price,
        'probability': probability,
      };
}

@immutable
class TradeReasoningModel {
  const TradeReasoningModel({
    required this.factorType,
    required this.factorText,
  });

  final String factorType;
  final String factorText;

  factory TradeReasoningModel.fromJson(Map<String, dynamic> json) {
    return TradeReasoningModel(
      factorType: json['factor_type'] as String,
      factorText: json['factor_text'] as String,
    );
  }

  Map<String, dynamic> toJson() => {
        'factor_type': factorType,
        'factor_text': factorText,
      };
}

@immutable
class ExecutionRecommendationModel {
  const ExecutionRecommendationModel({
    required this.situation,
    required this.suggestedOrderType,
    required this.orderPrice,
    required this.reason,
  });

  final String situation;
  final String suggestedOrderType;
  final double orderPrice;
  final String reason;

  factory ExecutionRecommendationModel.fromJson(Map<String, dynamic> json) {
    return ExecutionRecommendationModel(
      situation: json['situation'] as String,
      suggestedOrderType: json['suggested_order_type'] as String,
      orderPrice: (json['order_price'] as num).toDouble(),
      reason: json['reason'] as String,
    );
  }

  Map<String, dynamic> toJson() => {
        'situation': situation,
        'suggested_order_type': suggestedOrderType,
        'order_price': orderPrice,
        'reason': reason,
      };
}

@immutable
class ExpectedMoveModel {
  const ExpectedMoveModel({
    required this.expectedUpsidePct,
    required this.expectedDownsidePct,
    required this.confidenceIntervalLow,
    required this.confidenceIntervalHigh,
  });

  final double expectedUpsidePct;
  final double expectedDownsidePct;
  final double confidenceIntervalLow;
  final double confidenceIntervalHigh;

  factory ExpectedMoveModel.fromJson(Map<String, dynamic> json) {
    return ExpectedMoveModel(
      expectedUpsidePct: (json['expected_upside_pct'] as num).toDouble(),
      expectedDownsidePct: (json['expected_downside_pct'] as num).toDouble(),
      confidenceIntervalLow: (json['confidence_interval_low'] as num).toDouble(),
      confidenceIntervalHigh: (json['confidence_interval_high'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {
        'expected_upside_pct': expectedUpsidePct,
        'expected_downside_pct': expectedDownsidePct,
        'confidence_interval_low': confidenceIntervalLow,
        'confidence_interval_high': confidenceIntervalHigh,
      };
}

@immutable
class TradePlanModel {
  const TradePlanModel({
    required this.id,
    required this.stockId,
    required this.currentPrice,
    required this.forecastWindowMinDays,
    required this.forecastWindowMaxDays,
    required this.bullishProbability,
    required this.bearishProbability,
    required this.neutralProbability,
    required this.confidence,
    required this.regimeContext,
    required this.weeklyBias,
    required this.dailyBias,
    required this.intradayBias,
    required this.suggestedEntryLow,
    required this.suggestedEntryHigh,
    required this.suggestedEntryPrice,
    required this.entryType,
    required this.entryTiming,
    required this.entryScore,
    required this.stopLoss,
    required this.maxSuggestedRiskPct,
    required this.riskRewardRatio,
    required this.expectedHoldMinDays,
    required this.expectedHoldMaxDays,
    required this.suggestedExecution,
    required this.createdAt,
    this.stock,
    required this.targets,
    required this.reasoning,
    required this.executionRecommendations,
    this.expectedMove,
  });

  final String id;
  final String stockId;
  final double currentPrice;
  final int forecastWindowMinDays;
  final int forecastWindowMaxDays;
  final double bullishProbability;
  final double bearishProbability;
  final double neutralProbability;
  final String confidence;
  final String regimeContext;
  final String weeklyBias;
  final String dailyBias;
  final String intradayBias;
  final double suggestedEntryLow;
  final double suggestedEntryHigh;
  final double suggestedEntryPrice;
  final String entryType;
  final String entryTiming;
  final double entryScore;
  final double stopLoss;
  final double maxSuggestedRiskPct;
  final double riskRewardRatio;
  final int expectedHoldMinDays;
  final int expectedHoldMaxDays;
  final String suggestedExecution;
  final DateTime createdAt;
  final StockModel? stock;
  final List<TradeTargetModel> targets;
  final List<TradeReasoningModel> reasoning;
  final List<ExecutionRecommendationModel> executionRecommendations;
  final ExpectedMoveModel? expectedMove;

  factory TradePlanModel.fromJson(Map<String, dynamic> json) {
    return TradePlanModel(
      id: json['id'] as String,
      stockId: json['stock_id'] as String,
      currentPrice: (json['current_price'] as num).toDouble(),
      forecastWindowMinDays: json['forecast_window_min_days'] as int,
      forecastWindowMaxDays: json['forecast_window_max_days'] as int,
      bullishProbability: (json['bullish_probability'] as num).toDouble(),
      bearishProbability: (json['bearish_probability'] as num).toDouble(),
      neutralProbability: (json['neutral_probability'] as num).toDouble(),
      confidence: json['confidence'] as String,
      regimeContext: json['regime_context'] as String,
      weeklyBias: json['weekly_bias'] as String,
      dailyBias: json['daily_bias'] as String,
      intradayBias: json['intraday_bias'] as String,
      suggestedEntryLow: (json['suggested_entry_low'] as num).toDouble(),
      suggestedEntryHigh: (json['suggested_entry_high'] as num).toDouble(),
      suggestedEntryPrice: (json['suggested_entry_price'] as num).toDouble(),
      entryType: json['entry_type'] as String,
      entryTiming: json['entry_timing'] as String,
      entryScore: (json['entry_score'] as num).toDouble(),
      stopLoss: (json['stop_loss'] as num).toDouble(),
      maxSuggestedRiskPct: (json['max_suggested_risk_pct'] as num).toDouble(),
      riskRewardRatio: (json['risk_reward_ratio'] as num).toDouble(),
      expectedHoldMinDays: json['expected_hold_min_days'] as int,
      expectedHoldMaxDays: json['expected_hold_max_days'] as int,
      suggestedExecution: json['suggested_execution'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      stock: json['stock'] != null ? StockModel.fromJson(json['stock'] as Map<String, dynamic>) : null,
      targets: (json['targets'] as List? ?? [])
          .map((item) => TradeTargetModel.fromJson(item as Map<String, dynamic>))
          .toList(),
      reasoning: (json['reasoning'] as List? ?? [])
          .map((item) => TradeReasoningModel.fromJson(item as Map<String, dynamic>))
          .toList(),
      executionRecommendations: (json['execution_recommendations'] as List? ?? [])
          .map((item) => ExecutionRecommendationModel.fromJson(item as Map<String, dynamic>))
          .toList(),
      expectedMove: json['expected_move'] != null
          ? ExpectedMoveModel.fromJson(json['expected_move'] as Map<String, dynamic>)
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'stock_id': stockId,
        'current_price': currentPrice,
        'forecast_window_min_days': forecastWindowMinDays,
        'forecast_window_max_days': forecastWindowMaxDays,
        'bullish_probability': bullishProbability,
        'bearish_probability': bearishProbability,
        'neutral_probability': neutralProbability,
        'confidence': confidence,
        'regime_context': regimeContext,
        'weekly_bias': weeklyBias,
        'daily_bias': dailyBias,
        'intraday_bias': intradayBias,
        'suggested_entry_low': suggestedEntryLow,
        'suggested_entry_high': suggestedEntryHigh,
        'suggested_entry_price': suggestedEntryPrice,
        'entry_type': entryType,
        'entry_timing': entryTiming,
        'entry_score': entryScore,
        'stop_loss': stopLoss,
        'max_suggested_risk_pct': maxSuggestedRiskPct,
        'risk_reward_ratio': riskRewardRatio,
        'expected_hold_min_days': expectedHoldMinDays,
        'expected_hold_max_days': expectedHoldMaxDays,
        'suggested_execution': suggestedExecution,
        'created_at': createdAt.toIso8601String(),
        if (stock != null) 'stock': stock!.toJson(),
        'targets': targets.map((item) => item.toJson()).toList(),
        'reasoning': reasoning.map((item) => item.toJson()).toList(),
        'execution_recommendations': executionRecommendations.map((item) => item.toJson()).toList(),
        if (expectedMove != null) 'expected_move': expectedMove!.toJson(),
      };
}

@immutable
class RiskAnalysisModel {
  const RiskAnalysisModel({
    required this.ticker,
    required this.suggestedEntryPrice,
    required this.stopLoss,
    required this.maxSuggestedRiskPct,
    required this.riskRewardRatio,
    required this.trailingStop,
  });

  final String ticker;
  final double suggestedEntryPrice;
  final double stopLoss;
  final double maxSuggestedRiskPct;
  final double riskRewardRatio;
  final String trailingStop;

  factory RiskAnalysisModel.fromJson(Map<String, dynamic> json) {
    return RiskAnalysisModel(
      ticker: json['ticker'] as String,
      suggestedEntryPrice: (json['suggested_entry_price'] as num).toDouble(),
      stopLoss: (json['stop_loss'] as num).toDouble(),
      maxSuggestedRiskPct: (json['max_suggested_risk_pct'] as num).toDouble(),
      riskRewardRatio: (json['risk_reward_ratio'] as num).toDouble(),
      trailingStop: json['trailing_stop'] as String,
    );
  }
}

@immutable
class TimeframeAnalysisModel {
  const TimeframeAnalysisModel({
    required this.ticker,
    required this.weekly,
    required this.daily,
    required this.intraday,
    required this.counterTrendWarning,
  });

  final String ticker;
  final String weekly;
  final String daily;
  final String intraday;
  final bool counterTrendWarning;

  factory TimeframeAnalysisModel.fromJson(Map<String, dynamic> json) {
    return TimeframeAnalysisModel(
      ticker: json['ticker'] as String,
      weekly: json['weekly'] as String,
      daily: json['daily'] as String,
      intraday: json['intraday'] as String,
      counterTrendWarning: json['counter_trend_warning'] as bool,
    );
  }
}
