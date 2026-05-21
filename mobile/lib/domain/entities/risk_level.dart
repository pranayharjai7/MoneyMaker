import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

enum RiskLevel {
  low,
  medium,
  high;

  static RiskLevel fromScore(double score) {
    if (score < 0.35) {
      return RiskLevel.low;
    }
    if (score < 0.6) {
      return RiskLevel.medium;
    }
    return RiskLevel.high;
  }

  Color get color => switch (this) {
        RiskLevel.low => AppTheme.buy,
        RiskLevel.medium => AppTheme.hold,
        RiskLevel.high => AppTheme.sell,
      };

  String get label => switch (this) {
        RiskLevel.low => 'Low',
        RiskLevel.medium => 'Medium',
        RiskLevel.high => 'High',
      };
}
