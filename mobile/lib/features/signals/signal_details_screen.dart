import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/extensions/formatters.dart';
import '../../core/theme/app_theme.dart';
import '../../domain/entities/access_level.dart';
import '../../presentation/providers/trading_providers.dart';
import '../../presentation/widgets/entitlement_gate.dart';
import '../../presentation/widgets/metric_tile.dart';
import '../../presentation/widgets/risk_pill.dart';
import '../../presentation/widgets/section_header.dart';

class SignalDetailsScreen extends ConsumerWidget {
  const SignalDetailsScreen({
    required this.signalId,
    super.key,
  });

  final String signalId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final signal = ref.watch(signalByIdProvider(signalId));
    if (signal == null) {
      return const Center(child: Text('Signal not found.'));
    }
    final explainability = ref.watch(signalExplainabilityProvider(signal));
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
      children: [
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Signal: ${signal.signalType.toUpperCase()} ${signal.ticker}',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  Text(signal.timestamp.shortDateTime, style: Theme.of(context).textTheme.bodyMedium),
                ],
              ),
            ),
            RiskPill(riskLevel: signal.riskLevel),
          ],
        ),
        const SizedBox(height: 16),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          childAspectRatio: 1.5,
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          children: [
            MetricTile(label: 'Buy probability', value: signal.buyProbability.asPercent(digits: 0)),
            MetricTile(
              label: 'Expected return',
              value: signal.expectedReturn.asSignedPercent(digits: 1),
              accent: signal.expectedReturn >= 0 ? AppTheme.buy : AppTheme.sell,
            ),
            MetricTile(label: 'Risk score', value: signal.riskScore.asPercent(digits: 0)),
            MetricTile(label: 'Hold window', value: '${signal.suggestedHoldDays}-${signal.suggestedHoldDays + 2} days'),
          ],
        ),
        const SectionHeader(title: 'Why'),
        EntitlementGate(
          minimum: AccessLevel.elite,
          child: explainability.when(
            loading: () => const GlassCard(child: Center(child: CircularProgressIndicator())),
            error: (error, stackTrace) => GlassCard(child: Text(error.toString())),
            data: (explanation) {
              final agreed = explanation.modelAgreements.where((model) => model.agreed).toList();
              return GlassCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _ReasonRow(text: '${explanation.regime.currentRegime} regime active'),
                    for (final model in agreed)
                      _ReasonRow(
                        text:
                            '${_label(model.modelName)} agreed (${model.probability.asPercent(digits: 0)}, confidence ${model.confidence.asPercent(digits: 0)})',
                      ),
                    if (agreed.isEmpty) const _ReasonRow(text: 'Consensus is mixed; position size should stay conservative'),
                  ],
                ),
              );
            },
          ),
        ),
        const SectionHeader(title: 'Risk'),
        explainability.when(
          loading: () => const GlassCard(child: LinearProgressIndicator()),
          error: (error, stackTrace) => GlassCard(child: Text(error.toString())),
          data: (explanation) => GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final reason in explanation.riskReasons) _RiskRow(text: reason),
              ],
            ),
          ),
        ),
      ],
    );
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

class _ReasonRow extends StatelessWidget {
  const _ReasonRow({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          const Icon(Icons.check_circle, color: AppTheme.buy, size: 18),
          const SizedBox(width: 10),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}

class _RiskRow extends StatelessWidget {
  const _RiskRow({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          const Icon(Icons.warning_amber, color: AppTheme.hold, size: 18),
          const SizedBox(width: 10),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}
