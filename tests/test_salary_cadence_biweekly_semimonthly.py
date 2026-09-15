"""
Regression tests for _salary_score compound pay-cadence normalization.

Same `in`-substring-collision class already fixed in this file for "il"/Nashville
and "ai"/retail. The period-normalization block read pay cadences with a bare
substring test, so:
  * "biweekly" / "bi-weekly" matched the "week" branch  -> x52 instead of x26
    (~2x too HIGH: an underpaid role false-clears SALARY_FLOOR and can fire a
     score>=ALERT_SCORE_THRESHOLD alert).
  * "semimonthly" / "semi-monthly" matched the "month" branch -> x12 instead of
    x24 (~2x too LOW: a genuine above-floor role is scored under the floor and
    buried -- the same harmful direction as the weekly/monthly annualization fix).

Bi-weekly = 26 pay periods/yr; semi-monthly = 24/yr. True weekly/monthly/hourly
paths must stay unchanged.

Self-contained: runs under pytest OR directly with
`python3 tests/test_salary_cadence_biweekly_semimonthly.py`.
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
    # --- the bug: semimonthly under-annualized and buried ---
    ("$3,000 semimonthly", 1.0, "semi-monthly $3k x24 = $72k -> clears floor (was x12=$36k, buried)"),
    ("$3,000 semi-monthly", 1.0, "hyphenated semi-monthly annualizes the same"),
    # --- the bug: biweekly over-annualized and false-cleared ---
    ("$1,731 bi-weekly", round(45006 / SALARY_FLOOR, 6),
     "bi-weekly $1,731 x26 = $45,006 -> below floor, proportional (was x52=$90k, false clear)"),
    ("$2,300 biweekly", 1.0, "bi-weekly $2,300 x26 = $59,800 -> genuinely clears floor"),
    # --- controls: true cadences unchanged (must NOT be caught by the new branches) ---
    ("$1,500/week", 1.0, "true weekly still x52 = $78k"),
    ("$800/week", round(41600 / SALARY_FLOOR, 6), "true weekly below floor unchanged"),
    ("$5,000/month", 1.0, "true monthly still x12 = $60k"),
    ("$2,000/month", round(24000 / SALARY_FLOOR, 6), "true monthly below floor unchanged"),
    ("$30/hr", 1.0, "hourly unchanged"),
    ("$60,000", 1.0, "annual unchanged"),
    ("", 0.5, "unlisted stays neutral"),
]


def test_salary_cadence_cases():
    failures = []
    for salary, expected, note in CASES:
        got = _score(salary)
        if got != round(expected, 6):
            failures.append(f"  {salary!r}: got {got}, expected {round(expected, 6)}  ({note})")
    assert not failures, "salary cadence mismatches:\n" + "\n".join(failures)


if __name__ == "__main__":
    test_salary_cadence_cases()
    print(f"OK - {len(CASES)} salary-cadence cases passed")
