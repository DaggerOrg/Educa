import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/course_repository.dart';
import '../domain/course.dart';

/// Single source of truth for the loaded course. `build()` does the
/// initial fetch; every lesson-level action (edit, approve, publish)
/// replaces just that lesson in-place so every screen watching this
/// provider — the course list, the lesson detail screen — stays in sync
/// without a manual refetch or a callback threaded through widget props.
class CourseController extends AsyncNotifier<Course> {
  @override
  Future<Course> build() => ref.read(courseRepositoryProvider).fetchCourse();

  Future<void> refresh() async {
    state = const AsyncLoading<Course>().copyWithPrevious(state);
    state = await AsyncValue.guard(() => ref.read(courseRepositoryProvider).fetchCourse());
  }

  Future<void> resetCourse() async {
    await ref.read(courseRepositoryProvider).resetCourse();
    await refresh();
  }

  /// These intentionally don't route through AsyncValue.guard: a failed
  /// approve/publish call should surface as an error to the caller (a
  /// SnackBar on the lesson screen), not blow away the whole course state.
  Future<void> patchLesson(String lessonId, {String? title, String? objective}) async {
    final updated = await ref.read(courseRepositoryProvider).patchLesson(lessonId, title: title, objective: objective);
    _replaceLesson(updated);
  }

  Future<void> setApproval(String lessonId, bool approved) async {
    final updated = await ref.read(courseRepositoryProvider).setApproval(lessonId, approved);
    _replaceLesson(updated);
  }

  Future<void> publish(String lessonId) async {
    final updated = await ref.read(courseRepositoryProvider).publishLesson(lessonId);
    _replaceLesson(updated);
  }

  void _replaceLesson(Lesson updated) {
    final course = state.valueOrNull;
    if (course == null) return;
    state = AsyncData(course.replacingLesson(updated));
  }
}

final courseControllerProvider = AsyncNotifierProvider<CourseController, Course>(CourseController.new);
