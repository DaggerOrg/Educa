import 'package:flutter/material.dart';

import '../../../../core/theme/studio_theme.dart';

/// Studio's inline-editable-field look (see docs/design-system.md):
/// borderless until focus, underline in --rule. Shared between the login
/// and signup forms rather than duplicated per screen.
class AuthTextField extends StatelessWidget {
  final TextEditingController controller;
  final String label;
  final bool obscureText;
  final TextInputType? keyboardType;
  final String? Function(String?)? validator;
  final ValueChanged<String>? onFieldSubmitted;
  final TextInputAction? textInputAction;

  const AuthTextField({
    super.key,
    required this.controller,
    required this.label,
    this.obscureText = false,
    this.keyboardType,
    this.validator,
    this.onFieldSubmitted,
    this.textInputAction,
  });

  @override
  Widget build(BuildContext context) {
    final colors = context.studioColors;
    return TextFormField(
      controller: controller,
      obscureText: obscureText,
      keyboardType: keyboardType,
      validator: validator,
      onFieldSubmitted: onFieldSubmitted,
      textInputAction: textInputAction,
      style: Theme.of(context).textTheme.bodyLarge,
      decoration: InputDecoration(
        labelText: label,
        labelStyle: Theme.of(context).textTheme.bodyMedium?.copyWith(color: colors.inkFaint),
        filled: true,
        fillColor: colors.paperRaised,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: BorderSide(color: colors.rule)),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: BorderSide(color: colors.rule),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: BorderSide(color: colors.violet),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: BorderSide(color: colors.accentSoftInk),
        ),
      ),
    );
  }
}
