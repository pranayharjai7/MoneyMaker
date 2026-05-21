import 'package:intl/intl.dart';

extension MoneyMakerNumberFormat on num {
  String asPercent({int digits = 0}) {
    final formatter = NumberFormat.percentPattern()
      ..minimumFractionDigits = digits
      ..maximumFractionDigits = digits;
    return formatter.format(this);
  }

  String asSignedPercent({int digits = 1}) {
    final value = this >= 0 ? '+${asPercent(digits: digits)}' : asPercent(digits: digits);
    return value;
  }

  String asMoney({String symbol = r'$'}) {
    return NumberFormat.currency(symbol: symbol, decimalDigits: 2).format(this);
  }
}

extension MoneyMakerDateFormat on DateTime {
  String get shortDateTime => DateFormat('MMM d, HH:mm').format(toLocal());
}
