import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';
import '../constants/api_constants.dart';
import '../constants/app_constants.dart';
import '../storage/secure_storage_service.dart';
import '../utils/error_handler.dart';
import '../config/environment.dart'; // environmentProvider (shared singleton)

/// Environment-aware provider that returns the correct base URL.
final baseUrlProvider = Provider<String>((ref) {
  final env = ref.watch(environmentProvider);
  switch (env) {
    case 'production':
      return '${ApiConstants.baseUrlProd}${ApiConstants.apiPrefix}';
    case 'staging':
      return 'https://staging-api.warungio.com${ApiConstants.apiPrefix}';
    default:
      return '${ApiConstants.baseUrlDev}${ApiConstants.apiPrefix}';
  }
});

/// Provider for the raw Dio HTTP client (with interceptors).
/// environmentProvider is defined in main.dart and overridden there.
final dioClientProvider = Provider<Dio>((ref) {
  final secureStorage = ref.watch(secureStorageServiceProvider);
  final baseUrl = ref.watch(baseUrlProvider);
  final client = DioClient(secureStorage, baseUrl);
  return client.dio;
});

/// Provider for ApiClient helper (typed HTTP methods).
final apiClientProvider = Provider<ApiClient>((ref) {
  final dio = ref.watch(dioClientProvider);
  final secureStorage = ref.watch(secureStorageServiceProvider);
  return ApiClient(dio: dio, storage: secureStorage);
});

/// Standardized API response wrapper.
class ApiResponse {
  final bool success;
  final String? message;
  final dynamic data;
  final int? statusCode;

  const ApiResponse({
    required this.success,
    this.message,
    this.data,
    this.statusCode,
  });

  factory ApiResponse.fromJson(Map<String, dynamic> json) {
    return ApiResponse(
      success: json['success'] as bool? ??
          (json['status'] as String? == 'success') ??
          false,
      message: json['message'] as String? ??
          json['detail'] as String? ??
          json['error'] as String?,
      data: json['data'] ?? json,
      statusCode: json['status_code'] as int?,
    );
  }

  factory ApiResponse.error(String message, {int? statusCode, dynamic data}) {
    return ApiResponse(
      success: false,
      message: message,
      data: data,
      statusCode: statusCode,
    );
  }

  factory ApiResponse.success({String? message, dynamic data}) {
    return ApiResponse(
      success: true,
      message: message,
      data: data,
    );
  }

  /// Convenience: extract a paginated results list from the response data.
  List<dynamic> get resultsList {
    if (data is Map<String, dynamic>) {
      final map = data as Map<String, dynamic>;
      return (map['results'] as List<dynamic>?) ??
          (map['data'] as List<dynamic>?) ??
          [];
    }
    if (data is List) return data as List<dynamic>;
    return [];
  }

  /// Convenience: extract total count from paginated response.
  int get totalCount {
    if (data is Map<String, dynamic>) {
      return (data as Map<String, dynamic>)['count'] as int? ?? resultsList.length;
    }
    return resultsList.length;
  }
}

/// Centralized HTTP client with auth, logging, and error interceptors.
/// Base URL is injected at construction time via [baseUrl].
class DioClient {
  late final Dio _dio;
  final SecureStorageService _storage;

  DioClient(this._storage, String baseUrl) {
    _dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout:
            const Duration(milliseconds: AppConstants.connectionTimeout),
        receiveTimeout:
            const Duration(milliseconds: AppConstants.receiveTimeout),
        sendTimeout: const Duration(milliseconds: AppConstants.sendTimeout),
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
      ),
    );

    _dio.interceptors.addAll([
      _AuthInterceptor(_storage),
      _LoggingInterceptor(),
      _ErrorInterceptor(),
    ]);
  }

  Dio get dio => _dio;
}

/// Helper class that provides typed HTTP methods (get, post, put, patch, delete)
/// and standardizes error handling across all datasources.
class ApiClient {
  final Dio _dio;
  final SecureStorageService _storage;

  ApiClient({required Dio dio, required SecureStorageService storage})
      : _dio = dio,
        _storage = storage;

  // ── HTTP Methods ───────────────────────────────────────────────────────

  Future<ApiResponse> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      final response = await _dio.get(
        path,
        queryParameters: queryParameters,
        options: options,
      );
      return _handleResponse(response);
    } on DioException catch (e) {
      return _handleDioError(e);
    } catch (e) {
      return ApiResponse.error('Terjadi kesalahan tak terduga: $e');
    }
  }

  Future<ApiResponse> post(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      final response = await _dio.post(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
      return _handleResponse(response);
    } on DioException catch (e) {
      return _handleDioError(e);
    } catch (e) {
      return ApiResponse.error('Terjadi kesalahan tak terduga: $e');
    }
  }

  Future<ApiResponse> put(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      final response = await _dio.put(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
      return _handleResponse(response);
    } on DioException catch (e) {
      return _handleDioError(e);
    } catch (e) {
      return ApiResponse.error('Terjadi kesalahan tak terduga: $e');
    }
  }

  Future<ApiResponse> patch(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      final response = await _dio.patch(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
      return _handleResponse(response);
    } on DioException catch (e) {
      return _handleDioError(e);
    } catch (e) {
      return ApiResponse.error('Terjadi kesalahan tak terduga: $e');
    }
  }

  Future<ApiResponse> delete(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      final response = await _dio.delete(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
      return _handleResponse(response);
    } on DioException catch (e) {
      return _handleDioError(e);
    } catch (e) {
      return ApiResponse.error('Terjadi kesalahan tak terduga: $e');
    }
  }

  // ── Response/Error Handlers ────────────────────────────────────────────

  ApiResponse _handleResponse(Response response) {
    final data = response.data;
    if (data is Map<String, dynamic>) {
      return ApiResponse.fromJson(data);
    }
    return ApiResponse.success(data: data);
  }

  ApiResponse _handleDioError(DioException error) {
    final appError = ErrorHandler.handle(error);
    final responseData = error.response?.data;
    return ApiResponse(
      success: false,
      message: appError.message,
      data: responseData,
      statusCode: appError.statusCode ?? error.response?.statusCode,
    );
  }
}

// ── Auth Interceptor ─────────────────────────────────────────────────────

class _AuthInterceptor extends Interceptor {
  final SecureStorageService _storage;

  _AuthInterceptor(this._storage);

  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final publicPaths = [
      '/auth/login/',
      '/auth/register/',
      '/auth/otp/',
      '/auth/otp/request/',
      '/auth/otp/verify/',
      '/auth/otp/resend/',
      '/auth/forgot-password/',
      '/auth/reset-password/',
      '/auth/check-availability/',
      '/health/',
      '/payments/config/',
      '/payments/config/public/',
      '/payments/methods/',
    ];

    final isPublic = publicPaths.any((p) => options.path.contains(p));

    if (!isPublic) {
      final token = await _storage.getAccessToken();
      if (token != null && token.isNotEmpty) {
        options.headers['Authorization'] = 'Bearer $token';
      }
    }

    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      try {
        final refreshToken = await _storage.getRefreshToken();
        if (refreshToken != null) {
          final dio = Dio();
          final response = await dio.post(
            '${err.requestOptions.baseUrl}/auth/token-refresh/',
            data: {'refresh': refreshToken},
          );

          if (response.statusCode == 200) {
            final newAccessToken = response.data['access'] as String?;
            if (newAccessToken != null) {
              await _storage.setAccessToken(newAccessToken);

              // Retry original request with new token
              err.requestOptions.headers['Authorization'] =
                  'Bearer $newAccessToken';
              final retryResponse = await Dio().fetch(err.requestOptions);
              handler.resolve(retryResponse);
              return;
            }
          }
        }
      } catch (_) {
        await _storage.clearAll();
      }
    }

    handler.next(err);
  }
}

// ── Logging Interceptor ──────────────────────────────────────────────────

class _LoggingInterceptor extends Interceptor {
  final Logger _logger = Logger();

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    _logger.d('🌐 ${options.method} ${options.path}');
    handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    _logger.d('✅ ${response.statusCode} ${response.requestOptions.path}');
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    _logger.e(
        '❌ ${err.response?.statusCode} ${err.requestOptions.path}: ${err.message}');
    handler.next(err);
  }
}

// ── Error Interceptor ────────────────────────────────────────────────────

class _ErrorInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final error = _mapError(err);
    handler.reject(error);
  }

  DioException _mapError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return DioException(
          requestOptions: error.requestOptions,
          error: 'Koneksi timeout. Silakan coba lagi.',
          type: error.type,
        );
      case DioExceptionType.connectionError:
        return DioException(
          requestOptions: error.requestOptions,
          error:
              'Tidak dapat terhubung ke server. Periksa koneksi internet Anda.',
          type: error.type,
        );
      default:
        return error;
    }
  }
}
