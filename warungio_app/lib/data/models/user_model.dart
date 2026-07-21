class UserModel {
  final int id;
  final String email;
  final String fullName;
  final String? phone;
  final String role;
  final String? address;
  final String? profilePhoto;
  final String? bio;
  final bool isVerified;
  final double walletBalance;
  final DateTime? createdAt;

  UserModel({
    required this.id,
    required this.email,
    required this.fullName,
    this.phone,
    required this.role,
    this.address,
    this.profilePhoto,
    this.bio,
    this.isVerified = false,
    this.walletBalance = 0.0,
    this.createdAt,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] as int,
      email: json['email'] as String? ?? '',
      fullName: json['full_name'] as String? ?? '',
      phone: json['phone'] as String?,
      role: json['role'] as String? ?? 'buyer',
      address: json['address'] as String?,
      profilePhoto: json['profile_photo'] as String?,
      bio: json['bio'] as String?,
      isVerified: json['is_verified'] as bool? ?? false,
      walletBalance: (json['wallet_balance'] as num?)?.toDouble() ?? 0.0,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'full_name': fullName,
      'phone': phone,
      'role': role,
      'address': address,
      'profile_photo': profilePhoto,
      'bio': bio,
      'is_verified': isVerified,
      'wallet_balance': walletBalance,
    };
  }

  bool get isSeller => role == 'seller';
  bool get isBuyer => role == 'buyer';
  bool get isAdmin => role == 'admin';
}
