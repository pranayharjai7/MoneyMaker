import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:moneymaker_mobile/core/theme/app_theme.dart';
import 'package:moneymaker_mobile/data/models/signal_model.dart';
import 'package:moneymaker_mobile/data/models/stock_model.dart';
import 'package:moneymaker_mobile/features/signals/widgets/signal_card.dart';

void main() {
  testWidgets('signal card renders trading signal fields', (tester) async {
    final signal = SignalModel(
      id: 'signal-1',
      stockId: 'stock-1',
      timestamp: DateTime.utc(2026, 5, 20, 12),
      buyProbability: 0.68,
      sellProbability: 0.32,
      expectedReturn: 0.042,
      riskScore: 0.48,
      suggestedHoldDays: 5,
      signalType: 'buy',
      stock: const StockModel(
        id: 'stock-1',
        ticker: 'NVDA',
        companyName: 'NVIDIA',
        sector: 'Technology',
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        themeMode: ThemeMode.dark,
        darkTheme: AppTheme.dark(),
        home: Scaffold(body: SignalCard(signal: signal)),
      ),
    );

    expect(find.text('NVDA'), findsOneWidget);
    expect(find.text('BUY SIGNAL'), findsOneWidget);
    expect(find.text('Probability'), findsOneWidget);
    expect(find.text('+4.2%'), findsOneWidget);
    expect(find.text('Medium'), findsOneWidget);
  });
}
