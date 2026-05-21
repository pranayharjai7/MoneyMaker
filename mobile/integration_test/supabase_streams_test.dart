import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('ensemble signals stream can be constructed', (tester) async {
    const url = String.fromEnvironment('SUPABASE_URL');
    const anonKey = String.fromEnvironment('SUPABASE_ANON_KEY');
    if (url.isEmpty || anonKey.isEmpty) {
      return;
    }

    await Supabase.initialize(url: url, anonKey: anonKey);
    final stream = Supabase.instance.client
        .from('ensemble_signals')
        .stream(primaryKey: ['id'])
        .order('timestamp', ascending: false)
        .limit(1);

    expect(stream, isA<Stream<List<Map<String, dynamic>>>>());
  });
}
