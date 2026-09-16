"""
Regression tests for _salary_score hourly-cadence false fires.

The cadence-detection block used bare "hour" in raw, which fires on any salary
string that mentions hours in a non-pay-cadence context:

  * "$45,000, 24-hour emergency on-call" -> "hour" in "24-hour" -> x2080 -> $93.6M
    (below-floor annual role falsely clears SALARY_FLOOR and can fire an ALERT)
  * "$48,000 + unlimited office hours" -> "hour" in "hours" -> x2080 -> $99.8M
    (same false-clear)

Same `in`-substring-collision class already fixed here for:
  il->Nashville (location), ai->retail (title), biweekly/semimonthly (PR#28),
  week/month PTO descriptions (PR#29).

Fix (scorer.py, _salary_score): replace bare "hour" with anchored forms
(/hour, /hr, per hour, hourly) so only real hourly pay cadences multiply the
raw figure by 2080.

Self-contained: runs under pytest OR directly with
`python3 tests/test_salary_hours_not_cadence.py`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SALARY_FLOOR  # noqa: E402
from scorer import _salary_score  # noqa: E402


def _score(salary):
    return round(_salary_score({"salary": salary}), 6)


def _annual(n):
    """Expected score for a plain annual figure (no cadence multiplier)."""
    return round(n / SALARY_FLOOR, 6) if n < SALARY_FLOOR else 1.0


def _hourly(rate):
    """Expected score for a true hourly rate (x2080 annualization)."""
    annual = rate * 2080
    return 1.0 if annual >= SALARY_FLOOR else round(annual / SALARY_FLOOR, 6)


# (salary string, expected score, note)
CASES = [
    # --- the bug: "hours" mention inflates a below-floor annual salary ---
    ("$45,000, 24-hour emergency on-call bonus",
     _annual(45000),
     "$45k annual + 24-hour on-call: below floor (was $45k*2080=$93.6M, false 1.0)"),
    ("$48,000 + unlimited office hours support",
     _annual(48000),
     "$48k annual + office hours: below floor (was $48k*2080=$99.8M, false 1.0)"),
    ("$50,000 with flexible hours",
     _annual(50000),
     "$50k annual + flexible hours: below floor (was false 1.0)"),
    ("$53,000 / year, 8-hour workday",
     _annual(53000),
     "$53k annual + 8-hour workday: below floor (was false 1.0)"),
    # --- controls: real hourly cadences still annualize correctly ---
    ("$30/hour", _hourly(30),
     "true /hour -> $30*2080=$62.4k, clears floor"),
    ("$25/hr", _hourly(25),
     "true /hr -> $25*2080=$52k, below floor"),
    ("$30 per hour", _hourly(30),
     "true per hour -> $30*2080=$62.4k"),
    ("$30 hourly", _hourly(30),
     "true hourly -> $30*2080=$62.4k"),
    # --- controls: annual and unlisted unchanged ---
    ("$60,000", 1.0, "annual unchanged"),
    ("", 0.5, "unlisted stays neutral"),
]


def test_salary_hours_not_cadence():
    failures = []
    for salary, expected, note in CASES:
        got = _score(salary)
        if got != round(expected, 6):
            failures.append(
                f"  {salary!r}:\n    got {got}, expected {round(expected, 6)}  ({note})"
            )
    assert not failures, "salary score mismatches:\n" + "\n".join(failures)


if __name__ == "__main__":
    test_salary_hours_not_cadence()
    print(f"OK - {len(CASES)} salary-hours-cadence cases passed")
