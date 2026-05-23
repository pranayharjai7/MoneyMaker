import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/extensions/formatters.dart';
import '../../core/theme/app_theme.dart';
import '../../data/models/signal_model.dart';
import '../../data/models/trade_plan_model.dart';
import '../../presentation/providers/trading_providers.dart';
import '../../presentation/widgets/entitlement_gate.dart';
import '../../presentation/widgets/risk_pill.dart';
import '../../presentation/widgets/section_header.dart';
import '../../domain/entities/access_level.dart';

class SignalDetailsScreen extends ConsumerStatefulWidget {
  const SignalDetailsScreen({
    required this.signalId,
    super.key,
  });

  final String signalId;

  @override
  ConsumerState<SignalDetailsScreen> createState() => _SignalDetailsScreenState();
}

class _SignalDetailsScreenState extends ConsumerState<SignalDetailsScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final signal = ref.watch(signalByIdProvider(widget.signalId));
    if (signal == null) {
      return const Scaffold(
        body: Center(child: Text('Signal not found.')),
      );
    }

    final tradePlanState = ref.watch(tradePlanProvider(signal.ticker));

    return Scaffold(
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(48),
        child: TabBar(
          controller: _tabController,
          indicatorColor: AppTheme.accent,
          labelColor: AppTheme.textPrimary,
          unselectedLabelColor: AppTheme.textSecondary,
          tabs: const [
            Tab(text: 'Trade Plan'),
            Tab(text: 'AI Reasoning'),
            Tab(text: 'Lifecycle'),
          ],
        ),
      ),
      body: tradePlanState.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Text(
              'Error loading plan: ${error.toString()}',
              textAlign: TextAlign.center,
            ),
          ),
        ),
        data: (plan) => TabBarView(
          controller: _tabController,
          children: [
            _buildTradePlanTab(context, signal, plan),
            _buildReasoningTab(context, signal, plan),
            _buildLifecycleTab(context, signal, plan),
          ],
        ),
      ),
    );
  }

  Widget _buildTradePlanTab(BuildContext context, SignalModel signal, TradePlanModel plan) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
      children: [
        // Header Stock Row
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    plan.stock?.companyName ?? signal.ticker,
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  Text(
                    'Ticker: ${signal.ticker.toUpperCase()} • Current Price: \$${plan.currentPrice.toStringAsFixed(2)}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            RiskPill(riskLevel: signal.riskLevel),
          ],
        ),
        const SizedBox(height: 16),

        // Probability / Forecast metrics
        GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('AI Prediction Window', style: TextStyle(fontWeight: FontWeight.bold)),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: _confidenceColor(plan.confidence).withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: _confidenceColor(plan.confidence).withValues(alpha: 0.35)),
                    ),
                    child: Text(
                      '${plan.confidence} CONFIDENCE',
                      style: TextStyle(
                        color: _confidenceColor(plan.confidence),
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Expected range in ${plan.forecastWindowMinDays}–${plan.forecastWindowMaxDays} trading days:',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 10),
              if (plan.expectedMove != null) ...[
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '\$${plan.expectedMove!.confidenceIntervalLow.toStringAsFixed(2)}',
                      style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.sell),
                    ),
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            Container(
                              height: 6,
                              decoration: BoxDecoration(
                                color: Colors.white24,
                                borderRadius: BorderRadius.circular(3),
                              ),
                            ),
                            Positioned(
                              left: 30,
                              right: 30,
                              child: Container(
                                height: 6,
                                decoration: BoxDecoration(
                                  color: AppTheme.accent.withValues(alpha: 0.5),
                                  borderRadius: BorderRadius.circular(3),
                                ),
                              ),
                            ),
                            Container(
                              height: 12,
                              width: 12,
                              decoration: const BoxDecoration(
                                color: AppTheme.textPrimary,
                                shape: BoxShape.circle,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    Text(
                      '\$${plan.expectedMove!.confidenceIntervalHigh.toStringAsFixed(2)}',
                      style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.buy),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('-${plan.expectedMove!.expectedDownsidePct}% Expected Downside', style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                    Text('+${plan.expectedMove!.expectedUpsidePct}% Expected Upside', style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                  ],
                ),
              ],
              const SizedBox(height: 14),
              const Text('Probability Distribution', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              const SizedBox(height: 8),
              _buildProbabilityBar(plan.bullishProbability, plan.bearishProbability, plan.neutralProbability),
            ],
          ),
        ),
        const SizedBox(height: 14),

        // Buy Zone Card
        GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.arrow_circle_right_outlined, color: AppTheme.buy),
                  const SizedBox(width: 8),
                  Text('Ideal Buy Entry Zone', style: Theme.of(context).textTheme.titleMedium),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('BUY ZONE RANGE', style: TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                      Text('\$${plan.suggestedEntryLow.toStringAsFixed(2)} – \$${plan.suggestedEntryHigh.toStringAsFixed(2)}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    ],
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      const Text('ENTRY STRATEGY', style: TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                      Text(plan.entryType, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: AppTheme.accent)),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.03),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  'Actionable Timing: ${plan.entryTiming}',
                  style: const TextStyle(fontSize: 12),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),

        // Risk parameters and sizing
        Row(
          children: [
            Expanded(
              child: GlassCard(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('STOP LOSS', style: TextStyle(fontSize: 11, color: AppTheme.sell, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text('\$${plan.stopLoss.toStringAsFixed(2)}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 2),
                    Text('${((1.0 - plan.stopLoss / plan.suggestedEntryPrice) * 100).toStringAsFixed(1)}% protective space', style: const TextStyle(fontSize: 10, color: AppTheme.textSecondary)),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: GlassCard(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('PORTFOLIO RISK', style: TextStyle(fontSize: 11, color: AppTheme.hold, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text('${plan.maxSuggestedRiskPct.toStringAsFixed(1)}%', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 2),
                    const Text('Max suggested allocation', style: TextStyle(fontSize: 10, color: AppTheme.textSecondary)),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: GlassCard(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('RISK / REWARD', style: TextStyle(fontSize: 11, color: AppTheme.buy, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text('1 : ${plan.riskRewardRatio.toStringAsFixed(1)}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 2),
                    const Text('Asymmetric ratio', style: TextStyle(fontSize: 10, color: AppTheme.textSecondary)),
                  ],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),

        // Target Ladder (take profit targets)
        const SectionHeader(title: 'Probabilistic Exits'),
        for (int i = 0; i < plan.targets.length; i++) ...[
          _buildTargetLadderRow(context, plan.targets[i], i + 1, plan.suggestedEntryPrice),
          const SizedBox(height: 8),
        ],

        const SizedBox(height: 12),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Hold Window: ${plan.expectedHoldMinDays}–${plan.expectedHoldMaxDays} trading days', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
            Text('Execution: ${plan.suggestedExecution}', style: const TextStyle(color: AppTheme.accent, fontWeight: FontWeight.bold, fontSize: 12)),
          ],
        ),
      ],
    );
  }

  Widget _buildReasoningTab(BuildContext context, SignalModel signal, TradePlanModel plan) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
      children: [
        const SectionHeader(title: 'Multi-Timeframe Trend Matrix'),
        GlassCard(
          child: Column(
            children: [
              _buildTimeframeRow('WEEKLY TREND', plan.weeklyBias),
              const Divider(color: Colors.white12, height: 16),
              _buildTimeframeRow('DAILY TREND', plan.dailyBias),
              const Divider(color: Colors.white12, height: 16),
              _buildTimeframeRow('INTRADAY MOMENTUM', plan.intradayBias),
              if (plan.weeklyBias == 'Bearish' && plan.dailyBias == 'Bullish') ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppTheme.sell.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: AppTheme.sell.withValues(alpha: 0.35)),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.warning, color: AppTheme.sell, size: 18),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'MACRO TREND WARNING: Prevent long trades against weekly macro bear trend. Consider smaller size.',
                          style: TextStyle(color: AppTheme.sell, fontSize: 11, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 16),

        const SectionHeader(title: 'AI Contributing Explanations'),
        EntitlementGate(
          minimum: AccessLevel.elite,
          child: GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (plan.reasoning.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 12.0),
                    child: Text('Consensus models are stable. Trade fits standard regime parameters.'),
                  )
                else
                  for (final item in plan.reasoning) ...[
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6.0),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            _factorIcon(item.factorType),
                            color: _factorColor(item.factorType),
                            size: 18,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              item.factorText,
                              style: const TextStyle(fontSize: 13),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 6),
                  ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildLifecycleTab(BuildContext context, SignalModel signal, TradePlanModel plan) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 16, 16, 28),
      children: [
        const Text(
          'Trade Lifecycle Pipeline',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 4),
        const Text(
          'Realtime monitoring of entry trigger points and exit ladders.',
          style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
        ),
        const SizedBox(height: 24),

        // Vertical Stepper
        _buildStepRow(
          context,
          title: 'Signal Emitted & Calibrated',
          desc: 'Meta-model generated consensus signal at ${plan.createdAt.shortDateTime}. Calibrated bullish probability is ${(plan.bullishProbability * 100).toStringAsFixed(0)}%.',
          isCompleted: true,
          isFirst: true,
        ),
        _buildStepRow(
          context,
          title: 'Ideal Buy Zone Active',
          desc: 'Optimal price entry window [${plan.suggestedEntryLow.toStringAsFixed(2)} - ${plan.suggestedEntryHigh.toStringAsFixed(2)}]. Suggested order type is ${plan.suggestedExecution.toLowerCase()}.',
          isCompleted: plan.currentPrice <= plan.suggestedEntryHigh,
        ),
        _buildStepRow(
          context,
          title: 'Protective Stop-Loss & Risk Caps Active',
          desc: 'Dynamic risk protection placed at \$${plan.stopLoss.toStringAsFixed(2)}. Suggested maximum capital risk: ${plan.maxSuggestedRiskPct}%.',
          isCompleted: true,
        ),
        _buildStepRow(
          context,
          title: 'Exits & Exit Target Ladders Triggered',
          desc: plan.targets.isNotEmpty
              ? 'Monitoring take-profit steps. TP1 target set at \$${plan.targets[0].price.toStringAsFixed(2)} with ${(plan.targets[0].probability * 100).toStringAsFixed(0)}% theoretical capture likelihood.'
              : 'Monitoring take-profit steps. Exit targets will activate once ideal entry zone is filled.',
          isCompleted: false,
          isLast: true,
        ),
      ],
    );
  }

  Widget _buildProbabilityBar(double bull, double bear, double neutral) {
    return Column(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: SizedBox(
            height: 10,
            width: double.infinity,
            child: Row(
              children: [
                Expanded(
                  flex: (bull * 100).round(),
                  child: Container(color: AppTheme.buy),
                ),
                Expanded(
                  flex: (neutral * 100).round(),
                  child: Container(color: AppTheme.hold),
                ),
                Expanded(
                  flex: (bear * 100).round(),
                  child: Container(color: AppTheme.sell),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 6),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Bullish ${(bull * 100).toStringAsFixed(0)}%', style: const TextStyle(fontSize: 10, color: AppTheme.buy, fontWeight: FontWeight.bold)),
            Text('Neutral ${(neutral * 100).toStringAsFixed(0)}%', style: const TextStyle(fontSize: 10, color: AppTheme.hold, fontWeight: FontWeight.bold)),
            Text('Bearish ${(bear * 100).toStringAsFixed(0)}%', style: const TextStyle(fontSize: 10, color: AppTheme.sell, fontWeight: FontWeight.bold)),
          ],
        ),
      ],
    );
  }

  Widget _buildTargetLadderRow(BuildContext context, TradeTargetModel target, int index, double entryPrice) {
    final upsidePct = ((target.price / entryPrice - 1.0) * 100);
    return GlassCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: Row(
        children: [
          CircleAvatar(
            radius: 12,
            backgroundColor: AppTheme.buy.withValues(alpha: 0.12),
            child: Text(
              '$index',
              style: const TextStyle(color: AppTheme.buy, fontSize: 11, fontWeight: FontWeight.bold),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      target.targetLabel,
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                    ),
                    Text(
                      '\$${target.price.toStringAsFixed(2)}',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.buy),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '+${upsidePct.toStringAsFixed(1)}% profit potential',
                      style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                    ),
                    Text(
                      'Capture Probability: ${(target.probability * 100).toStringAsFixed(0)}%',
                      style: TextStyle(
                        fontSize: 11,
                        color: _probColor(target.probability),
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimeframeRow(String title, String bias) {
    final Color color;
    if (bias == 'Bullish') {
      color = AppTheme.buy;
    } else if (bias == 'Bearish') {
      color = AppTheme.sell;
    } else {
      color = AppTheme.hold;
    }
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(title, style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
        Row(
          children: [
            Container(
              height: 8,
              width: 8,
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            ),
            const SizedBox(width: 6),
            Text(
              bias.toUpperCase(),
              style: TextStyle(fontWeight: FontWeight.bold, color: color, fontSize: 12),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildStepRow(
    BuildContext context, {
    required String title,
    required String desc,
    required bool isCompleted,
    bool isFirst = false,
    bool isLast = false,
  }) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            children: [
              Container(
                height: 18,
                width: 18,
                decoration: BoxDecoration(
                  color: isCompleted ? AppTheme.buy : Colors.transparent,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: isCompleted ? AppTheme.buy : Colors.white24,
                    width: 2,
                  ),
                ),
                child: isCompleted
                    ? const Icon(Icons.check, size: 10, color: Colors.black)
                    : null,
              ),
              if (!isLast)
                Expanded(
                  child: Container(
                    width: 2,
                    color: isCompleted ? AppTheme.buy.withValues(alpha: 0.5) : Colors.white10,
                  ),
                ),
            ],
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                      color: isCompleted ? AppTheme.textPrimary : AppTheme.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    desc,
                    style: const TextStyle(
                      color: AppTheme.textSecondary,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _confidenceColor(String level) {
    switch (level.toUpperCase()) {
      case 'HIGH':
        return AppTheme.buy;
      case 'MEDIUM':
        return AppTheme.hold;
      default:
        return AppTheme.sell;
    }
  }

  Color _probColor(double val) {
    if (val >= 0.70) return AppTheme.buy;
    if (val >= 0.45) return AppTheme.hold;
    return AppTheme.textSecondary;
  }

  IconData _factorIcon(String type) {
    switch (type.toLowerCase()) {
      case 'regime':
        return Icons.layers_outlined;
      case 'momentum':
        return Icons.speed_outlined;
      case 'volume':
        return Icons.bar_chart_outlined;
      case 'volatility':
        return Icons.waves_outlined;
      case 'meta_model':
        return Icons.auto_awesome_outlined;
      default:
        return Icons.info_outline;
    }
  }

  Color _factorColor(String type) {
    switch (type.toLowerCase()) {
      case 'regime':
        return AppTheme.purple;
      case 'momentum':
        return AppTheme.buy;
      case 'volume':
        return AppTheme.hold;
      case 'volatility':
        return AppTheme.sell;
      case 'meta_model':
        return AppTheme.accent;
      default:
        return AppTheme.textSecondary;
    }
  }
}
