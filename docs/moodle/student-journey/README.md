# Student journey through Moodle

Enrollment to badges. Same scoring convention as the [teacher
journey](../teacher-journey/README.md): 1–5 happiness at that step.

```mermaid
journey
    title Student journey through Moodle
    section Get into the course
      Log in to Moodle: 5: Student
      Search or browse the course catalog: 3: Student
      Self-enroll with an enrollment key: 4: Student
    section Learn
      Open the course page and read sections: 4: Student
      Open resources — pages, files, embedded video: 4: Student
      Post or reply in a forum activity: 3: Student
    section Be assessed
      Attempt a quiz within the time limit: 3: Student
      Upload an assignment file before the due date: 4: Student
      Wait for grading and read teacher feedback: 2: Student
    section Track progress
      Check grades in the gradebook: 4: Student
      Watch the completion checklist tick off: 4: Student
      Earn a badge on course completion: 5: Student
```

## Reading the low point

- **Waiting for grading (2):** quizzes self-grade instantly, but
  assignments and essay-type quiz questions sit in a teacher's queue —
  the single biggest source of "when will I know my grade" friction in
  Moodle. Educa doesn't have this problem yet only because it doesn't
  have free-response grading at all: `QuizItem.kind` is
  `multiple_choice | fill_in_blank`, both auto-gradable. The moment
  Educa adds an open-ended question type, it inherits this exact wait.
- **Course catalog search (3):** finding the right course among many is
  a real Moodle weak spot (categories nest deep, search is keyword-only).
  Doesn't apply to Educa yet — there's one course, one student list, no
  catalog to browse.

Compare against the [teacher journey](../teacher-journey/README.md): the
student side has no analogue to Moodle's question-bank pain, but it's the
side that inherits the grading-wait cost the moment Educa's assessment
model grows past auto-gradable question types.
