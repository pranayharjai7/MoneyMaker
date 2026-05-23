import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final appConfigProvider = Provider<AppConfig>((_) {
  throw StateError('AppConfig must be provided at startup.');
});

class AppConfig {
  const AppConfig({
    required this.supabaseUrl,
    required this.supabaseAnonKey,
    required this.apiBaseUrl,
    required this.revenueCatAndroidApiKey,
    required this.revenueCatIosApiKey,
    required this.firebaseApiKey,
    required this.firebaseAppId,
    required this.firebaseMessagingSenderId,
    required this.firebaseProjectId,
  });

  factory AppConfig.fromEnvironment() {
    const supabaseUrl = String.fromEnvironment('SUPABASE_URL');
    const supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY');
    const apiBaseUrlDefine = String.fromEnvironment('MONEYMAKER_API_BASE_URL');
    final defaultApiUrl = defaultTargetPlatform == TargetPlatform.android
        ? 'http://10.0.2.2:8000'
        : 'http://localhost:8000';
    final apiBaseUrl = apiBaseUrlDefine.isNotEmpty ? apiBaseUrlDefine : defaultApiUrl;

    return AppConfig(
      supabaseUrl: supabaseUrl,
      supabaseAnonKey: supabaseAnonKey,
      apiBaseUrl: apiBaseUrl,
      revenueCatAndroidApiKey: const String.fromEnvironment(
        'REVENUECAT_ANDROID_API_KEY',
      ),
      revenueCatIosApiKey: const String.fromEnvironment('REVENUECAT_IOS_API_KEY'),
      firebaseApiKey: const String.fromEnvironment('FIREBASE_API_KEY'),
      firebaseAppId: const String.fromEnvironment('FIREBASE_APP_ID'),
      firebaseMessagingSenderId: const String.fromEnvironment(
        'FIREBASE_MESSAGING_SENDER_ID',
      ),
      firebaseProjectId: const String.fromEnvironment('FIREBASE_PROJECT_ID'),
    );
  }

  final String supabaseUrl;
  final String supabaseAnonKey;
  final String apiBaseUrl;
  final String revenueCatAndroidApiKey;
  final String revenueCatIosApiKey;
  final String firebaseApiKey;
  final String firebaseAppId;
  final String firebaseMessagingSenderId;
  final String firebaseProjectId;

  bool get hasFirebaseDartDefines =>
      firebaseApiKey.isNotEmpty &&
      firebaseAppId.isNotEmpty &&
      firebaseMessagingSenderId.isNotEmpty &&
      firebaseProjectId.isNotEmpty;

  bool get hasRevenueCatKeys =>
      revenueCatAndroidApiKey.isNotEmpty || revenueCatIosApiKey.isNotEmpty;

  bool get hasSupabaseConfig =>
      supabaseUrl.isNotEmpty && supabaseAnonKey.isNotEmpty;
}
