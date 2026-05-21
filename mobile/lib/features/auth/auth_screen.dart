import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../presentation/providers/auth_controller.dart';

class AuthScreen extends ConsumerStatefulWidget {
  const AuthScreen({super.key});

  @override
  ConsumerState<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends ConsumerState<AuthScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isSignUp = false;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    return Scaffold(
      body: Stack(
        children: [
          const DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFF08110F),
                  Color(0xFF111722),
                  Color(0xFF0B0D13),
                ],
              ),
            ),
            child: SizedBox.expand(),
          ),
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: GlassCard(
                margin: const EdgeInsets.all(20),
                padding: const EdgeInsets.all(22),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'MoneyMaker AI',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Trading intelligence, streamed live.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 24),
                    TextField(
                      controller: _emailController,
                      keyboardType: TextInputType.emailAddress,
                      decoration: const InputDecoration(labelText: 'Email'),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _passwordController,
                      obscureText: true,
                      decoration: const InputDecoration(labelText: 'Password'),
                    ),
                    const SizedBox(height: 18),
                    FilledButton(
                      onPressed: authState.isLoading ? null : _submit,
                      child: Text(_isSignUp ? 'Create account' : 'Sign in'),
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(child: Divider(color: Colors.white.withValues(alpha: 0.16))),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          child: Text('or', style: Theme.of(context).textTheme.bodyMedium),
                        ),
                        Expanded(child: Divider(color: Colors.white.withValues(alpha: 0.16))),
                      ],
                    ),
                    const SizedBox(height: 14),
                    _SocialSignInButton(
                      icon: Icons.g_mobiledata,
                      label: 'Continue with Google',
                      onPressed: authState.isLoading
                          ? null
                          : ref.read(authControllerProvider.notifier).signInWithGoogle,
                    ),
                    const SizedBox(height: 10),
                    _SocialSignInButton(
                      icon: Icons.apple,
                      label: 'Continue with Apple',
                      onPressed: authState.isLoading
                          ? null
                          : ref.read(authControllerProvider.notifier).signInWithApple,
                    ),
                    TextButton(
                      onPressed: () => setState(() => _isSignUp = !_isSignUp),
                      child: Text(_isSignUp ? 'Use existing account' : 'Create an account'),
                    ),
                    if (authState.hasError) ...[
                      const SizedBox(height: 8),
                      Text(
                        authState.error.toString(),
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.sell),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _submit() async {
    final notifier = ref.read(authControllerProvider.notifier);
    if (_isSignUp) {
      await notifier.signUp(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );
    } else {
      await notifier.signIn(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );
    }
  }
}

class _SocialSignInButton extends StatelessWidget {
  const _SocialSignInButton({
    required this.icon,
    required this.label,
    required this.onPressed,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon, size: 22),
      label: Text(label),
      style: OutlinedButton.styleFrom(
        foregroundColor: AppTheme.textPrimary,
        padding: const EdgeInsets.symmetric(vertical: 14),
        side: BorderSide(color: Colors.white.withValues(alpha: 0.16)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    );
  }
}
