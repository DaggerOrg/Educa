import '../../../core/network/api_exception.dart';

String? validateEmail(String? value) {
  if (value == null || value.trim().isEmpty) return 'Email is required';
  if (!value.contains('@') || !value.contains('.')) return 'Enter a valid email';
  return null;
}

String? validatePassword(String? value) {
  if (value == null || value.isEmpty) return 'Password is required';
  if (value.length < 8) return 'At least 8 characters';
  return null;
}

String? validateName(String? value) {
  if (value == null || value.trim().isEmpty) return 'Name is required';
  return null;
}

String authErrorMessage(Object? error) => error is ApiException ? error.message : 'Something went wrong. Try again.';
