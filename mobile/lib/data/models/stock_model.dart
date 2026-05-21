class StockModel {
  const StockModel({
    required this.id,
    required this.ticker,
    required this.companyName,
    this.sector,
    this.exchange,
  });

  factory StockModel.fromJson(Map<String, dynamic> json) {
    return StockModel(
      id: json['id']?.toString() ?? '',
      ticker: json['ticker']?.toString() ?? '',
      companyName: json['company_name']?.toString() ?? json['ticker']?.toString() ?? '',
      sector: json['sector']?.toString(),
      exchange: json['exchange']?.toString(),
    );
  }

  final String id;
  final String ticker;
  final String companyName;
  final String? sector;
  final String? exchange;

  Map<String, dynamic> toJson() => {
        'id': id,
        'ticker': ticker,
        'company_name': companyName,
        'sector': sector,
        'exchange': exchange,
      };
}
