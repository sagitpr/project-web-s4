import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';

/// Provider for RegionApi.
final regionApiProvider = Provider<RegionApi>((ref) {
  return RegionApi(ref.watch(apiClientProvider));
});

/// Indonesian Regions API datasource.
class RegionApi {
  final ApiClient _client;

  RegionApi(this._client);

  /// Get list of provinces.
  Future<ApiResponse> getProvinces() async {
    return _client.get(ApiConstants.provinces);
  }

  /// Get regencies/cities for a province.
  Future<ApiResponse> getRegencies(String provinceCode) async {
    return _client.get(
      ApiConstants.regencies,
      queryParameters: {'province_code': provinceCode},
    );
  }

  /// Get districts for a regency.
  Future<ApiResponse> getDistricts(String regencyCode) async {
    return _client.get(
      ApiConstants.districts,
      queryParameters: {'regency_code': regencyCode},
    );
  }

  /// Get villages for a district.
  Future<ApiResponse> getVillages(String districtCode) async {
    return _client.get(
      ApiConstants.villages,
      queryParameters: {'district_code': districtCode},
    );
  }

  /// Search regions.
  Future<ApiResponse> search(String query) async {
    return _client.get(
      ApiConstants.regionSearch,
      queryParameters: {'q': query},
    );
  }
}
