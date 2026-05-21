import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import '../../domain/entities/access_level.dart';
import '../providers/trading_providers.dart';

class EntitlementGate extends ConsumerWidget {
  const EntitlementGate({
    required this.minimum,
    required this.child,
    super.key,
    this.compact = false,
  });

  final AccessLevel minimum;
  final Widget child;
  final bool compact;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final entitlement = ref.watch(entitlementProvider).valueOrNull;
    final current = entitlement?.accessLevel ?? AccessLevel.free;
    final allowed = current.index >= minimum.index && (entitlement?.isActive ?? true);
    if (allowed) {
      return child;
    }
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '${minimum.label} required',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          if (!compact) ...[
            const SizedBox(height: 8),
            Text(
              'Upgrade to unlock this layer of the AI engine.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
          const SizedBox(height: 12),
          FilledButton(
            onPressed: () => context.go('/subscription'),
            child: const Text('View plans'),
          ),
        ],
      ),
    );
  }
}
