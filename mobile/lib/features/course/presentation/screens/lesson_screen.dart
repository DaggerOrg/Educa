import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_exception.dart';
import '../../../../core/theme/studio_theme.dart';
import '../../application/course_controller.dart';
import '../../domain/course.dart';
import '../widgets/status_pill.dart';

/// Lesson detail — edit title/objective inline (Studio's pattern: the
/// field itself is the editor, no separate edit mode), review generated
/// content, approve, then publish. Publishing is only ever a dedicated
/// server-side action (see backend/app/main.py) — this screen never sets
/// `published` itself, only calls POST .../publish via the course
/// controller, which is the single source of truth for lesson state
/// across this screen and the course list.
class LessonScreen extends ConsumerStatefulWidget {
  final String lessonId;

  const LessonScreen({super.key, required this.lessonId});

  @override
  ConsumerState<LessonScreen> createState() => _LessonScreenState();
}

class _LessonScreenState extends ConsumerState<LessonScreen> {
  late TextEditingController _titleController;
  late TextEditingController _objectiveController;
  Lesson? _lesson;
  bool _saving = false;
  bool _busy = false;
  bool _initialized = false;

  void _initFrom(Lesson lesson) {
    _lesson = lesson;
    _titleController = TextEditingController(text: lesson.title);
    _objectiveController = TextEditingController(text: lesson.objective);
    _initialized = true;
  }

  @override
  void dispose() {
    if (_initialized) {
      _titleController.dispose();
      _objectiveController.dispose();
    }
    super.dispose();
  }

  Future<void> _saveEdits() async {
    final lesson = _lesson;
    if (lesson == null) return;
    final title = _titleController.text.trim();
    final objective = _objectiveController.text.trim();
    if (title == lesson.title && objective == lesson.objective) return;
    setState(() => _saving = true);
    try {
      await ref
          .read(courseControllerProvider.notifier)
          .patchLesson(
            lesson.id,
            title: title == lesson.title ? null : title,
            objective: objective == lesson.objective ? null : objective,
          );
    } on ApiException catch (e) {
      if (mounted) _showError(e.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _toggleApproval() async {
    final lesson = _lesson;
    if (lesson == null) return;
    setState(() => _busy = true);
    try {
      await ref.read(courseControllerProvider.notifier).setApproval(lesson.id, !lesson.approved);
    } on ApiException catch (e) {
      if (mounted) _showError(e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _publish() async {
    final lesson = _lesson;
    if (lesson == null) return;
    setState(() => _busy = true);
    try {
      await ref.read(courseControllerProvider.notifier).publish(lesson.id);
    } on ApiException catch (e) {
      if (mounted) _showError(e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    // The course controller is the single source of truth for
    // approved/published/content; text fields stay locally controlled
    // until saved so a rebuild from elsewhere doesn't clobber a draft edit.
    ref.listen<AsyncValue<Course>>(courseControllerProvider, (previous, next) {
      final updated = next.valueOrNull?.findLesson(widget.lessonId);
      if (updated != null) setState(() => _lesson = updated);
    });

    if (!_initialized) {
      final courseState = ref.watch(courseControllerProvider);
      final initial = courseState.valueOrNull?.findLesson(widget.lessonId);
      if (initial != null) {
        _initFrom(initial);
      } else if (courseState.isLoading) {
        return Scaffold(
          appBar: AppBar(title: const Text('Lesson')),
          body: const Center(child: CircularProgressIndicator()),
        );
      } else {
        return Scaffold(
          appBar: AppBar(title: const Text('Lesson')),
          body: const Center(child: Text('Lesson not found.')),
        );
      }
    }

    final lesson = _lesson!;
    final colors = context.studioColors;
    final textTheme = Theme.of(context).textTheme;
    final canPublish = lesson.approved && lesson.content != null && !lesson.published;

    return Scaffold(
      appBar: AppBar(title: const Text('Lesson')),
      body: Focus(
        onFocusChange: (hasFocus) {
          if (!hasFocus) _saveEdits();
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            StatusPill(status: statusOfLesson(lesson)),
            const SizedBox(height: 12),
            TextField(
              controller: _titleController,
              style: textTheme.headlineSmall,
              decoration: const InputDecoration(border: InputBorder.none, isDense: true),
              onSubmitted: (_) => _saveEdits(),
              onTapOutside: (_) => _saveEdits(),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _objectiveController,
              style: textTheme.bodyMedium?.copyWith(color: colors.inkSoft),
              maxLines: null,
              decoration: const InputDecoration(
                border: InputBorder.none,
                isDense: true,
                hintText: 'Objective',
              ),
              onSubmitted: (_) => _saveEdits(),
              onTapOutside: (_) => _saveEdits(),
            ),
            if (_saving) ...[
              const SizedBox(height: 4),
              Text('Saving…', style: textTheme.bodySmall),
            ],
            const SizedBox(height: 20),
            Row(
              children: [
                OutlinedButton(
                  onPressed: _busy || lesson.published ? null : _toggleApproval,
                  child: Text(lesson.approved ? 'Reject' : 'Approve'),
                ),
                const SizedBox(width: 12),
                FilledButton(
                  onPressed: _busy || !canPublish ? null : _publish,
                  child: const Text('Publish'),
                ),
              ],
            ),
            const SizedBox(height: 24),
            Divider(color: colors.rule),
            const SizedBox(height: 16),
            if (lesson.content == null)
              Text('Not drafted yet — generate this lesson in Studio first.', style: textTheme.bodySmall)
            else
              _LessonContentView(content: lesson.content!),
          ],
        ),
      ),
    );
  }
}

class _LessonContentView extends StatelessWidget {
  final LessonContent content;

  const _LessonContentView({required this.content});

  @override
  Widget build(BuildContext context) {
    final colors = context.studioColors;
    final textTheme = Theme.of(context).textTheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('SLIDES', style: textTheme.labelSmall),
        const SizedBox(height: 8),
        for (final slide in content.slides)
          Container(
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: colors.paperRaised,
              border: Border.all(color: colors.rule),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(slide.heading, style: textTheme.titleMedium),
                const SizedBox(height: 6),
                for (final bullet in slide.bullets)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 2),
                    child: Text('•  $bullet', style: textTheme.bodyMedium),
                  ),
              ],
            ),
          ),
        const SizedBox(height: 12),
        Text('SPEAKER NOTES', style: textTheme.labelSmall),
        const SizedBox(height: 8),
        Text(content.speakerNotes, style: textTheme.bodyMedium),
        const SizedBox(height: 20),
        Text('QUIZ', style: textTheme.labelSmall),
        const SizedBox(height: 8),
        Text(content.quiz.question, style: textTheme.titleMedium),
        const SizedBox(height: 8),
        for (final (i, option) in content.quiz.options.indexed)
          Container(
            margin: const EdgeInsets.only(bottom: 6),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: i == content.quiz.correctIndex ? colors.tealSoft : colors.paperRaised,
              border: Border.all(color: i == content.quiz.correctIndex ? colors.teal : colors.rule),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              option,
              style: textTheme.bodyMedium?.copyWith(
                color: i == content.quiz.correctIndex ? colors.tealSoftInk : colors.ink,
              ),
            ),
          ),
      ],
    );
  }
}
