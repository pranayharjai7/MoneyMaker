import 'package:flutter/material.dart';

import '../../../core/extensions/formatters.dart';
import '../../../core/theme/app_theme.dart';
import '../../../data/models/signal_model.dart';
import '../../../presentation/widgets/risk_pill.dart';

class SignalCard extends StatelessWidget {
  const SignalCard({
    required this.signal,
    super.key,
    this.onTap,
  });

  final SignalModel signal;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final signalColor = signal.isBuy
        ? AppTheme.buy
        : signal.isSell
            ? AppTheme.sell
            : AppTheme.hold;
    return GlassCard(
      onTap: onTap,
      margin: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      signal.ticker,
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    Text(
                      '${signal.signalType.toUpperCase()} SIGNAL',
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(color: signalColor),
                    ),
                  ],
                ),
              ),
              RiskPill(riskLevel: signal.riskLevel),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _MiniMetric(
                label: 'Probability',
                value: signal.buyProbability.asPercent(digits: 0),
              ),
              _MiniMetric(
                label: 'Expected return',
                value: signal.expectedReturn.asSignedPercent(digits: 1),
                color: signal.expectedReturn >= 0 ? AppTheme.buy : AppTheme.sell,
              ),
              _MiniMetric(
                label: 'Hold',
                value: '${signal.suggestedHoldDays}-${signal.suggestedHoldDays + 2} days',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MiniMetric extends StatelessWidget {
  const _MiniMetric({
    required this.label,
    required this.value,
    this.color,
  });

  final String label;
  final String value;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: const BoxConstraints(minWidth: 96),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 4),
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(color: color),
          ),
        ],
      ),
    );
  }
}
