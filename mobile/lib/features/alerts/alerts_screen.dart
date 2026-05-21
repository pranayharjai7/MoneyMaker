import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/extensions/formatters.dart';
import '../../core/theme/app_theme.dart';
import '../../domain/entities/access_level.dart';
import '../../presentation/providers/app_providers.dart';
import '../../presentation/providers/trading_providers.dart';
import '../../presentation/widgets/entitlement_gate.dart';
import '../../presentation/widgets/risk_pill.dart';

class AlertsScreen extends ConsumerWidget {
  const AlertsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alertsState = ref.watch(alertsProvider);
    return EntitlementGate(
      minimum: AccessLevel.pro,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
        children: [
          Row(
            children: [
              Expanded(
                child: Text('Alerts', style: Theme.of(context).textTheme.headlineMedium),
              ),
              TextButton.icon(
                onPressed: () async {
                  final ids = (alertsState.valueOrNull ?? const [])
                      .where((alert) => !alert.isRead)
                      .map((alert) => alert.id)
                      .toList();
                  await ref.read(tradingRepositoryProvider).markAlertsRead(ids);
                  ref.invalidate(alertsProvider);
                },
                icon: const Icon(Icons.done_all),
                label: const Text('Read'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          alertsState.when(
            loading: () => const GlassCard(child: LinearProgressIndicator()),
            error: (error, stackTrace) => GlassCard(child: Text(error.toString())),
            data: (alerts) {
              if (alerts.isEmpty) {
                return const GlassCard(child: Text('No alerts yet.'));
              }
              return Column(
                children: [
                  for (final alert in alerts)
                    GlassCard(
                      margin: const EdgeInsets.only(bottom: 10),
                      child: Row(
                        children: [
                          Icon(
                            alert.alertType == 'sell'
                                ? Icons.trending_down
                                : alert.alertType == 'risk'
                                    ? Icons.warning_amber
                                    : Icons.trending_up,
                            color: alert.alertType == 'sell' ? AppTheme.sell : AppTheme.buy,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '${alert.alertType.toUpperCase()} ${alert.ticker}',
                                  style: Theme.of(context).textTheme.titleMedium,
                                ),
                                Text(
                                  'Probability ${alert.probability.asPercent(digits: 0)} • Return ${alert.expectedReturn.asSignedPercent(digits: 1)}',
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                                Text(alert.createdAt.shortDateTime, style: Theme.of(context).textTheme.bodyMedium),
                              ],
                            ),
                          ),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              RiskPill(riskLevel: alert.riskLevel),
                              const SizedBox(height: 8),
                              Icon(
                                alert.isRead ? Icons.mark_email_read_outlined : Icons.circle,
                                size: alert.isRead ? 20 : 10,
                                color: alert.isRead ? AppTheme.textSecondary : AppTheme.accent,
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
        ],
      ),
    );
  }
}
