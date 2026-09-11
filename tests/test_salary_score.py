"""
Regression tests for _salary_score annualization (issue #17).

Weekly and monthly salaries must be normalized to an annual figure before the
SALARY_FLOOR comparison, exactly as hourly pay already was. Annual, hourly, and
unlisted-salary paths are unchanged.

Self-contained: runs under pytest OR directly with `python3 tests/test_salary_score.py`
(the repo has no CI / third-party test deps).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SALARY_FLOOR  # noqa: E402
from scorer import _salary_score  # noqa: E402


def _score(salary):
    return round(_salary_score({"salary": salary}), 6)


# (salary string, expected score, note)
CASES = [
    ("$5,000/month", 1.0, "monthly annualizes to $60k -> clears floor"),
    ("$1,500/week", 1.0, "weekly annualizes to $78k -> clears floor"),
    ("$30/hr", 1.0, "hourly still annualizes to $62.4k (unchanged)"),
    ("$60,000", 1.0, "annual figure at/above floor (unchanged)"),
    ("$40,000/year", round(40000 / SALARY_FLOOR, 6), "below-floor annual scored proportionally (unchanged)"),
    ("$2,000/month", round(24000 / SALARY_FLOOR, 6), "monthly below floor -> proportional, not near-zero"),
    ("$800/week", round(41600 / SALARY_FLOOR, 6), "weekly below floor -> proportional"),
    ("", 0.5, "unlisted salary stays neutral (unchanged)"),
]


def test_salary_score_cases():
    failures = []
    for salary, expected, note in CASES:
        got = _score(salary)
        if got != round(expected, 6):
            failures.append(f"  {salary!r}: got {got}, expected {round(expected, 6)}  ({note})")
    assert not failures, "salary score mismatches:\n" + "\n".join(failures)


if __name__ == "__main__":
    test_salary_score_cases()
    print(f"OK - {len(CASES)} salary-score cases passed")
