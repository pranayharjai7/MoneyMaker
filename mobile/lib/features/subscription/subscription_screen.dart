import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:purchases_flutter/purchases_flutter.dart';

import '../../core/theme/app_theme.dart';
import '../../domain/entities/access_level.dart';
import '../../presentation/providers/subscription_controller.dart';
import '../../presentation/providers/trading_providers.dart';
import '../../presentation/widgets/section_header.dart';

class SubscriptionScreen extends ConsumerWidget {
  const SubscriptionScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final entitlement = ref.watch(entitlementProvider).valueOrNull;
    final offerings = ref.watch(offeringsProvider);
    final controller = ref.watch(subscriptionControllerProvider);

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
      children: [
        Text('Subscription', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 8),
        GlassCard(
          child: Row(
            children: [
              const Icon(Icons.verified, color: AppTheme.accent),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      entitlement?.accessLevel.label ?? 'Free',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    Text(
                      entitlement?.isActive ?? true ? 'Entitlement active' : 'Entitlement expired',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              TextButton(
                onPressed: controller.isLoading ? null : ref.read(subscriptionControllerProvider.notifier).restore,
                child: const Text('Restore'),
              ),
            ],
          ),
        ),
        if (controller.hasError) ...[
          const SizedBox(height: 10),
          Text(
            controller.error.toString(),
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.sell),
          ),
        ],
        const SectionHeader(title: 'Plans'),
        _PlanCard(
          level: AccessLevel.free,
          price: r'$0',
          active: entitlement?.accessLevel == AccessLevel.free || entitlement == null,
          features: const [
            'Delayed signals',
            'Limited watchlist',
            'Basic market regime',
          ],
        ),
        offerings.when(
          loading: () => const GlassCard(
            margin: EdgeInsets.only(bottom: 12),
            child: LinearProgressIndicator(),
          ),
          error: (error, stackTrace) => Column(
            children: [
              _PlanCard(
                level: AccessLevel.pro,
                price: 'RevenueCat Pro',
                active: entitlement?.accessLevel == AccessLevel.pro,
                features: const [
                  'Real-time signals',
                  'AI alerts',
                  'Portfolio insights',
                ],
              ),
              _PlanCard(
                level: AccessLevel.elite,
                price: 'RevenueCat Elite',
                active: entitlement?.accessLevel == AccessLevel.elite,
                features: const [
                  'Full AI engine',
                  'Explainability',
                  'Premium signal stream',
                ],
              ),
            ],
          ),
          data: (value) {
            final packages = value?.current?.availablePackages ?? const <Package>[];
            final proPackage = _packageFor(packages, 'pro');
            final elitePackage = _packageFor(packages, 'elite');
            return Column(
              children: [
                _PlanCard(
                  level: AccessLevel.pro,
                  price: proPackage?.storeProduct.priceString ?? 'Pro',
                  active: entitlement?.accessLevel == AccessLevel.pro,
                  package: proPackage,
                  isLoading: controller.isLoading,
                  features: const [
                    'Real-time signals',
                    'AI alerts',
                    'Portfolio insights',
                  ],
                  onPurchase: proPackage == null
                      ? null
                      : () => ref.read(subscriptionControllerProvider.notifier).purchase(proPackage),
                ),
                _PlanCard(
                  level: AccessLevel.elite,
                  price: elitePackage?.storeProduct.priceString ?? 'Elite',
                  active: entitlement?.accessLevel == AccessLevel.elite,
                  package: elitePackage,
                  isLoading: controller.isLoading,
                  features: const [
                    'Full AI engine',
                    'Explainability',
                    'Premium signal stream',
                  ],
                  onPurchase: elitePackage == null
                      ? null
                      : () => ref.read(subscriptionControllerProvider.notifier).purchase(elitePackage),
                ),
              ],
            );
          },
        ),
        const SectionHeader(title: 'Access control'),
        const GlassCard(
          child: Text(
            'Entitlements are validated server-side from RevenueCat webhooks and mirrored into Supabase for RLS-safe product access.',
          ),
        ),
      ],
    );
  }

  Package? _packageFor(List<Package> packages, String entitlement) {
    for (final package in packages) {
      final id = '${package.identifier} ${package.storeProduct.identifier}'.toLowerCase();
      if (id.contains(entitlement)) {
        return package;
      }
    }
    return null;
  }
}

class _PlanCard extends StatelessWidget {
  const _PlanCard({
    required this.level,
    required this.price,
    required this.active,
    required this.features,
    this.package,
    this.onPurchase,
    this.isLoading = false,
  });

  final AccessLevel level;
  final String price;
  final bool active;
  final List<String> features;
  final Package? package;
  final VoidCallback? onPurchase;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    final color = switch (level) {
      AccessLevel.free => AppTheme.textSecondary,
      AccessLevel.pro => AppTheme.accent,
      AccessLevel.elite => AppTheme.elite,
    };
    return GlassCard(
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
                    Text(level.label, style: Theme.of(context).textTheme.titleLarge?.copyWith(color: color)),
                    Text(price, style: Theme.of(context).textTheme.bodyMedium),
                  ],
                ),
              ),
              if (active)
                Chip(
                  label: const Text('Active'),
                  backgroundColor: AppTheme.buy.withValues(alpha: 0.16),
                  side: BorderSide(color: AppTheme.buy.withValues(alpha: 0.5)),
                )
              else if (level != AccessLevel.free)
                FilledButton(
                  onPressed: isLoading ? null : onPurchase,
                  child: Text(package == null ? 'Configure' : 'Upgrade'),
                ),
            ],
          ),
          const SizedBox(height: 12),
          for (final feature in features)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  Icon(Icons.check_circle, size: 17, color: color),
                  const SizedBox(width: 10),
                  Expanded(child: Text(feature)),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
