import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/extensions/formatters.dart';
import '../../core/theme/app_theme.dart';
import '../../domain/entities/access_level.dart';
import '../../presentation/providers/trading_providers.dart';
import '../../presentation/widgets/entitlement_gate.dart';
import '../../presentation/widgets/metric_tile.dart';
import '../../presentation/widgets/section_header.dart';

class InsightsScreen extends ConsumerWidget {
  const InsightsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final regime = ref.watch(regimeProvider);
    final performance = ref.watch(modelPerformanceProvider);
    final calibration = ref.watch(calibrationStatusProvider);

    return EntitlementGate(
      minimum: AccessLevel.pro,
      child: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(regimeProvider);
          ref.invalidate(modelPerformanceProvider);
          ref.invalidate(calibrationStatusProvider);
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
          children: [
            Text('Insights', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 14),
            regime.when(
              loading: () => const GlassCard(child: LinearProgressIndicator()),
              error: (error, stackTrace) => GlassCard(child: Text(error.toString())),
              data: (value) => Column(
                children: [
                  GridView.count(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    crossAxisCount: 2,
                    childAspectRatio: 1.55,
                    crossAxisSpacing: 10,
                    mainAxisSpacing: 10,
                    children: [
                      MetricTile(label: 'Current regime', value: value.currentRegime, accent: AppTheme.elite),
                      MetricTile(label: 'Confidence', value: value.confidence.asPercent(digits: 0)),
                      MetricTile(label: 'SPX trend', value: value.spxTrend.asSignedPercent(digits: 1)),
                      MetricTile(label: 'Liquidity', value: value.liquidityScore.asPercent(digits: 0)),
                    ],
                  ),
                  const SizedBox(height: 10),
                  GlassCard(
                    child: Text(_regimeExplanation(value.currentRegime)),
                  ),
                ],
              ),
            ),
            const SectionHeader(title: 'Model performance'),
            performance.when(
              loading: () => const GlassCard(child: LinearProgressIndicator()),
              error: (error, stackTrace) => GlassCard(child: Text(error.toString())),
              data: (models) {
                if (models.isEmpty) {
                  return const GlassCard(child: Text('No performance window available yet.'));
                }
                final averageAccuracy =
                    models.map((model) => model.accuracy).reduce((a, b) => a + b) / models.length;
                return Column(
                  children: [
                    MetricTile(
                      label: 'Model accuracy (${models.first.windowDays} days)',
                      value: averageAccuracy.asPercent(digits: 0),
                      accent: AppTheme.buy,
                    ),
                    const SizedBox(height: 10),
                    GlassCard(
                      child: SizedBox(
                        height: 210,
                        child: BarChart(
                          BarChartData(
                            borderData: FlBorderData(show: false),
                            gridData: const FlGridData(show: false),
                            titlesData: const FlTitlesData(show: false),
                            barGroups: [
                              for (var i = 0; i < models.length; i++)
                                BarChartGroupData(
                                  x: i,
                                  barRods: [
                                    BarChartRodData(
                                      toY: models[i].accuracy,
                                      width: 18,
                                      borderRadius: BorderRadius.circular(4),
                                      color: AppTheme.accent,
                                    ),
                                  ],
                                ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    for (final model in models)
                      GlassCard(
                        margin: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          children: [
                            Expanded(
                              child: Text(_label(model.modelName), style: Theme.of(context).textTheme.titleMedium),
                            ),
                            Text(model.accuracy.asPercent(digits: 0)),
                          ],
                        ),
                      ),
                  ],
                );
              },
            ),
            const SectionHeader(title: 'Calibration confidence'),
            calibration.when(
              loading: () => const GlassCard(child: LinearProgressIndicator()),
              error: (error, stackTrace) => GlassCard(child: Text(error.toString())),
              data: (status) => GlassCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Calibration quality: ${status.qualityLabel}',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            color: status.qualityLabel == 'GOOD' ? AppTheme.buy : AppTheme.hold,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Average error ${status.averageCalibrationError.asPercent(digits: 1)} across ${status.models.length} models',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 12),
                    for (final model in status.models.take(5))
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          children: [
                            Expanded(child: Text(_label(model.modelName))),
                            Text(model.calibrationError.asPercent(digits: 1)),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _regimeExplanation(String regime) {
    return switch (regime) {
      'BULL TREND' => 'Bull trend favors momentum continuation and lets high-confidence buy signals carry more weight.',
      'BEAR TREND' => 'Bear trend raises drawdown risk; sell and risk alerts receive priority.',
      'HIGH VOLATILITY' => 'High volatility narrows hold windows and increases position-size discipline.',
      'LOW LIQUIDITY' => 'Low liquidity reduces confidence for thinly traded names and widens risk buffers.',
      _ => 'Sideways markets favor selectivity, calibration quality, and lower portfolio concentration.',
    };
  }

  String _label(String value) {
    return value.replaceAll('_', ' ').split(' ').map((part) {
      if (part.isEmpty) {
        return part;
      }
      return '${part[0].toUpperCase()}${part.substring(1)}';
    }).join(' ');
  }
}
