import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/extensions/formatters.dart';
import '../../core/theme/app_theme.dart';
import '../../domain/entities/access_level.dart';
import '../../domain/entities/risk_level.dart';
import '../../presentation/providers/trading_providers.dart';
import '../../presentation/widgets/entitlement_gate.dart';
import '../../presentation/widgets/metric_tile.dart';
import '../../presentation/widgets/risk_pill.dart';
import '../../presentation/widgets/section_header.dart';

class PortfolioScreen extends ConsumerWidget {
  const PortfolioScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final holdingsState = ref.watch(portfolioProvider);
    final weightsState = ref.watch(portfolioWeightsProvider);

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(portfolioProvider);
        ref.invalidate(portfolioWeightsProvider);
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
        children: [
          Text('Portfolio', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 14),
          holdingsState.when(
            loading: () => const GlassCard(child: LinearProgressIndicator()),
            error: (error, stackTrace) => GlassCard(child: Text(error.toString())),
            data: (holdings) {
              final totalBasis = holdings.fold<double>(0, (sum, item) => sum + item.costBasis);
              return GridView.count(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: 2,
                childAspectRatio: 1.55,
                mainAxisSpacing: 10,
                crossAxisSpacing: 10,
                children: [
                  MetricTile(label: 'Holdings', value: holdings.length.toString()),
                  MetricTile(label: 'Cost basis', value: totalBasis.asMoney()),
                ],
              );
            },
          ),
          const SectionHeader(title: 'Holdings'),
          holdingsState.when(
            loading: () => const SizedBox.shrink(),
            error: (error, stackTrace) => const SizedBox.shrink(),
            data: (holdings) {
              if (holdings.isEmpty) {
                return const GlassCard(child: Text('No holdings yet.'));
              }
              return Column(
                children: [
                  for (final holding in holdings)
                    GlassCard(
                      margin: const EdgeInsets.only(bottom: 10),
                      child: Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(holding.ticker, style: Theme.of(context).textTheme.titleLarge),
                                Text(
                                  '${holding.shares.toStringAsFixed(2)} shares',
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                              ],
                            ),
                          ),
                          Text(holding.costBasis.asMoney()),
                        ],
                      ),
                    ),
                ],
              );
            },
          ),
          const SectionHeader(title: 'AI recommended allocation'),
          EntitlementGate(
            minimum: AccessLevel.pro,
            child: weightsState.when(
              loading: () => const GlassCard(child: LinearProgressIndicator()),
              error: (error, stackTrace) => GlassCard(child: Text(error.toString())),
              data: (weights) {
                if (weights.isEmpty) {
                  return const GlassCard(child: Text('No allocation run available.'));
                }
                final risk = weights.fold<double>(0, (sum, weight) => sum + weight.riskScore * weight.allocation);
                return Column(
                  children: [
                    GlassCard(
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              'Risk exposure ${(risk).asPercent(digits: 0)}',
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                          ),
                          RiskPill(riskLevel: RiskLevel.fromScore(risk)),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    GlassCard(
                      child: SizedBox(
                        height: 180,
                        child: PieChart(
                          PieChartData(
                            sectionsSpace: 2,
                            centerSpaceRadius: 46,
                            sections: [
                              for (var i = 0; i < weights.take(8).length; i++)
                                PieChartSectionData(
                                  value: weights[i].allocation,
                                  title: weights[i].ticker,
                                  radius: 54,
                                  titleStyle: Theme.of(context).textTheme.labelLarge,
                                  color: _allocationColors[i % _allocationColors.length],
                                ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    for (final weight in weights)
                      GlassCard(
                        margin: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(weight.ticker, style: Theme.of(context).textTheme.titleMedium),
                                  Text(
                                    weight.sector ?? 'Unclassified',
                                    style: Theme.of(context).textTheme.bodyMedium,
                                  ),
                                ],
                              ),
                            ),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: [
                                Text(weight.allocation.asPercent(digits: 1)),
                                Text(
                                  weight.expectedReturn.asSignedPercent(digits: 1),
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                  ],
                );
              },
            ),
          ),
          const SectionHeader(title: 'Sector breakdown'),
          weightsState.maybeWhen(
            data: (weights) {
              final sectors = <String, double>{};
              for (final weight in weights) {
                sectors.update(
                  weight.sector ?? 'Other',
                  (value) => value + weight.allocation,
                  ifAbsent: () => weight.allocation,
                );
              }
              if (sectors.isEmpty) {
                return const GlassCard(child: Text('No sector allocation yet.'));
              }
              return Column(
                children: [
                  for (final entry in sectors.entries)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Row(
                        children: [
                          Expanded(child: Text(entry.key)),
                          SizedBox(
                            width: 130,
                            child: LinearProgressIndicator(
                              value: entry.value.clamp(0, 1),
                              minHeight: 8,
                              borderRadius: BorderRadius.circular(8),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Text(entry.value.asPercent(digits: 0)),
                        ],
                      ),
                    ),
                ],
              );
            },
            orElse: () => const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }
}

const _allocationColors = [
  AppTheme.accent,
  AppTheme.elite,
  AppTheme.purple,
  AppTheme.buy,
  AppTheme.hold,
  Color(0xFFFF9F7A),
  Color(0xFF8BD3FF),
  Color(0xFFFF7AB6),
];
