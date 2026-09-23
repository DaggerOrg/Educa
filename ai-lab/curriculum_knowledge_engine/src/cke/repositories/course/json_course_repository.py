"""File-backed `CourseRepository` - one JSON file per course under
`persist_dir`. Adequate for this project's scale (a handful of curricula);
a production deployment would swap this for a row in the same Postgres
database `PgVectorRepository` already talks to, without any service code
changing (it only depends on `CourseRepository`, the interface).
"""

from __future__ import annotations

from pathlib import Path
from threading import RLock

from cke.domain.models import Course
from cke.logging_config import get_logger
from cke.repositories.interfaces import CourseRepository

logger = get_logger(__name__)


class JsonCourseRepository(CourseRepository):
    def __init__(self, persist_dir: Path):
        self._persist_dir = persist_dir
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def _path_for(self, course_id: str) -> Path:
        return self._persist_dir / f"{course_id}.json"

    def save(self, course: Course) -> None:
        with self._lock:
            self._path_for(course.id).write_text(course.model_dump_json(indent=2))
        logger.info("Saved course '%s' (%d lessons)", course.id, course.lesson_count)

    def get(self, course_id: str) -> Course | None:
        path = self._path_for(course_id)
        if not path.exists():
            return None
        return Course.model_validate_json(path.read_text())

    def list(self) -> list[Course]:
        courses = [
            Course.model_validate_json(path.read_text())
            for path in sorted(self._persist_dir.glob("*.json"))
        ]
        return sorted(courses, key=lambda c: c.title)

    def delete(self, course_id: str) -> None:
        path = self._path_for(course_id)
        if path.exists():
            path.unlink()
