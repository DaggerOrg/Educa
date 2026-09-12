import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/theme/studio_theme.dart';
import '../../../auth/application/auth_controller.dart';
import '../../application/course_controller.dart';
import '../../domain/course.dart';
import '../widgets/status_pill.dart';

/// The course overview — weeks and their lessons. Read/review/publish only;
/// syllabus generation and refinement still happen in Studio's chat (this
/// app doesn't port the CopilotKit/Agno agent loop, only the REST surface
/// backend/app/main.py exposes for direct edits and the publish gate).
class CourseScreen extends ConsumerWidget {
  const CourseScreen({super.key});

  Future<void> _confirmReset(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Reset course?'),
        content: const Text('This clears the demo course on the backend. This cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Reset')),
        ],
      ),
    );
    if (confirmed == true) {
      await ref.read(courseControllerProvider.notifier).resetCourse();
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final courseAsync = ref.watch(courseControllerProvider);
    final userName = ref.watch(authControllerProvider).valueOrNull?.user?.name;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Educa'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: () => ref.read(courseControllerProvider.notifier).refresh(),
          ),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'reset') _confirmReset(context, ref);
              if (value == 'logout') ref.read(authControllerProvider.notifier).logout();
            },
            itemBuilder: (context) => [
              if (userName != null) PopupMenuItem(enabled: false, child: Text('Signed in as $userName')),
              const PopupMenuItem(value: 'reset', child: Text('Reset course')),
              const PopupMenuItem(value: 'logout', child: Text('Log out')),
            ],
          ),
        ],
      ),
      body: courseAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorState(error: error, onRetry: () => ref.invalidate(courseControllerProvider)),
        data: (course) => RefreshIndicator(
          onRefresh: () => ref.read(courseControllerProvider.notifier).refresh(),
          child: _CourseBody(
            course: course,
            onOpenLesson: (lesson) => context.push('/lesson/${lesson.id}'),
          ),
        ),
      ),
    );
  }
}

class _CourseBody extends StatelessWidget {
  final Course course;
  final ValueChanged<Lesson> onOpenLesson;

  const _CourseBody({required this.course, required this.onOpenLesson});

  @override
  Widget build(BuildContext context) {
    final colors = context.studioColors;
    final textTheme = Theme.of(context).textTheme;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(course.title, style: textTheme.headlineLarge),
        const SizedBox(height: 4),
        Text(course.audience, style: textTheme.bodySmall),
        const SizedBox(height: 20),
        for (final week in course.weeks) ...[
          Text('WEEK ${week.week} — ${week.title}'.toUpperCase(), style: textTheme.labelSmall),
          const SizedBox(height: 8),
          for (final lesson in week.lessons)
            _LessonRow(lesson: lesson, onTap: () => onOpenLesson(lesson)),
          const SizedBox(height: 20),
        ],
        if (course.weeks.isEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 40),
            child: Text('No weeks yet.', style: textTheme.bodyMedium?.copyWith(color: colors.inkFaint)),
          ),
      ],
    );
  }
}

class _LessonRow extends StatelessWidget {
  final Lesson lesson;
  final VoidCallback onTap;

  const _LessonRow({required this.lesson, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final colors = context.studioColors;
    final textTheme = Theme.of(context).textTheme;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: colors.paperRaised,
        border: Border.all(color: colors.rule),
        borderRadius: BorderRadius.circular(8),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(lesson.title, style: textTheme.titleMedium),
                    if (lesson.objective.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        lesson.objective,
                        style: textTheme.bodySmall,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 12),
              StatusPill(status: statusOfLesson(lesson)),
            ],
          ),
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  final Object? error;
  final VoidCallback onRetry;

  const _ErrorState({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    final message = error is ApiException ? (error as ApiException).message : 'Something went wrong.';
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(message, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: 16),
            OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}
