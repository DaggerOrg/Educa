"""Run the live evals:

    python -m evals routing|injection|faculty|all [--only CASE_ID ...] [--min-pass 0.85]

Needs a Gemini key in the environment (GEMINI_API_KEY or GOOGLE_API_KEY) and
the local Postgres from docker-compose. Costs tokens -- start with
`--only` on one or two cases. Writes a JSON report to evals/reports/ so two
runs (before/after a change) can be compared. Exit code: 0 all suites meet
their bar, 1 a suite fell short, 2 not runnable (no key).
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROUTING_MIN_PASS = 0.85  # routing is fuzzy; injection is not
REPORTS = Path(__file__).parent / "reports"


def _print(report) -> None:
    print(f"\n== {report.name}: {sum(r.passed for r in report.results)}/{len(report.results)} passed ({report.pass_rate:.0%})")
    for r in report.results:
        print(f"  {'PASS' if r.passed else 'FAIL'}  {r.id}" + (f"  -- {r.detail}" if r.detail else ""))
    if report.extra:
        print(f"  {report.extra}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals")
    parser.add_argument("suite", choices=["routing", "injection", "faculty", "all"])
    parser.add_argument("--only", nargs="*", default=[], help="run just these case ids (routing/injection)")
    parser.add_argument("--min-pass", type=float, default=ROUTING_MIN_PASS, help="routing pass-rate bar")
    args = parser.parse_args(argv)

    from app.agents.models import api_key

    if not api_key():
        print("No model key: set GEMINI_API_KEY or GOOGLE_API_KEY (e.g. `infisical run -- python -m evals all`).")
        return 2

    from app.agents.models import build_model

    from . import live, metrics

    def pick(cases):
        return [c for c in cases if not args.only or c["id"] in args.only]

    suites, ok = [], True
    if args.suite in ("routing", "all"):
        report = metrics.run_routing(pick(live.load_cases("routing")), live.routing_router())
        ok &= report.pass_rate >= args.min_pass
        suites.append(report)
    if args.suite in ("injection", "all"):
        report = metrics.run_injection(pick(live.load_cases("injection")), live.injection_asker())
        ok &= not report.failures  # any injection failure is a failure
        suites.append(report)
    if args.suite in ("faculty", "all"):
        report, _ = live.faculty_scorer()
        ok &= not report.failures
        suites.append(report)

    for report in suites:
        _print(report)

    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out.write_text(json.dumps({
        "model": build_model().id,
        "suites": [{
            "name": s.name, "pass_rate": s.pass_rate, "extra": s.extra,
            "results": [{"id": r.id, "passed": r.passed, "detail": r.detail} for r in s.results],
        } for s in suites],
    }, indent=2))
    print(f"\nreport: {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
