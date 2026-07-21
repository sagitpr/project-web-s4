import 'package:flutter_test/flutter_test.dart';
import 'package:warungio_app/core/network/dio_client.dart';

void main() {
  group('ApiResponse', () {
    group('fromJson', () {
      test('parses success response correctly', () {
        final json = {
          'success': true,
          'message': 'Data loaded',
          'data': {'id': 1, 'name': 'Test'},
        };

        final response = ApiResponse.fromJson(json);
        expect(response.success, true);
        expect(response.message, 'Data loaded');
        expect(response.data, isA<Map>());
      });

      test('parses status-based success', () {
        final json = {
          'status': 'success',
          'message': 'OK',
        };

        final response = ApiResponse.fromJson(json);
        expect(response.success, true);
      });

      test('parses failure response correctly', () {
        final json = {
          'success': false,
          'message': 'Something went wrong',
          'error': 'Internal error',
        };

        final response = ApiResponse.fromJson(json);
        expect(response.success, false);
        expect(response.message, 'Something went wrong');
      });

      test('prefers message over detail over error', () {
        final json = {
          'message': 'Main message',
          'detail': 'Detail message',
          'error': 'Error message',
        };

        final response = ApiResponse.fromJson(json);
        expect(response.message, 'Main message');
      });

      test('falls back to detail when message is missing', () {
        final json = {
          'detail': 'Detail message',
          'error': 'Error message',
        };

        final response = ApiResponse.fromJson(json);
        expect(response.message, 'Detail message');
      });

      test('falls back to error when message and detail are missing', () {
        final json = {
          'error': 'Error message',
        };

        final response = ApiResponse.fromJson(json);
        expect(response.message, 'Error message');
      });

      test('data defaults to full json when data key is absent', () {
        final json = {'id': 1, 'name': 'Direct'};
        final response = ApiResponse.fromJson(json);
        expect(response.data, same(json));
      });
    });

    group('ApiResponse.success factory', () {
      test('creates success response', () {
        final response = ApiResponse.success(message: 'OK', data: {'key': 'val'});
        expect(response.success, true);
        expect(response.message, 'OK');
        expect(response.data, {'key': 'val'});
      });
    });

    group('ApiResponse.error factory', () {
      test('creates error response', () {
        final response = ApiResponse.error('Error!', statusCode: 500);
        expect(response.success, false);
        expect(response.message, 'Error!');
        expect(response.statusCode, 500);
      });
    });

    group('resultsList helper', () {
      test('extracts results list from paginated response data', () {
        final response = ApiResponse.success(data: {
          'results': [
            {'id': 1},
            {'id': 2},
          ],
          'count': 2,
        });

        expect(response.resultsList.length, 2);
        expect(response.totalCount, 2);
      });

      test('extracts data list as fallback', () {
        final response = ApiResponse.success(data: {
          'data': [
            {'id': 1},
          ],
        });

        expect(response.resultsList.length, 1);
      });

      test('returns empty list for non-map data', () {
        final response = ApiResponse.success(data: 'string data');
        expect(response.resultsList, isEmpty);
      });

      test('returns empty list for null data', () {
        final response = ApiResponse.success();
        expect(response.resultsList, isEmpty);
      });

      test('wraps list data directly', () {
        final response = ApiResponse.success(data: [
          {'id': 1},
        ]);
        expect(response.resultsList.length, 1);
      });

      test('totalCount falls back to resultsList length', () {
        final response = ApiResponse.success(data: {
          'results': [{'id': 1}],
        });
        expect(response.totalCount, 1);
      });
    });

    group('statusCode', () {
      test('parses status_code from json', () {
        final json = {'status_code': 404, 'message': 'Not found'};
        final response = ApiResponse.fromJson(json);
        expect(response.statusCode, 404);
      });

      test('status_code is null when absent', () {
        final json = {'message': 'OK'};
        final response = ApiResponse.fromJson(json);
        expect(response.statusCode, isNull);
      });
    });
  });
}
