/// Mirrors frontend/src/types.ts — keep the two in sync.
library;

class Quiz {
  final String question;
  final List<String> options;
  final int correctIndex;

  const Quiz({
    required this.question,
    required this.options,
    required this.correctIndex,
  });

  factory Quiz.fromJson(Map<String, dynamic> json) => Quiz(
    question: json['question'] as String,
    options: List<String>.from(json['options'] as List),
    correctIndex: json['correctIndex'] as int,
  );
}

class Slide {
  final String heading;
  final List<String> bullets;

  const Slide({required this.heading, required this.bullets});

  factory Slide.fromJson(Map<String, dynamic> json) => Slide(
    heading: json['heading'] as String,
    bullets: List<String>.from(json['bullets'] as List),
  );
}

class LessonContent {
  final List<Slide> slides;
  final String speakerNotes;
  final Quiz quiz;

  const LessonContent({
    required this.slides,
    required this.speakerNotes,
    required this.quiz,
  });

  factory LessonContent.fromJson(Map<String, dynamic> json) => LessonContent(
    slides: (json['slides'] as List)
        .map((s) => Slide.fromJson(s as Map<String, dynamic>))
        .toList(),
    speakerNotes: json['speakerNotes'] as String,
    quiz: Quiz.fromJson(json['quiz'] as Map<String, dynamic>),
  );
}

class Lesson {
  final String id;
  final String title;
  final String objective;
  final LessonContent? content;
  final bool approved;
  final bool published;

  const Lesson({
    required this.id,
    required this.title,
    required this.objective,
    required this.content,
    required this.approved,
    required this.published,
  });

  factory Lesson.fromJson(Map<String, dynamic> json) => Lesson(
    id: json['id'] as String,
    title: json['title'] as String,
    objective: json['objective'] as String? ?? '',
    content: json['content'] == null
        ? null
        : LessonContent.fromJson(json['content'] as Map<String, dynamic>),
    approved: json['approved'] as bool? ?? false,
    published: json['published'] as bool? ?? false,
  );
}

class Week {
  final int week;
  final String title;
  final List<Lesson> lessons;

  const Week({required this.week, required this.title, required this.lessons});

  factory Week.fromJson(Map<String, dynamic> json) => Week(
    week: json['week'] as int,
    title: json['title'] as String,
    lessons: (json['lessons'] as List)
        .map((l) => Lesson.fromJson(l as Map<String, dynamic>))
        .toList(),
  );

  Week replacingLesson(Lesson updated) => Week(
    week: week,
    title: title,
    lessons: lessons.map((l) => l.id == updated.id ? updated : l).toList(),
  );
}

class Course {
  final String id;
  final String title;
  final String audience;
  final List<Week> weeks;

  const Course({
    required this.id,
    required this.title,
    required this.audience,
    required this.weeks,
  });

  factory Course.fromJson(Map<String, dynamic> json) => Course(
    id: json['id'] as String,
    title: json['title'] as String,
    audience: json['audience'] as String? ?? '',
    weeks: (json['weeks'] as List)
        .map((w) => Week.fromJson(w as Map<String, dynamic>))
        .toList(),
  );

  Lesson? findLesson(String lessonId) {
    for (final week in weeks) {
      for (final lesson in week.lessons) {
        if (lesson.id == lessonId) return lesson;
      }
    }
    return null;
  }

  Course replacingLesson(Lesson updated) =>
      Course(id: id, title: title, audience: audience, weeks: weeks.map((w) => w.replacingLesson(updated)).toList());
}
