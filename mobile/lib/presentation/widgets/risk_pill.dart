import 'package:flutter/material.dart';

import '../../domain/entities/risk_level.dart';

class RiskPill extends StatelessWidget {
  const RiskPill({
    required this.riskLevel,
    super.key,
  });

  final RiskLevel riskLevel;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: riskLevel.color.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: riskLevel.color.withValues(alpha: 0.55)),
      ),
      child: Text(
        riskLevel.label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(color: riskLevel.color),
      ),
    );
  }
}
