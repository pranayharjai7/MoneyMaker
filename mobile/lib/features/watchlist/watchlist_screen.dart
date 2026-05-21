import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/extensions/formatters.dart';
import '../../core/theme/app_theme.dart';
import '../../presentation/providers/app_providers.dart';
import '../../presentation/providers/trading_providers.dart';
import '../../presentation/widgets/section_header.dart';

class WatchlistScreen extends ConsumerStatefulWidget {
  const WatchlistScreen({super.key});

  @override
  ConsumerState<WatchlistScreen> createState() => _WatchlistScreenState();
}

class _WatchlistScreenState extends ConsumerState<WatchlistScreen> {
  final _tickerController = TextEditingController();
  bool _adding = false;

  @override
  void dispose() {
    _tickerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final watchlistState = ref.watch(watchlistProvider);
    final entitlement = ref.watch(entitlementProvider).valueOrNull;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
      children: [
        Text('Watchlist', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 12),
        GlassCard(
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _tickerController,
                  textCapitalization: TextCapitalization.characters,
                  decoration: const InputDecoration(
                    labelText: 'Ticker',
                    prefixIcon: Icon(Icons.search),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              IconButton.filled(
                tooltip: 'Add',
                onPressed: _adding ? null : _addTicker,
                icon: _adding
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.add),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Limit ${entitlement?.accessLevel.watchlistLimit ?? 5} symbols',
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        const SectionHeader(title: 'Live probabilities'),
        watchlistState.when(
          loading: () => const GlassCard(child: LinearProgressIndicator()),
          error: (error, stackTrace) => GlassCard(child: Text(error.toString())),
          data: (items) {
            if (items.isEmpty) {
              return const GlassCard(child: Text('Add a ticker to start tracking live probabilities.'));
            }
            return Column(
              children: [
                for (final item in items)
                  GlassCard(
                    margin: const EdgeInsets.only(bottom: 10),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(item.ticker, style: Theme.of(context).textTheme.titleLarge),
                              Text(
                                item.stock?.companyName ?? item.stockId,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                            ],
                          ),
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(
                              item.latestProbability?.asPercent(digits: 0) ?? '--',
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppTheme.accent),
                            ),
                            Switch.adaptive(
                              value: item.alertsEnabled,
                              onChanged: (enabled) async {
                                await ref.read(tradingRepositoryProvider).setWatchlistAlertEnabled(
                                      stockId: item.stockId,
                                      enabled: enabled,
                                    );
                                ref.invalidate(watchlistProvider);
                              },
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
    );
  }

  Future<void> _addTicker() async {
    final ticker = _tickerController.text.trim();
    if (ticker.isEmpty) {
      return;
    }
    setState(() => _adding = true);
    try {
      await ref.read(tradingRepositoryProvider).addToWatchlist(ticker);
      _tickerController.clear();
      ref.invalidate(watchlistProvider);
    } finally {
      if (mounted) {
        setState(() => _adding = false);
      }
    }
  }
}
