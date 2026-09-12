import 'package:flutter/material.dart';

import '../../../../core/theme/studio_theme.dart';
import '../../domain/course.dart';

enum LessonStatus { draft, approved, published }

LessonStatus statusOfLesson(Lesson lesson) {
  if (lesson.published) return LessonStatus.published;
  if (lesson.approved) return LessonStatus.approved;
  return LessonStatus.draft;
}

/// Mono-uppercase tinted label — Studio's ".status-pill" pattern (see
/// docs/design-system.md). Reuse this for any new status/metadata chip
/// rather than inventing a new label style.
class StatusPill extends StatelessWidget {
  final LessonStatus status;

  const StatusPill({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    final colors = context.studioColors;
    final (label, bg, fg) = switch (status) {
      LessonStatus.draft => ('DRAFT', colors.paperSunken, colors.inkSoft),
      LessonStatus.approved => ('APPROVED', colors.accentSoft, colors.accentSoftInk),
      LessonStatus.published => ('PUBLISHED', colors.tealSoft, colors.tealSoftInk),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(3)),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(color: fg),
      ),
    );
  }
}
