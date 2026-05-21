import 'dart:async';
import 'dart:convert';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/config/app_config.dart';
import '../../firebase_options.dart';

@pragma('vm:entry-point')
Future<void> moneyMakerFirebaseMessagingBackgroundHandler(RemoteMessage message) async {
  try {
    if (Firebase.apps.isEmpty) {
      await Firebase.initializeApp(
        options: DefaultFirebaseOptions.currentPlatform,
      );
    }
  } catch (_) {
    // Background push handling should never prevent the app from opening.
  }
}

class NotificationPayload {
  const NotificationPayload({
    required this.title,
    required this.body,
    required this.data,
  });

  factory NotificationPayload.fromRemoteMessage(RemoteMessage message) {
    return NotificationPayload(
      title: message.notification?.title ?? message.data['title']?.toString() ?? 'MoneyMaker',
      body: message.notification?.body ?? message.data['body']?.toString() ?? '',
      data: message.data.map((key, value) => MapEntry(key, value.toString())),
    );
  }

  factory NotificationPayload.fromMap(Map<String, dynamic> value) {
    return NotificationPayload(
      title: value['title']?.toString() ?? 'MoneyMaker',
      body: value['body']?.toString() ?? '',
      data: Map<String, String>.from((value['data'] as Map?) ?? {}),
    );
  }

  final String title;
  final String body;
  final Map<String, String> data;
}

class NotificationService {
  NotificationService({
    FirebaseMessaging? messaging,
    FlutterLocalNotificationsPlugin? localNotifications,
  })  : _injectedMessaging = messaging,
        _localNotifications = localNotifications ?? FlutterLocalNotificationsPlugin();

  final FirebaseMessaging? _injectedMessaging;
  final FlutterLocalNotificationsPlugin _localNotifications;
  StreamSubscription<AuthState>? _authSubscription;

  static void registerBackgroundHandler() {
    FirebaseMessaging.onBackgroundMessage(moneyMakerFirebaseMessagingBackgroundHandler);
  }

  Future<void> initialize({
    required AppConfig config,
    required SupabaseClient supabase,
  }) async {
    if (kIsWeb ||
        defaultTargetPlatform == TargetPlatform.windows ||
        defaultTargetPlatform == TargetPlatform.linux) {
      return;
    }
    final firebaseReady = await _initializeFirebase(config);
    if (!firebaseReady) {
      return;
    }
    final messaging = _injectedMessaging ?? FirebaseMessaging.instance;
    await _initializeLocalNotifications();
    await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );
    FirebaseMessaging.onMessage.listen((message) {
      showForegroundNotification(NotificationPayload.fromRemoteMessage(message));
    });
    FirebaseMessaging.onMessageOpenedApp.listen((message) {
      // Deep links are routed by payload consumers; this keeps the service side-effect free.
    });
    messaging.onTokenRefresh.listen((token) => _registerToken(supabase, token));
    _authSubscription?.cancel();
    _authSubscription = supabase.auth.onAuthStateChange.listen((event) async {
      if (event.session != null) {
        final token = await messaging.getToken();
        if (token != null) {
          await _registerToken(supabase, token);
        }
      }
    });
    final token = await messaging.getToken();
    if (token != null) {
      await _registerToken(supabase, token);
    }
  }

  Future<void> showForegroundNotification(NotificationPayload payload) async {
    const androidDetails = AndroidNotificationDetails(
      'trading_signals',
      'Trading Signals',
      channelDescription: 'AI trading signals, alerts, and risk changes.',
      importance: Importance.high,
      priority: Priority.high,
    );
    const iosDetails = DarwinNotificationDetails();
    await _localNotifications.show(
      DateTime.now().millisecondsSinceEpoch.remainder(100000),
      payload.title,
      payload.body,
      const NotificationDetails(android: androidDetails, iOS: iosDetails),
      payload: jsonEncode(payload.data),
    );
  }

  Future<void> dispose() async {
    await _authSubscription?.cancel();
  }

  Future<bool> _initializeFirebase(AppConfig config) async {
    try {
      if (Firebase.apps.isNotEmpty) {
        return true;
      }
      if (config.hasFirebaseDartDefines) {
        await Firebase.initializeApp(
          options: FirebaseOptions(
            apiKey: config.firebaseApiKey,
            appId: config.firebaseAppId,
            messagingSenderId: config.firebaseMessagingSenderId,
            projectId: config.firebaseProjectId,
          ),
        );
      } else {
        await Firebase.initializeApp(
          options: DefaultFirebaseOptions.currentPlatform,
        );
      }
      return true;
    } catch (_) {
      // Firebase native config is environment-specific; the app remains usable without push setup.
      return false;
    }
  }

  Future<void> _initializeLocalNotifications() async {
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const ios = DarwinInitializationSettings();
    await _localNotifications.initialize(
      const InitializationSettings(android: android, iOS: ios),
    );
  }

  Future<void> _registerToken(SupabaseClient supabase, String token) async {
    final user = supabase.auth.currentUser;
    if (user == null || token.isEmpty) {
      return;
    }
    await supabase.from('user_devices').upsert(
      {
        'user_id': user.id,
        'platform': _platform,
        'push_token': token,
        'is_active': true,
        'last_seen_at': DateTime.now().toUtc().toIso8601String(),
      },
      onConflict: 'platform,push_token',
    );
  }

  String get _platform {
    return switch (defaultTargetPlatform) {
      TargetPlatform.iOS => 'ios',
      TargetPlatform.android => 'android',
      TargetPlatform.windows => 'windows',
      TargetPlatform.macOS => 'macos',
      TargetPlatform.linux => 'linux',
      _ => 'unknown',
    };
  }
}
