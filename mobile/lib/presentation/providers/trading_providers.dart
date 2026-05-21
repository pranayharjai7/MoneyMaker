import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/alert_model.dart';
import '../../data/models/entitlement_model.dart';
import '../../data/models/insight_models.dart';
import '../../data/models/portfolio_model.dart';
import '../../data/models/signal_model.dart';
import '../../data/models/watchlist_model.dart';
import '../../data/repositories/trading_repository.dart';
import 'app_providers.dart';

final entitlementProvider = StreamProvider<EntitlementModel>((ref) {
  return ref.watch(subscriptionRepositoryProvider).watchEntitlement();
});

final signalsProvider = StreamProvider<List<SignalModel>>((ref) {
  final entitlement = ref.watch(entitlementProvider).valueOrNull;
  final userId = ref.watch(supabaseClientProvider).auth.currentUser?.id ?? '';
  return ref.watch(tradingRepositoryProvider).watchSignals(
        entitlement: entitlement ?? EntitlementModel.free(userId),
      );
});

final alertsProvider = StreamProvider<List<AlertModel>>((ref) {
  final entitlement = ref.watch(entitlementProvider).valueOrNull;
  final userId = ref.watch(supabaseClientProvider).auth.currentUser?.id ?? '';
  return ref.watch(tradingRepositoryProvider).watchAlerts(
        entitlement: entitlement ?? EntitlementModel.free(userId),
      );
});

final watchlistProvider = StreamProvider<List<WatchlistItemModel>>((ref) {
  final signals = ref.watch(signalsProvider).valueOrNull ?? const <SignalModel>[];
  return ref.watch(tradingRepositoryProvider).watchWatchlist(signals);
});

final portfolioProvider = FutureProvider<List<PortfolioHoldingModel>>((ref) {
  return ref.watch(tradingRepositoryProvider).getPortfolio();
});

final portfolioWeightsProvider = FutureProvider<List<PortfolioWeightModel>>((ref) {
  return ref.watch(tradingRepositoryProvider).getPortfolioWeights();
});

final regimeProvider = FutureProvider<MarketRegimeModel>((ref) {
  return ref.watch(tradingRepositoryProvider).getRegime();
});

final modelPerformanceProvider = FutureProvider<List<ModelPerformanceModel>>((ref) {
  return ref.watch(tradingRepositoryProvider).getModelPerformance();
});

final calibrationStatusProvider = FutureProvider<CalibrationStatusModel>((ref) {
  return ref.watch(tradingRepositoryProvider).getCalibrationStatus();
});

final signalByIdProvider = Provider.family<SignalModel?, String>((ref, id) {
  final signals = ref.watch(signalsProvider).valueOrNull ?? const <SignalModel>[];
  for (final signal in signals) {
    if (signal.id == id) {
      return signal;
    }
  }
  return null;
});

final signalExplainabilityProvider = FutureProvider.family<SignalExplainability, SignalModel>((ref, signal) {
  return ref.watch(tradingRepositoryProvider).explainSignal(signal);
});

final dashboardSummaryProvider = Provider<DashboardSummary>((ref) {
  final signals = ref.watch(signalsProvider).valueOrNull ?? const <SignalModel>[];
  final alerts = ref.watch(alertsProvider).valueOrNull ?? const <AlertModel>[];
  final regime = ref.watch(regimeProvider).valueOrNull;
  final topSignals = signals.where((signal) => signal.isBuy).take(5).toList(growable: false);
  final riskScore = topSignals.isEmpty
      ? 0.5
      : topSignals.map((signal) => signal.riskScore).reduce((a, b) => a + b) / topSignals.length;
  return DashboardSummary(
    topSignals: topSignals,
    activeAlerts: alerts.where((alert) => !alert.isRead).toList(growable: false),
    regime: regime,
    portfolioRiskScore: riskScore,
  );
});

class DashboardSummary {
  const DashboardSummary({
    required this.topSignals,
    required this.activeAlerts,
    required this.regime,
    required this.portfolioRiskScore,
  });

  final List<SignalModel> topSignals;
  final List<AlertModel> activeAlerts;
  final MarketRegimeModel? regime;
  final double portfolioRiskScore;
}
