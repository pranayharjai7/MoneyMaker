import 'dart:async';

import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/constants/app_constants.dart';
import '../models/alert_model.dart';
import '../models/entitlement_model.dart';
import '../models/insight_models.dart';
import '../models/portfolio_model.dart';
import '../models/signal_model.dart';
import '../models/stock_model.dart';
import '../models/watchlist_model.dart';
import '../models/trade_plan_model.dart';
import '../services/api_client.dart';
import '../services/cache_service.dart';

class TradingRepository {
  const TradingRepository({
    required SupabaseClient supabase,
    required ApiClient apiClient,
    required CacheService cache,
  })  : _supabase = supabase,
        _apiClient = apiClient,
        _cache = cache;

  final SupabaseClient _supabase;
  final ApiClient _apiClient;
  final CacheService _cache;

  Stream<List<SignalModel>> watchSignals({
    required EntitlementModel entitlement,
    int limit = 100,
  }) async* {
    final cached = await _cache.readList(AppConstants.signalCacheKey);
    if (cached.isNotEmpty) {
      yield _applySignalAccess(
        cached.map(SignalModel.fromJson).toList(),
        entitlement,
      );
    }

    await for (final rows in _supabase
        .from('ensemble_signals')
        .stream(primaryKey: ['id'])
        .order('timestamp', ascending: false)
        .limit(limit)) {
      final hydrated = await _hydrateSignalRows(rows);
      final signals = hydrated.map(SignalModel.fromJson).toList(growable: false);
      await _cache.writeList(
        AppConstants.signalCacheKey,
        signals.map((signal) => signal.toJson()).toList(growable: false),
      );
      yield _applySignalAccess(signals, entitlement);
    }
  }

  Stream<List<AlertModel>> watchAlerts({
    required EntitlementModel entitlement,
  }) async* {
    final user = _supabase.auth.currentUser;
    if (user == null) {
      return;
    }
    final cached = await _cache.readList(AppConstants.alertsCacheKey);
    if (cached.isNotEmpty) {
      yield cached.map(AlertModel.fromJson).toList();
    }
    if (!entitlement.hasAlerts) {
      return;
    }
    await for (final rows in _supabase
        .from('alerts')
        .stream(primaryKey: ['id'])
        .eq('user_id', user.id)
        .order('created_at', ascending: false)) {
      final hydrated = await _hydrateAlertRows(rows);
      final alerts = hydrated.map(AlertModel.fromJson).toList(growable: false);
      await _cache.writeList(
        AppConstants.alertsCacheKey,
        alerts.map((alert) => alert.toJson()).toList(growable: false),
      );
      yield alerts;
    }
  }

  Stream<List<WatchlistItemModel>> watchWatchlist(List<SignalModel> signals) async* {
    final user = _supabase.auth.currentUser;
    if (user == null) {
      return;
    }
    final cached = await _cache.readList(AppConstants.watchlistCacheKey);
    if (cached.isNotEmpty) {
      yield _mergeWatchlistProbabilities(cached.map(WatchlistItemModel.fromJson), signals);
    }
    await for (final rows in _supabase
        .from('user_watchlists')
        .stream(primaryKey: ['id'])
        .eq('user_id', user.id)
        .order('created_at', ascending: false)) {
      final hydrated = await _hydrateWatchlistRows(rows);
      final items = _mergeWatchlistProbabilities(
        hydrated.map(WatchlistItemModel.fromJson),
        signals,
      );
      await _cache.writeList(
        AppConstants.watchlistCacheKey,
        items.map((item) => item.toJson()).toList(growable: false),
      );
      yield items;
    }
  }

  Future<WatchlistItemModel> addToWatchlist(String ticker) async {
    final row = await _apiClient.postMap('/watchlist/add', body: {'ticker': ticker.trim().toUpperCase()});
    return WatchlistItemModel.fromJson(row);
  }

  Future<void> setWatchlistAlertEnabled({
    required String stockId,
    required bool enabled,
  }) async {
    final user = _supabase.auth.currentUser;
    if (user == null) {
      throw StateError('No signed-in user.');
    }
    await _supabase.from('watchlist_alert_preferences').upsert(
      {
        'user_id': user.id,
        'stock_id': stockId,
        'alerts_enabled': enabled,
      },
      onConflict: 'user_id,stock_id',
    );
  }

  Future<void> markAlertsRead(List<String> alertIds) async {
    if (alertIds.isEmpty) {
      return;
    }
    await _apiClient.postList('/alerts/read', body: {'alert_ids': alertIds});
  }

  Future<List<PortfolioHoldingModel>> getPortfolio() async {
    final cached = await _cache.readList(AppConstants.portfolioCacheKey);
    final rows = await _apiClient.getList('/portfolio').catchError((_) => cached);
    await _cache.writeList(AppConstants.portfolioCacheKey, rows);
    return rows.map(PortfolioHoldingModel.fromJson).toList(growable: false);
  }

  Future<List<PortfolioWeightModel>> getPortfolioWeights() async {
    final cached = await _cache.readList(AppConstants.portfolioWeightsCacheKey);
    final rows = await _apiClient.getList('/portfolio-weights').catchError((_) => cached);
    await _cache.writeList(AppConstants.portfolioWeightsCacheKey, rows);
    return rows.map(PortfolioWeightModel.fromJson).toList(growable: false);
  }

  Future<MarketRegimeModel> getRegime() async {
    final cached = await _cache.readMap(AppConstants.regimeCacheKey);
    final row = await _apiClient.getMap('/regime').catchError((_) {
      if (cached == null) {
        throw StateError('No cached market regime available.');
      }
      return cached;
    });
    await _cache.writeMap(AppConstants.regimeCacheKey, row);
    return MarketRegimeModel.fromJson(row);
  }

  Future<List<ModelPerformanceModel>> getModelPerformance() async {
    final cached = await _cache.readList(AppConstants.performanceCacheKey);
    final rows = await _apiClient.getList('/model-performance').catchError((_) => cached);
    await _cache.writeList(AppConstants.performanceCacheKey, rows);
    return rows.map(ModelPerformanceModel.fromJson).toList(growable: false);
  }

  Future<CalibrationStatusModel> getCalibrationStatus() async {
    final cached = await _cache.readMap(AppConstants.calibrationCacheKey);
    final row = await _apiClient.getMap('/calibration-status').catchError((_) {
      if (cached == null) {
        throw StateError('No cached calibration status available.');
      }
      return cached;
    });
    await _cache.writeMap(AppConstants.calibrationCacheKey, row);
    return CalibrationStatusModel.fromJson(row);
  }

  Future<SignalExplainability> explainSignal(SignalModel signal) async {
    final predictions = await _supabase
        .from('model_predictions')
        .select()
        .eq('stock_id', signal.stockId)
        .eq('timestamp', signal.timestamp.toIso8601String())
        .order('confidence', ascending: false);
    final regime = await getRegime();
    final modelReasons = predictions.whereType<Map>().map((raw) {
      final row = Map<String, dynamic>.from(raw);
      final probability = (row['probability_up'] as num?)?.toDouble() ?? 0.5;
      final confidence = (row['confidence'] as num?)?.toDouble() ?? 0;
      final modelName = row['model_name']?.toString() ?? 'Model';
      return ModelAgreement(
        modelName: modelName,
        agreed: signal.isBuy ? probability >= 0.55 : probability <= 0.45,
        probability: probability,
        confidence: confidence,
      );
    }).toList(growable: false);

    return SignalExplainability(
      signal: signal,
      regime: regime,
      modelAgreements: modelReasons,
      riskReasons: _riskReasons(signal, regime),
    );
  }

  List<SignalModel> _applySignalAccess(
    List<SignalModel> signals,
    EntitlementModel entitlement,
  ) {
    if (entitlement.hasRealtimeSignals) {
      return signals;
    }
    final cutoff = DateTime.now().toUtc().subtract(
          const Duration(minutes: AppConstants.delayedSignalMinutes),
        );
    return signals.where((signal) => signal.timestamp.toUtc().isBefore(cutoff)).toList(growable: false);
  }

  Future<List<Map<String, dynamic>>> _hydrateSignalRows(List<Map<String, dynamic>> rows) async {
    final stocks = await _stocksForIds(
      rows.map((row) => row['stock_id']?.toString()).nonNulls,
    );
    return rows
        .map(
          (row) => {
            ...row,
            'stock': stocks[row['stock_id']?.toString()]?.toJson(),
          },
        )
        .toList(growable: false);
  }

  Future<List<Map<String, dynamic>>> _hydrateAlertRows(List<Map<String, dynamic>> rows) async {
    final stocks = await _stocksForIds(
      rows.map((row) => row['stock_id']?.toString()).nonNulls,
    );
    return rows
        .map(
          (row) => {
            ...row,
            'stock': stocks[row['stock_id']?.toString()]?.toJson(),
          },
        )
        .toList(growable: false);
  }

  Future<List<Map<String, dynamic>>> _hydrateWatchlistRows(List<Map<String, dynamic>> rows) async {
    final stocks = await _stocksForIds(
      rows.map((row) => row['stock_id']?.toString()).nonNulls,
    );
    final preferences = await _watchlistPreferences();
    return rows
        .map(
          (row) => {
            ...row,
            'stock': stocks[row['stock_id']?.toString()]?.toJson(),
            'alerts_enabled': preferences[row['stock_id']?.toString()] ?? true,
          },
        )
        .toList(growable: false);
  }

  Future<Map<String, StockModel>> _stocksForIds(Iterable<String> ids) async {
    final unique = ids.where((id) => id.isNotEmpty).toSet().toList(growable: false);
    if (unique.isEmpty) {
      return const {};
    }
    final rows = await _supabase.from('stocks').select().inFilter('id', unique);
    return {
      for (final raw in rows.whereType<Map>())
        StockModel.fromJson(Map<String, dynamic>.from(raw)).id:
            StockModel.fromJson(Map<String, dynamic>.from(raw)),
    };
  }

  Future<Map<String, bool>> _watchlistPreferences() async {
    final user = _supabase.auth.currentUser;
    if (user == null) {
      return const {};
    }
    final rows = await _supabase
        .from('watchlist_alert_preferences')
        .select('stock_id,alerts_enabled')
        .eq('user_id', user.id);
    return {
      for (final raw in rows.whereType<Map>())
        raw['stock_id'].toString(): raw['alerts_enabled'] != false,
    };
  }

  List<WatchlistItemModel> _mergeWatchlistProbabilities(
    Iterable<WatchlistItemModel> items,
    List<SignalModel> signals,
  ) {
    final latestByStock = <String, SignalModel>{};
    for (final signal in signals) {
      final existing = latestByStock[signal.stockId];
      if (existing == null || signal.timestamp.isAfter(existing.timestamp)) {
        latestByStock[signal.stockId] = signal;
      }
    }
    return items
        .map((item) => item.copyWith(latestProbability: latestByStock[item.stockId]?.buyProbability))
        .toList(growable: false);
  }

  List<String> _riskReasons(SignalModel signal, MarketRegimeModel regime) {
    return [
      if (signal.riskScore >= 0.55) 'High volatility increases stop-loss sensitivity',
      if (signal.riskScore >= 0.35 && signal.riskScore < 0.55) 'Medium volatility requires controlled sizing',
      if (regime.sectorCorrelationShift > 0.5) 'Sector correlation is elevated',
      if (regime.liquidityScore < 0.5) 'Liquidity score is below normal',
      if (signal.expectedReturn.abs() < 0.02) 'Expected return edge is modest',
      if (signal.riskScore < 0.35) 'Risk model shows stable volatility and drawdown profile',
    ];
  }

  Future<TradePlanModel> getTradePlan(String ticker) async {
    final row = await _apiClient.getMap('/trade-plans/$ticker');
    return TradePlanModel.fromJson(row);
  }

  Future<RiskAnalysisModel> getRiskAnalysis(String ticker) async {
    final row = await _apiClient.getMap('/risk-analysis/$ticker');
    return RiskAnalysisModel.fromJson(row);
  }

  Future<TimeframeAnalysisModel> getTimeframeAnalysis(String ticker) async {
    final row = await _apiClient.getMap('/timeframes/$ticker');
    return TimeframeAnalysisModel.fromJson(row);
  }
}

class SignalExplainability {
  const SignalExplainability({
    required this.signal,
    required this.regime,
    required this.modelAgreements,
    required this.riskReasons,
  });

  final SignalModel signal;
  final MarketRegimeModel regime;
  final List<ModelAgreement> modelAgreements;
  final List<String> riskReasons;
}

class ModelAgreement {
  const ModelAgreement({
    required this.modelName,
    required this.agreed,
    required this.probability,
    required this.confidence,
  });

  final String modelName;
  final bool agreed;
  final double probability;
  final double confidence;
}
