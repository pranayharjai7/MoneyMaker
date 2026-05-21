enum AccessLevel {
  free,
  pro,
  elite;

  bool get hasRealtimeSignals => this == AccessLevel.pro || this == AccessLevel.elite;
  bool get hasAlerts => this == AccessLevel.pro || this == AccessLevel.elite;
  bool get hasPortfolioInsights => this == AccessLevel.pro || this == AccessLevel.elite;
  bool get hasExplainability => this == AccessLevel.elite;
  int get watchlistLimit => switch (this) {
        AccessLevel.free => 5,
        AccessLevel.pro => 50,
        AccessLevel.elite => 250,
      };

  String get label => switch (this) {
        AccessLevel.free => 'Free',
        AccessLevel.pro => 'Pro',
        AccessLevel.elite => 'Elite',
      };

  static AccessLevel fromString(String? value) {
    return switch (value?.toLowerCase()) {
      'elite' => AccessLevel.elite,
      'pro' => AccessLevel.pro,
      _ => AccessLevel.free,
    };
  }
}
