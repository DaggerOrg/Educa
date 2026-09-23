"""Background worker entrypoint. Run with:

    python -m curriculum_ai.jobs.worker

from backend/, with the venv active and REDIS_URL/DATABASE_URL/storage env
vars set the same way the API process has them (see README section this
package's parent adds, or docs/architecture/educa-ai-architecture.md).

Uses RQ's `SimpleWorker` (runs each job in-process) rather than the default
fork-per-job `Worker`. On macOS, forking a child process after
sentence-transformers/torch has touched the Objective-C runtime crashes
the work-horse outright ("may have been in progress in another thread
when fork() was called... Crashing instead" - Apple's documented
fork-safety guard, hit in practice the first time a job actually runs).
SimpleWorker sidesteps it entirely by never calling fork(); the tradeoff
(a hard crash in job code would take down the worker process, not just
one job) is acceptable here since processing.py already catches and
records every expected failure mode, and reprocessing is idempotent
(see processing.py's module docstring) so a worker restart loses nothing.
"""

from rq import SimpleWorker

from .queue import get_queue, get_redis


def main() -> None:
    worker = SimpleWorker([get_queue()], connection=get_redis())
    worker.work()


if __name__ == "__main__":
    main()
