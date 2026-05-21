import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class AuthRepository {
  const AuthRepository(this._client);

  static const oauthRedirectUrl = 'com.moneymaker.mobile://login-callback/';
  static const desktopOAuthRedirectHost = '127.0.0.1';
  static const desktopOAuthRedirectPort = 54321;
  static const desktopOAuthRedirectPath = '/login-callback';

  final SupabaseClient _client;

  Stream<AuthState> get authStateChanges => _client.auth.onAuthStateChange;
  Session? get currentSession => _client.auth.currentSession;
  User? get currentUser => _client.auth.currentUser;

  Future<AuthResponse> signIn({
    required String email,
    required String password,
  }) {
    return _client.auth.signInWithPassword(email: email, password: password);
  }

  Future<AuthResponse> signUp({
    required String email,
    required String password,
  }) {
    return _client.auth.signUp(email: email, password: password);
  }

  Future<bool> signInWithGoogle() {
    return _signInWithOAuth(
      OAuthProvider.google,
      queryParams: const {
        'access_type': 'offline',
        'prompt': 'consent',
      },
    );
  }

  Future<bool> signInWithApple() {
    return _signInWithOAuth(OAuthProvider.apple);
  }

  Future<void> signOut() => _client.auth.signOut();

  Future<bool> _signInWithOAuth(
    OAuthProvider provider, {
    Map<String, String>? queryParams,
  }) {
    if (_isDesktop) {
      return _signInWithOAuthOnDesktop(
        provider,
        queryParams: queryParams,
      );
    }

    return _client.auth.signInWithOAuth(
      provider,
      redirectTo: oauthRedirectUrl,
      queryParams: queryParams,
    );
  }

  Future<bool> _signInWithOAuthOnDesktop(
    OAuthProvider provider, {
    Map<String, String>? queryParams,
  }) async {
    final server = await HttpServer.bind(
      InternetAddress.loopbackIPv4,
      desktopOAuthRedirectPort,
      shared: true,
    );
    final redirectTo =
        'http://$desktopOAuthRedirectHost:${server.port}$desktopOAuthRedirectPath';

    try {
      final launched = await _client.auth.signInWithOAuth(
        provider,
        redirectTo: redirectTo,
        queryParams: queryParams,
      );
      if (!launched) {
        return false;
      }

      final request = await server.first.timeout(const Duration(minutes: 5));
      final code = request.uri.queryParameters['code'];
      final error = request.uri.queryParameters['error_description'] ??
          request.uri.queryParameters['error'];

      request.response.headers.contentType = ContentType.html;
      if (code == null || code.isEmpty) {
        request.response.write(
          _desktopCallbackHtml(
            title: 'Login failed',
            body: error ?? 'No authorization code was returned.',
          ),
        );
        await request.response.close();
        throw AuthException(error ?? 'No authorization code was returned.');
      }

      request.response.write(
        _desktopCallbackHtml(
          title: 'Login complete',
          body: 'You can return to MoneyMaker AI.',
        ),
      );
      await request.response.close();
      await _client.auth.exchangeCodeForSession(code);
      return true;
    } on TimeoutException {
      throw const AuthException('Login timed out. Please try again.');
    } finally {
      await server.close(force: true);
    }
  }

  bool get _isDesktop {
    return !kIsWeb &&
        (defaultTargetPlatform == TargetPlatform.windows ||
            defaultTargetPlatform == TargetPlatform.macOS ||
            defaultTargetPlatform == TargetPlatform.linux);
  }

  String _desktopCallbackHtml({
    required String title,
    required String body,
  }) {
    return '''
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>$title</title>
    <style>
      body {
        background: #080b10;
        color: #f4f7fb;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        display: grid;
        min-height: 100vh;
        place-items: center;
        margin: 0;
      }
      main {
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 8px;
        padding: 28px;
        max-width: 420px;
        background: #111722;
      }
      h1 { margin: 0 0 8px; font-size: 24px; }
      p { margin: 0; color: #aeb8c8; }
    </style>
  </head>
  <body>
    <main>
      <h1>$title</h1>
      <p>$body</p>
    </main>
  </body>
</html>
''';
  }
}
