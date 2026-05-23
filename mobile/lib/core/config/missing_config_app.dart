import 'package:flutter/material.dart';

/// Shown when required `--dart-define` values are missing or Supabase fails to start.
class MissingConfigApp extends StatelessWidget {
  const MissingConfigApp({super.key, this.message});

  final String? message;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(),
      home: Scaffold(
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: SelectableText(
              message ??
                  'Missing Supabase configuration.\n\n'
                  'Run the app with:\n'
                  '  --dart-define=SUPABASE_URL=https://<project>.supabase.co\n'
                  '  --dart-define=SUPABASE_ANON_KEY=<anon-key>\n\n'
                  'If Windows fails with "log reader stopped unexpectedly", run:\n'
                  '  flutter clean\n'
                  '  flutter pub get\n'
                  '  flutter run -d windows',
              style: const TextStyle(fontSize: 15, height: 1.5),
            ),
          ),
        ),
      ),
    );
  }
}
