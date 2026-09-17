"""
Regression tests for _salary_score space-separated compound cadence forms.

"bi weekly" (space, no hyphen) slips past the "biweekly"/"bi-weekly" guard and
hits the "weekly" branch  -> x52 instead of x26 (2x overcount: underpaid role
false-clears SALARY_FLOOR and may fire an alert).
"semi monthly" (space) slips past "semimonthly"/"semi-monthly" and hits
"monthly" -> x12 instead of x24 (0.5x undercount: above-floor role buried).

Municipal and county job boards -- Cook County included -- often write pay
schedules with a space separator rather than a hyphen. Same in-substring-
collision class as issues #3, #28, #29, #30; see issue #32.

Self-contained: runs under pytest OR directly with
`python3 tests/test_salary_biweekly_space.py`.
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
    # --- space-separated biweekly: was x52 (false-clear), must be x26 ---
    ("$950 bi weekly",
     round(950 * 26 / SALARY_FLOOR, 6),
     "bi weekly $950 x26=$24,700 below floor (was x52=$49,400, false clear)"),
    ("$2,500 bi weekly",
     1.0,
     "bi weekly $2,500 x26=$65,000 genuinely clears floor"),
    # --- space-separated semimonthly: was x12 (buried), must be x24 ---
    ("$2,300 semi monthly",
     1.0,
     "semi monthly $2,300 x24=$55,200 clears floor (was x12=$27,600, buried)"),
    ("$1,000 semi monthly",
     round(1000 * 24 / SALARY_FLOOR, 6),
     "semi monthly $1,000 x24=$24,000 below floor proportional"),
    # --- controls: existing forms still work (use below-floor values for proportional check) ---
    ("$1,500 biweekly",
     round(1500 * 26 / SALARY_FLOOR, 6),
     "concatenated biweekly x26 unchanged"),
    ("$1,500 bi-weekly",
     round(1500 * 26 / SALARY_FLOOR, 6),
     "hyphenated bi-weekly x26 unchanged"),
    ("$1,500 semimonthly",
     round(1500 * 24 / SALARY_FLOOR, 6),
     "concatenated semimonthly x24 unchanged"),
    ("$1,500 semi-monthly",
     round(1500 * 24 / SALARY_FLOOR, 6),
     "hyphenated semi-monthly x24 unchanged"),
    # --- controls: true weekly/monthly paths unchanged ---
    ("$1,500/week", 1.0, "true weekly still x52"),
    ("$5,000/month", 1.0, "true monthly still x12"),
]


def test_salary_biweekly_space_cases():
    failures = []
    for salary, expected, note in CASES:
        got = _score(salary)
        if got != round(expected, 6):
            failures.append(f"  {salary!r}: got {got}, expected {round(expected, 6)}  ({note})")
    assert not failures, "biweekly/semi-monthly space-form mismatches:\n" + "\n".join(failures)


if __name__ == "__main__":
    test_salary_biweekly_space_cases()
    print(f"OK - {len(CASES)} biweekly-space cases passed")
