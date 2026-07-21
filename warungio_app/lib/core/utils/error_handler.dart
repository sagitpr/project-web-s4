import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// Represents a user-friendly error message.
class AppError {
  final String message;
  final String? technicalDetail;
  final int? statusCode;

  const AppError({
    required this.message,
    this.technicalDetail,
    this.statusCode,
  });

  @override
  String toString() => 'AppError: $message (${statusCode ?? "unknown"})';
}

/// Centralized error handler that translates various exception types
/// into user-friendly error messages.
class ErrorHandler {
  /// Translates an exception into a user-friendly AppError.
  static AppError handle(dynamic error) {
    // Dio network errors
    if (error is DioException) {
      return _handleDioError(error);
    }

    // General exceptions
    if (error is Exception) {
      return AppError(
        message: 'Terjadi kesalahan yang tidak terduga.',
        technicalDetail: kDebugMode ? error.toString() : null,
      );
    }

    return AppError(
      message: 'Terjadi kesalahan.',
      technicalDetail: kDebugMode ? error.toString() : null,
    );
  }

  static AppError _handleDioError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return const AppError(
          message: 'Koneksi terputus. Periksa koneksi internet Anda.',
          statusCode: 0,
        );

      case DioExceptionType.badResponse:
        return _handleStatusCode(error.response);

      case DioExceptionType.cancel:
        return const AppError(
          message: 'Permintaan dibatalkan.',
          statusCode: 0,
        );

      case DioExceptionType.connectionError:
        return const AppError(
          message: 'Tidak dapat terhubung ke server. Periksa koneksi internet Anda.',
          statusCode: 0,
        );

      default:
        return AppError(
          message: 'Kesalahan jaringan.',
          technicalDetail: kDebugMode ? error.message : null,
        );
    }
  }

  static AppError _handleStatusCode(Response? response) {
    if (response == null) {
      return const AppError(message: 'Tidak ada respons dari server.', statusCode: 0);
    }

    final statusCode = response.statusCode ?? 0;
    final data = response.data;
    String? serverMessage;

    // Try to extract message from various API response formats
    if (data is Map<String, dynamic>) {
      serverMessage = (data['message'] as String?) ??
          (data['detail'] as String?) ??
          (data['error'] as String?);
    }

    switch (statusCode) {
      case 400:
        return AppError(
          message: serverMessage ?? 'Data yang dikirim tidak valid.',
          statusCode: statusCode,
        );
      case 401:
        return AppError(
          message: serverMessage ?? 'Sesi telah berakhir. Silakan login kembali.',
          statusCode: statusCode,
        );
      case 403:
        return AppError(
          message: serverMessage ?? 'Anda tidak memiliki izin untuk mengakses ini.',
          statusCode: statusCode,
        );
      case 404:
        return AppError(
          message: serverMessage ?? 'Data tidak ditemukan.',
          statusCode: statusCode,
        );
      case 429:
        return AppError(
          message: 'Terlalu banyak permintaan. Silakan tunggu beberapa saat.',
          statusCode: statusCode,
        );
      case 500:
        return AppError(
          message: serverMessage ?? 'Terjadi kesalahan pada server. Silakan coba lagi.',
          statusCode: statusCode,
        );
      default:
        return AppError(
          message: serverMessage ?? 'Terjadi kesalahan (${statusCode}).',
          statusCode: statusCode,
        );
    }
  }
}
