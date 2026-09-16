"""
Regression tests for _salary_score PTO/benefit week and month false cadence.

The cadence-detection block used bare "week" and "month" substring tests, which
fires on compensation descriptions that mention PTO or benefit duration rather
than a pay cadence:

  * "$48,000 per year + 3 weeks PTO"  -> "week" in raw -> x52 -> $2.5M/yr
    (below-floor annual role falsely clears SALARY_FLOOR and can fire an ALERT)
  * "$60,000 annual, 12 months health coverage" -> "month" in raw -> x12 -> $720k
    (above-floor role bloats; below-floor role false-clears the floor)

Same `in`-substring-collision class already fixed here for:
  il->Nashville (location), ai->retail (title), biweekly/semimonthly (PR#28).

Fix (scorer.py, _salary_score): replace bare "week"/"month" with anchored forms
(/week, /wk, per week, weekly; /month, /mo, per month, monthly) so only real
weekly/monthly pay cadences multiply the raw figure.

Self-contained: runs under pytest OR directly with
`python3 tests/test_salary_ptoweeks_notcadence.py`.
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
    # --- the bug: PTO weeks inflate a below-floor annual salary ---
    ("$48,000 per year + 3 weeks PTO", round(48000 / SALARY_FLOOR, 6),
     "$48k annual + 3 weeks PTO: below floor (was $48k*52=$2.5M, false 1.0)"),
    ("$40,000 with 4 weeks vacation", round(40000 / SALARY_FLOOR, 6),
     "$40k annual + 4 weeks vacation: below floor (was $40k*52, false 1.0)"),
    ("$53,000 / year, 2 weeks PTO", round(53000 / SALARY_FLOOR, 6),
     "$53k annual + 2 weeks PTO: just below floor (was false 1.0)"),
    # --- the bug: months in benefits inflate a below-floor annual salary ---
    ("$45,000 annual plus 12 months health coverage", round(45000 / SALARY_FLOOR, 6),
     "$45k annual + 12 months benefits: below floor (was $45k*12=$540k, false 1.0)"),
    ("$50,000, 6 months dental included", round(50000 / SALARY_FLOOR, 6),
     "$50k annual + 6 months dental: below floor (was false 1.0)"),
    # --- controls: real weekly cadences still annualize correctly ---
    ("$1,500/week", 1.0, "true /week -> x52 = $78k, clears floor"),
    ("$800/week", round(41600 / SALARY_FLOOR, 6), "true /week below floor"),
    ("$1,500 per week", 1.0, "true per week -> x52 = $78k"),
    ("$1,500 weekly", 1.0, "true weekly -> x52 = $78k"),
    # --- controls: real monthly cadences still annualize correctly ---
    ("$5,000/month", 1.0, "true /month -> x12 = $60k, clears floor"),
    ("$4,000/month", round(48000 / SALARY_FLOOR, 6), "true /month below floor"),
    ("$5,000 per month", 1.0, "true per month -> x12 = $60k"),
    ("$5,000 monthly", 1.0, "true monthly -> x12 = $60k"),
    # --- controls: hourly, annual, and unlisted unchanged ---
    ("$30/hr", 1.0, "hourly unchanged: x2080 = $62.4k"),
    ("$60,000", 1.0, "annual unchanged"),
    ("", 0.5, "unlisted stays neutral"),
]


def test_salary_ptoweeks_not_cadence():
    failures = []
    for salary, expected, note in CASES:
        got = _score(salary)
        if got != round(expected, 6):
            failures.append(f"  {salary!r}:\n    got {got}, expected {round(expected, 6)}  ({note})")
    assert not failures, "salary score mismatches:\n" + "\n".join(failures)


if __name__ == "__main__":
    test_salary_ptoweeks_not_cadence()
    print(f"OK - {len(CASES)} salary-PTO-cadence cases passed")
