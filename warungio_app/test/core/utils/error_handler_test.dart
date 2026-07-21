import 'package:flutter_test/flutter_test.dart';
import 'package:dio/dio.dart';
import 'package:warungio_app/core/utils/error_handler.dart';

void main() {
  group('ErrorHandler', () {
    test('handles connection timeout error', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.connectionTimeout,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, contains('Koneksi'));
      expect(appError.statusCode, 0);
    });

    test('handles send timeout error', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.sendTimeout,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, contains('Koneksi'));
    });

    test('handles receive timeout error', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.receiveTimeout,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, contains('Koneksi'));
    });

    test('handles connection error', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.connectionError,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, contains('tidak dapat terhubung'));
    });

    test('handles cancellation error', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.cancel,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, contains('dibatalkan'));
    });

    test('handles 400 Bad Request', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 400,
          data: {'message': 'Data tidak valid'},
        ),
        type: DioExceptionType.badResponse,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, 'Data tidak valid');
      expect(appError.statusCode, 400);
    });

    test('handles 400 with detail field', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 400,
          data: {'detail': 'Invalid input'},
        ),
        type: DioExceptionType.badResponse,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, 'Invalid input');
    });

    test('handles 400 with error field', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 400,
          data: {'error': 'Something went wrong'},
        ),
        type: DioExceptionType.badResponse,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, 'Something went wrong');
    });

    test('handles 401 Unauthorized', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 401,
        ),
        type: DioExceptionType.badResponse,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, contains('login kembali'));
      expect(appError.statusCode, 401);
    });

    test('handles 403 Forbidden', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 403,
        ),
        type: DioExceptionType.badResponse,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, contains('izin'));
    });

    test('handles 404 Not Found', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 404,
        ),
        type: DioExceptionType.badResponse,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, contains('tidak ditemukan'));
    });

    test('handles 429 Too Many Requests', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 429,
        ),
        type: DioExceptionType.badResponse,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, contains('terlalu banyak'));
    });

    test('handles 500 Internal Server Error', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 500,
        ),
        type: DioExceptionType.badResponse,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, contains('server'));
    });

    test('handles null response gracefully', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.badResponse,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, contains('Tidak ada respons'));
    });

    test('handles generic Exception', () {
      final error = Exception('Something broke');
      final appError = ErrorHandler.handle(error);
      expect(appError.message, contains('tidak terduga'));
    });

    test('handles unknown error type', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.unknown,
      );

      final appError = ErrorHandler.handle(error);
      expect(appError.message, isNotEmpty);
    });
  });
}
