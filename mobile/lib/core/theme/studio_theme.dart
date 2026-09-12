import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Studio's warm paper/ink design tokens — mirrors the CSS custom
/// properties in frontend/src/styles.css. See docs/design-system.md.
/// Do not reuse these in a way that resembles the marketing site's dark
/// SaaS palette — the two apps are deliberately different products.
class StudioColors extends ThemeExtension<StudioColors> {
  final Color paper;
  final Color paperRaised;
  final Color paperSunken;
  final Color ink;
  final Color inkSoft;
  final Color inkFaint;
  final Color rule;
  final Color accent;
  final Color accentSoft;
  final Color accentSoftInk;
  final Color teal;
  final Color tealSoft;
  final Color tealSoftInk;
  final Color violet;
  final Color violetSoft;
  final Color violetSoftInk;

  const StudioColors({
    required this.paper,
    required this.paperRaised,
    required this.paperSunken,
    required this.ink,
    required this.inkSoft,
    required this.inkFaint,
    required this.rule,
    required this.accent,
    required this.accentSoft,
    required this.accentSoftInk,
    required this.teal,
    required this.tealSoft,
    required this.tealSoftInk,
    required this.violet,
    required this.violetSoft,
    required this.violetSoftInk,
  });

  static const light = StudioColors(
    paper: Color(0xFFF3F5F1),
    paperRaised: Color(0xFFFFFFFF),
    paperSunken: Color(0xFFE9ECE5),
    ink: Color(0xFF17223C),
    inkSoft: Color(0xFF55627C),
    inkFaint: Color(0xFF8991A4),
    rule: Color(0xFFD7DBD1),
    accent: Color(0xFFA66A10),
    accentSoft: Color(0xFFF1DDAE),
    accentSoftInk: Color(0xFF6B4A0C),
    teal: Color(0xFF2C6A58),
    tealSoft: Color(0xFFD9EAE3),
    tealSoftInk: Color(0xFF1F4C3F),
    violet: Color(0xFF5B57A8),
    violetSoft: Color(0xFFE3E1F5),
    violetSoftInk: Color(0xFF423F82),
  );

  static const dark = StudioColors(
    paper: Color(0xFF10151D),
    paperRaised: Color(0xFF171F2A),
    paperSunken: Color(0xFF1C2531),
    ink: Color(0xFFE8EAEE),
    inkSoft: Color(0xFF9AA5B7),
    inkFaint: Color(0xFF6C7789),
    rule: Color(0xFF2B3441),
    accent: Color(0xFFE7B75B),
    accentSoft: Color(0xFF33280F),
    accentSoftInk: Color(0xFFE7B75B),
    teal: Color(0xFF6DBBA2),
    tealSoft: Color(0xFF12312A),
    tealSoftInk: Color(0xFF6DBBA2),
    violet: Color(0xFFABA7E8),
    violetSoft: Color(0xFF241F45),
    violetSoftInk: Color(0xFFABA7E8),
  );

  @override
  StudioColors copyWith({
    Color? paper,
    Color? paperRaised,
    Color? paperSunken,
    Color? ink,
    Color? inkSoft,
    Color? inkFaint,
    Color? rule,
    Color? accent,
    Color? accentSoft,
    Color? accentSoftInk,
    Color? teal,
    Color? tealSoft,
    Color? tealSoftInk,
    Color? violet,
    Color? violetSoft,
    Color? violetSoftInk,
  }) => StudioColors(
    paper: paper ?? this.paper,
    paperRaised: paperRaised ?? this.paperRaised,
    paperSunken: paperSunken ?? this.paperSunken,
    ink: ink ?? this.ink,
    inkSoft: inkSoft ?? this.inkSoft,
    inkFaint: inkFaint ?? this.inkFaint,
    rule: rule ?? this.rule,
    accent: accent ?? this.accent,
    accentSoft: accentSoft ?? this.accentSoft,
    accentSoftInk: accentSoftInk ?? this.accentSoftInk,
    teal: teal ?? this.teal,
    tealSoft: tealSoft ?? this.tealSoft,
    tealSoftInk: tealSoftInk ?? this.tealSoftInk,
    violet: violet ?? this.violet,
    violetSoft: violetSoft ?? this.violetSoft,
    violetSoftInk: violetSoftInk ?? this.violetSoftInk,
  );

  @override
  StudioColors lerp(ThemeExtension<StudioColors>? other, double t) {
    if (other is! StudioColors) return this;
    return StudioColors(
      paper: Color.lerp(paper, other.paper, t)!,
      paperRaised: Color.lerp(paperRaised, other.paperRaised, t)!,
      paperSunken: Color.lerp(paperSunken, other.paperSunken, t)!,
      ink: Color.lerp(ink, other.ink, t)!,
      inkSoft: Color.lerp(inkSoft, other.inkSoft, t)!,
      inkFaint: Color.lerp(inkFaint, other.inkFaint, t)!,
      rule: Color.lerp(rule, other.rule, t)!,
      accent: Color.lerp(accent, other.accent, t)!,
      accentSoft: Color.lerp(accentSoft, other.accentSoft, t)!,
      accentSoftInk: Color.lerp(accentSoftInk, other.accentSoftInk, t)!,
      teal: Color.lerp(teal, other.teal, t)!,
      tealSoft: Color.lerp(tealSoft, other.tealSoft, t)!,
      tealSoftInk: Color.lerp(tealSoftInk, other.tealSoftInk, t)!,
      violet: Color.lerp(violet, other.violet, t)!,
      violetSoft: Color.lerp(violetSoft, other.violetSoft, t)!,
      violetSoftInk: Color.lerp(violetSoftInk, other.violetSoftInk, t)!,
    );
  }
}

extension StudioColorsContext on BuildContext {
  StudioColors get studioColors => Theme.of(this).extension<StudioColors>()!;
}

ThemeData _buildTheme(StudioColors colors, Brightness brightness) {
  final base = ThemeData(brightness: brightness, useMaterial3: true);
  final displayFont = GoogleFonts.fraunces;
  final bodyFont = GoogleFonts.publicSans;

  return base.copyWith(
    scaffoldBackgroundColor: colors.paper,
    colorScheme: base.colorScheme.copyWith(
      brightness: brightness,
      surface: colors.paperRaised,
      primary: colors.accent,
      onPrimary: Colors.white,
      secondary: colors.teal,
      error: colors.accentSoftInk,
      outline: colors.rule,
    ),
    extensions: [colors],
    textTheme: base.textTheme
        .copyWith(
          displayLarge: displayFont(color: colors.ink, fontWeight: FontWeight.w600),
          displayMedium: displayFont(color: colors.ink, fontWeight: FontWeight.w600),
          headlineLarge: displayFont(color: colors.ink, fontWeight: FontWeight.w600, fontSize: 28),
          headlineMedium: displayFont(color: colors.ink, fontWeight: FontWeight.w600, fontSize: 22),
          headlineSmall: displayFont(color: colors.ink, fontWeight: FontWeight.w600, fontSize: 18),
          titleLarge: displayFont(color: colors.ink, fontWeight: FontWeight.w600, fontSize: 17),
          titleMedium: bodyFont(color: colors.ink, fontWeight: FontWeight.w600),
          bodyLarge: bodyFont(color: colors.ink, fontSize: 15, height: 1.55),
          bodyMedium: bodyFont(color: colors.ink, fontSize: 15, height: 1.55),
          bodySmall: bodyFont(color: colors.inkSoft, fontSize: 13, height: 1.5),
          labelSmall: GoogleFonts.ibmPlexMono(
            color: colors.inkFaint,
            fontSize: 11,
            letterSpacing: 0.6,
            fontWeight: FontWeight.w500,
          ),
        )
        .apply(bodyColor: colors.ink, displayColor: colors.ink),
    appBarTheme: AppBarTheme(
      backgroundColor: colors.paper,
      foregroundColor: colors.ink,
      elevation: 0,
      titleTextStyle: displayFont(color: colors.ink, fontWeight: FontWeight.w600, fontSize: 20),
    ),
    cardTheme: CardThemeData(
      color: colors.paperRaised,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(color: colors.rule),
      ),
    ),
    dividerTheme: DividerThemeData(color: colors.rule, space: 1),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: colors.accent,
        foregroundColor: Colors.white,
        disabledBackgroundColor: colors.accent.withValues(alpha: 0.55),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
        textStyle: bodyFont(fontWeight: FontWeight.w600, fontSize: 13.5),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: colors.ink,
        side: BorderSide(color: colors.rule),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
        textStyle: bodyFont(fontWeight: FontWeight.w600, fontSize: 13.5),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: false,
      border: UnderlineInputBorder(borderSide: BorderSide(color: colors.rule)),
      enabledBorder: const UnderlineInputBorder(borderSide: BorderSide(color: Colors.transparent)),
      focusedBorder: UnderlineInputBorder(borderSide: BorderSide(color: colors.rule, style: BorderStyle.solid)),
    ),
  );
}

final ThemeData studioLightTheme = _buildTheme(StudioColors.light, Brightness.light);
final ThemeData studioDarkTheme = _buildTheme(StudioColors.dark, Brightness.dark);
