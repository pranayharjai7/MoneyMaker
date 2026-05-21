import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import '../providers/auth_controller.dart';

class MainShell extends ConsumerWidget {
  const MainShell({
    required this.child,
    super.key,
  });

  final Widget child;

  static const _tabs = [
    _TabItem('/dashboard', Icons.dashboard_outlined, 'Home'),
    _TabItem('/signals', Icons.show_chart, 'Signals'),
    _TabItem('/portfolio', Icons.account_balance_wallet_outlined, 'Portfolio'),
    _TabItem('/watchlist', Icons.visibility_outlined, 'Watchlist'),
    _TabItem('/insights', Icons.auto_graph_outlined, 'Insights'),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final location = GoRouterState.of(context).uri.toString();
    final index = _tabs.indexWhere((tab) => location.startsWith(tab.path));
    return Scaffold(
      appBar: AppBar(
        backgroundColor: AppTheme.background.withValues(alpha: 0.96),
        title: const Text('MoneyMaker AI'),
        actions: [
          IconButton(
            tooltip: 'Alerts',
            onPressed: () => context.go('/alerts'),
            icon: const Icon(Icons.notifications_none),
          ),
          IconButton(
            tooltip: 'Subscription',
            onPressed: () => context.go('/subscription'),
            icon: const Icon(Icons.workspace_premium_outlined),
          ),
          IconButton(
            tooltip: 'Sign out',
            onPressed: () => ref.read(authControllerProvider.notifier).signOut(),
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: Stack(
        children: [
          const _Background(),
          SafeArea(child: child),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index < 0 ? 0 : index,
        onDestinationSelected: (selected) => context.go(_tabs[selected].path),
        destinations: [
          for (final tab in _tabs)
            NavigationDestination(
              icon: Icon(tab.icon),
              label: tab.label,
            ),
        ],
      ),
    );
  }
}

class _Background extends StatelessWidget {
  const _Background();

  @override
  Widget build(BuildContext context) {
    return const DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF080B10),
            Color(0xFF0B1312),
            Color(0xFF10131B),
          ],
        ),
      ),
      child: SizedBox.expand(),
    );
  }
}

class _TabItem {
  const _TabItem(this.path, this.icon, this.label);

  final String path;
  final IconData icon;
  final String label;
}
