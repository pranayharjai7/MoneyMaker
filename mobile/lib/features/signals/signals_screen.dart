import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import '../../presentation/providers/trading_providers.dart';
import 'widgets/signal_card.dart';

class SignalsScreen extends ConsumerStatefulWidget {
  const SignalsScreen({super.key});

  @override
  ConsumerState<SignalsScreen> createState() => _SignalsScreenState();
}

class _SignalsScreenState extends ConsumerState<SignalsScreen> {
  String _filter = 'all';

  @override
  Widget build(BuildContext context) {
    final signalsState = ref.watch(signalsProvider);
    final entitlement = ref.watch(entitlementProvider).valueOrNull;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: Row(
            children: [
              Expanded(
                child: Text('Signal Stream', style: Theme.of(context).textTheme.headlineMedium),
              ),
              if (entitlement?.hasRealtimeSignals ?? false)
                const _LiveBadge()
              else
                const _DelayedBadge(),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'all', label: Text('All')),
              ButtonSegment(value: 'buy', label: Text('Buy')),
              ButtonSegment(value: 'sell', label: Text('Sell')),
              ButtonSegment(value: 'neutral', label: Text('Neutral')),
            ],
            selected: {_filter},
            onSelectionChanged: (value) => setState(() => _filter = value.first),
          ),
        ),
        const SizedBox(height: 10),
        Expanded(
          child: signalsState.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, stackTrace) => Center(child: Text(error.toString())),
            data: (signals) {
              final filtered = _filter == 'all'
                  ? signals
                  : signals.where((signal) => signal.signalType == _filter).toList(growable: false);
              if (filtered.isEmpty) {
                return const Center(child: Text('No signals in this view.'));
              }
              return ListView.builder(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 28),
                itemCount: filtered.length,
                itemBuilder: (context, index) {
                  final signal = filtered[index];
                  return SignalCard(
                    signal: signal,
                    onTap: () => context.go('/signals/${signal.id}'),
                  );
                },
              );
            },
          ),
        ),
      ],
    );
  }
}

class _LiveBadge extends StatelessWidget {
  const _LiveBadge();

  @override
  Widget build(BuildContext context) {
    return Chip(
      avatar: const Icon(Icons.bolt, size: 16, color: AppTheme.buy),
      label: const Text('Live'),
      side: BorderSide(color: AppTheme.buy.withValues(alpha: 0.5)),
      backgroundColor: AppTheme.buy.withValues(alpha: 0.12),
    );
  }
}

class _DelayedBadge extends StatelessWidget {
  const _DelayedBadge();

  @override
  Widget build(BuildContext context) {
    return Chip(
      avatar: const Icon(Icons.schedule, size: 16, color: AppTheme.hold),
      label: const Text('Delayed'),
      side: BorderSide(color: AppTheme.hold.withValues(alpha: 0.5)),
      backgroundColor: AppTheme.hold.withValues(alpha: 0.12),
    );
  }
}
