/// Model representing a payment method from the backend.
class PaymentMethodModel {
  final int id;
  final String name;
  final String? code;
  final String? type;
  final String? icon;
  final String? description;
  final double? minAmount;
  final double? maxAmount;
  final bool isActive;

  PaymentMethodModel({
    required this.id,
    required this.name,
    this.code,
    this.type,
    this.icon,
    this.description,
    this.minAmount,
    this.maxAmount,
    this.isActive = true,
  });

  factory PaymentMethodModel.fromJson(Map<String, dynamic> json) {
    return PaymentMethodModel(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      code: json['code'] as String?,
      type: json['type'] as String?,
      icon: json['icon'] as String?,
      description: json['description'] as String?,
      minAmount: (json['min_amount'] as num?)?.toDouble(),
      maxAmount: (json['max_amount'] as num?)?.toDouble(),
      isActive: json['is_active'] as bool? ?? true,
    );
  }
}

/// Model representing a payment transaction.
class PaymentModel {
  final int id;
  final int orderId;
  final String? orderIdDisplay;
  final double amount;
  final String? paymentMethod;
  final String? paymentType;
  final String status;
  final String? transactionId;
  final String? snapToken;
  final String? redirectUrl;
  final String? vaNumber;
  final String? billKey;
  final String? billerCode;
  final String? qrCodeUrl;
  final DateTime createdAt;
  final DateTime? paidAt;

  PaymentModel({
    required this.id,
    required this.orderId,
    this.orderIdDisplay,
    required this.amount,
    this.paymentMethod,
    this.paymentType,
    this.status = 'pending',
    this.transactionId,
    this.snapToken,
    this.redirectUrl,
    this.vaNumber,
    this.billKey,
    this.billerCode,
    this.qrCodeUrl,
    required this.createdAt,
    this.paidAt,
  });

  factory PaymentModel.fromJson(Map<String, dynamic> json) {
    return PaymentModel(
      id: json['id'] as int,
      orderId: json['order'] as int? ?? 0,
      orderIdDisplay: json['order_id'] as String?,
      amount: (json['amount'] as num?)?.toDouble() ?? 0.0,
      paymentMethod: json['payment_method'] as String?,
      paymentType: json['payment_type'] as String?,
      status: json['status'] as String? ?? 'pending',
      transactionId: json['transaction_id'] as String?,
      snapToken: json['snap_token'] as String?,
      redirectUrl: json['redirect_url'] as String?,
      vaNumber: json['va_number'] as String?,
      billKey: json['bill_key'] as String?,
      billerCode: json['biller_code'] as String?,
      qrCodeUrl: json['qr_code_url'] as String?,
      createdAt: DateTime.parse(
          json['created_at'] as String? ?? DateTime.now().toIso8601String()),
      paidAt: json['paid_at'] != null
          ? DateTime.tryParse(json['paid_at'] as String)
          : null,
    );
  }
}

/// Model representing the wallet.
class WalletModel {
  final int id;
  final double balance;
  final double? pendingBalance;
  final DateTime? createdAt;

  WalletModel({
    required this.id,
    this.balance = 0.0,
    this.pendingBalance,
    this.createdAt,
  });

  factory WalletModel.fromJson(Map<String, dynamic> json) {
    return WalletModel(
      id: json['id'] as int,
      balance: (json['balance'] as num?)?.toDouble() ?? 0.0,
      pendingBalance: (json['pending_balance'] as num?)?.toDouble(),
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String)
          : null,
    );
  }
}

/// Model representing a wallet transaction.
class WalletTransactionModel {
  final int id;
  final String type;
  final double amount;
  final double balanceBefore;
  final double balanceAfter;
  final String? description;
  final String? reference;
  final String status;
  final DateTime createdAt;

  WalletTransactionModel({
    required this.id,
    required this.type,
    required this.amount,
    required this.balanceBefore,
    required this.balanceAfter,
    this.description,
    this.reference,
    this.status = 'success',
    required this.createdAt,
  });

  factory WalletTransactionModel.fromJson(Map<String, dynamic> json) {
    return WalletTransactionModel(
      id: json['id'] as int,
      type: json['type'] as String? ?? '',
      amount: (json['amount'] as num?)?.toDouble() ?? 0.0,
      balanceBefore: (json['balance_before'] as num?)?.toDouble() ?? 0.0,
      balanceAfter: (json['balance_after'] as num?)?.toDouble() ?? 0.0,
      description: json['description'] as String?,
      reference: json['reference'] as String?,
      status: json['status'] as String? ?? 'success',
      createdAt: DateTime.parse(
          json['created_at'] as String? ?? DateTime.now().toIso8601String()),
    );
  }
}

/// Model for finance summary (seller).
class FinanceSummaryModel {
  final double totalRevenue;
  final double pendingPayout;
  final double availableBalance;
  final int totalTransactions;
  final int pendingTransactions;

  FinanceSummaryModel({
    this.totalRevenue = 0.0,
    this.pendingPayout = 0.0,
    this.availableBalance = 0.0,
    this.totalTransactions = 0,
    this.pendingTransactions = 0,
  });

  factory FinanceSummaryModel.fromJson(Map<String, dynamic> json) {
    return FinanceSummaryModel(
      totalRevenue: (json['total_revenue'] as num?)?.toDouble() ?? 0.0,
      pendingPayout: (json['pending_payout'] as num?)?.toDouble() ?? 0.0,
      availableBalance:
          (json['available_balance'] as num?)?.toDouble() ?? 0.0,
      totalTransactions: json['total_transactions'] as int? ?? 0,
      pendingTransactions: json['pending_transactions'] as int? ?? 0,
    );
  }
}

/// Model for bank account.
class BankAccountModel {
  final int id;
  final String bankName;
  final String accountNumber;
  final String accountHolder;
  final bool isPrimary;
  final bool isVerified;

  BankAccountModel({
    required this.id,
    required this.bankName,
    required this.accountNumber,
    required this.accountHolder,
    this.isPrimary = false,
    this.isVerified = false,
  });

  factory BankAccountModel.fromJson(Map<String, dynamic> json) {
    return BankAccountModel(
      id: json['id'] as int,
      bankName: json['bank_name'] as String? ?? '',
      accountNumber: json['account_number'] as String? ?? '',
      accountHolder: json['account_holder'] as String? ?? '',
      isPrimary: json['is_primary'] as bool? ?? false,
      isVerified: json['is_verified'] as bool? ?? false,
    );
  }
}
