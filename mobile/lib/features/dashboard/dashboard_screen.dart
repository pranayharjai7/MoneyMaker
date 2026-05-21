import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/extensions/formatters.dart';
import '../../core/theme/app_theme.dart';
import '../../domain/entities/risk_level.dart';
import '../../presentation/providers/trading_providers.dart';
import '../../presentation/widgets/metric_tile.dart';
import '../../presentation/widgets/risk_pill.dart';
import '../../presentation/widgets/section_header.dart';
import '../signals/widgets/signal_card.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref.watch(dashboardSummaryProvider);
    final signalsState = ref.watch(signalsProvider);
    final riskLevel = RiskLevel.fromScore(summary.portfolioRiskScore);

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(regimeProvider);
        ref.invalidate(portfolioWeightsProvider);
        ref.invalidate(modelPerformanceProvider);
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'AI Trading Desk',
                  style: Theme.of(context).textTheme.headlineLarge,
                ),
              ),
              RiskPill(riskLevel: riskLevel),
            ],
          ),
          const SizedBox(height: 16),
          GridView.count(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisCount: MediaQuery.sizeOf(context).width > 680 ? 4 : 2,
            mainAxisSpacing: 10,
            crossAxisSpacing: 10,
            childAspectRatio: 1.55,
            children: [
              MetricTile(
                label: 'Market regime',
                value: summary.regime?.currentRegime ?? 'Loading',
                accent: AppTheme.elite,
              ),
              MetricTile(
                label: 'Regime confidence',
                value: (summary.regime?.confidence ?? 0).asPercent(digits: 0),
              ),
              MetricTile(
                label: 'Portfolio risk',
                value: summary.portfolioRiskScore.asPercent(digits: 0),
                accent: riskLevel.color,
              ),
              MetricTile(
                label: 'Active alerts',
                value: summary.activeAlerts.length.toString(),
                accent: AppTheme.hold,
              ),
            ],
          ),
          SectionHeader(
            title: 'Top buy signals',
            action: TextButton(
              onPressed: () => context.go('/signals'),
              child: const Text('All signals'),
            ),
          ),
          signalsState.when(
            loading: () => const _SignalSkeleton(),
            error: (error, stackTrace) => _ErrorPanel(message: error.toString()),
            data: (_) {
              final topSignals = summary.topSignals;
              if (topSignals.isEmpty) {
                return const _EmptyPanel(message: 'No buy signals are available yet.');
              }
              return Column(
                children: [
                  for (final signal in topSignals)
                    SignalCard(
                      signal: signal,
                      onTap: () => context.go('/signals/${signal.id}'),
                    ),
                ],
              );
            },
          ),
          const SectionHeader(title: 'Active alerts'),
          if (summary.activeAlerts.isEmpty)
            const _EmptyPanel(message: 'No unread alerts.')
          else
            for (final alert in summary.activeAlerts.take(4))
              GlassCard(
                margin: const EdgeInsets.only(bottom: 10),
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text('${alert.alertType.toUpperCase()} ${alert.ticker}'),
                  subtitle: Text(
                    'Probability ${alert.probability.asPercent(digits: 0)} • ${alert.createdAt.shortDateTime}',
                  ),
                  trailing: Icon(Icons.chevron_right, color: Theme.of(context).colorScheme.primary),
                  onTap: () => context.go('/alerts'),
                ),
              ),
        ],
      ),
    );
  }
}

class _SignalSkeleton extends StatelessWidget {
  const _SignalSkeleton();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: List.generate(
        3,
        (index) => GlassCard(
          margin: const EdgeInsets.only(bottom: 12),
          child: SizedBox(
            height: 88,
            child: Center(
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _EmptyPanel extends StatelessWidget {
  const _EmptyPanel({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return GlassCard(child: Text(message));
  }
}

class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Text(
        message,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.sell),
      ),
    );
  }
}
