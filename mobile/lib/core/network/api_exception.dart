class ApiException implements Exception {
  final String message;
  final int status;

  ApiException(this.message, this.status);

  bool get isUnauthorized => status == 401;

  @override
  String toString() => message;
}
