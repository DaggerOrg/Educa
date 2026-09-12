# Moodle — reference for Educa's platform design

Moodle is the reference chosen for the "normal LMS" half of Educa: it's
open source, mature, and its course/quiz/enrollment schema maps closely
onto [Educa's own entity diagram](../entity-diagram/README.md) (`Course` →
`Section`, `Quiz`/`QuizAttempt` → `quiz`/`quiz_attempts`, etc). It's used
here purely to see feature breadth and flow and find gaps in Educa's
model — not as a spec to copy. Moodle carries 20 years of accreted
complexity (permissions, grading scales, plugin hooks) that Educa
shouldn't inherit wholesale.

- [mind-map/](mind-map/README.md) — Moodle's feature structure (roles,
  course structure, activities, gradebook, completion) with a note on
  which pieces Educa already has, and which it doesn't yet.
- [teacher-journey/](teacher-journey/README.md) — a teacher's path
  through Moodle, course setup to grading.
- [student-journey/](student-journey/README.md) — a student's path
  through Moodle, enrollment to badges.
