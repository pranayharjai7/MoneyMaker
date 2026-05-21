import 'package:hive_flutter/hive_flutter.dart';

class CacheService {
  static const _boxName = 'moneymaker_cache';

  Box<dynamic>? _box;

  Future<void> init() async {
    _box = Hive.isBoxOpen(_boxName) ? Hive.box<dynamic>(_boxName) : await Hive.openBox<dynamic>(_boxName);
  }

  Future<Box<dynamic>> _ensureBox() async {
    if (_box == null || !_box!.isOpen) {
      await init();
    }
    return _box!;
  }

  Future<List<Map<String, dynamic>>> readList(String key) async {
    final box = await _ensureBox();
    final value = box.get(key);
    if (value is! List) {
      return const [];
    }
    return value
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList(growable: false);
  }

  Future<Map<String, dynamic>?> readMap(String key) async {
    final box = await _ensureBox();
    final value = box.get(key);
    if (value is Map) {
      return Map<String, dynamic>.from(value);
    }
    return null;
  }

  Future<void> writeList(String key, List<Map<String, dynamic>> rows) async {
    final box = await _ensureBox();
    await box.put(key, rows);
  }

  Future<void> writeMap(String key, Map<String, dynamic> value) async {
    final box = await _ensureBox();
    await box.put(key, value);
  }
}
