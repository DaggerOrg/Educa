import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/course.dart';

/// Mirrors frontend/src/api.ts's course-related calls (fetchCourse,
/// patchLesson, setApproval, publishLesson, resetCourse) — same
/// endpoints, same request/response shape.
class CourseRepository {
  final ApiClient _client;

  CourseRepository(this._client);

  Future<Course> fetchCourse() =>
      _client.request('/course', parse: (json) => Course.fromJson(json as Map<String, dynamic>));

  Future<Lesson> patchLesson(String lessonId, {String? title, String? objective}) => _client.request(
    '/lessons/$lessonId',
    method: 'PATCH',
    body: {'title': ?title, 'objective': ?objective},
    parse: (json) => Lesson.fromJson(json as Map<String, dynamic>),
  );

  Future<Lesson> setApproval(String lessonId, bool approved) => _client.request(
    '/lessons/$lessonId/approval',
    method: 'PATCH',
    body: {'approved': approved},
    parse: (json) => Lesson.fromJson(json as Map<String, dynamic>),
  );

  Future<Lesson> publishLesson(String lessonId) => _client.request(
    '/lessons/$lessonId/publish',
    method: 'POST',
    parse: (json) => Lesson.fromJson(json as Map<String, dynamic>),
  );

  Future<void> resetCourse() => _client.request('/reset', method: 'POST', parse: (_) {});
}

final courseRepositoryProvider = Provider<CourseRepository>(
  (ref) => CourseRepository(ref.watch(apiClientProvider)),
);
