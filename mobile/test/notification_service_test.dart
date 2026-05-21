import 'package:flutter_test/flutter_test.dart';
import 'package:moneymaker_mobile/data/services/notification_service.dart';

void main() {
  test('notification payload maps FCM data contract', () {
    final payload = NotificationPayload.fromMap(
      {
        'title': 'BUY NVDA',
        'body': 'Probability: 68%, Expected return: 4.2%',
        'data': {
          'stock_id': 'stock-1',
          'signal_type': 'buy',
        },
      },
    );

    expect(payload.title, 'BUY NVDA');
    expect(payload.body, 'Probability: 68%, Expected return: 4.2%');
    expect(payload.data['stock_id'], 'stock-1');
    expect(payload.data['signal_type'], 'buy');
  });
}
