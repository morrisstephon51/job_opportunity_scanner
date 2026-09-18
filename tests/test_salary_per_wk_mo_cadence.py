"""
Regression tests for _salary_score space-separated abbreviated cadence forms.

"per wk" (space-separated weekly abbreviation) slips past /week, /wk, per week,
weekly and receives no cadence multiplier: "$900 per wk" is treated as $900/yr
(far below the $55k floor), even though $900 x 52 = $46,800 is on-floor.
"per mo" (space-separated monthly abbreviation) slips past /month, /mo,
per month, monthly: "$4,500 per mo" is treated as $4,500/yr instead of $54,000.

Same in-form gap as issue #36 (per hr for hourly). Fix: add "per wk" to the
weekly branch and "per mo" to the monthly branch. See issue #38.

Self-contained: runs under pytest OR directly with
`python3 tests/test_salary_per_wk_mo_cadence.py`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SALARY_FLOOR  # noqa: E402
from scorer import _salary_score  # noqa: E402

ANNUAL_ABOVE_FLOOR = SALARY_FLOOR + 1000
ABOVE_FLOOR_WEEKLY = ANNUAL_ABOVE_FLOOR / 52
ABOVE_FLOOR_MONTHLY = ANNUAL_ABOVE_FLOOR / 12
BELOW_FLOOR_WEEKLY = max(1, SALARY_FLOOR / 52 - 50)
BELOW_FLOOR_MONTHLY = max(1, SALARY_FLOOR / 12 - 50)


def _score(salary):
    return round(_salary_score({"salary": salary}), 6)


# --- per wk: weekly abbreviated form ---

def test_per_wk_above_floor_scores_1():
    rate = int(ABOVE_FLOOR_WEEKLY)
    job = {"salary": f"${rate} per wk"}
    assert _salary_score(job) == 1.0, f"${rate} per wk (above floor) must score 1.0"


def test_per_wk_below_floor_scores_proportional():
    rate = int(BELOW_FLOOR_WEEKLY)
    job = {"salary": f"${rate} per wk"}
    s = _salary_score(job)
    assert 0.0 < s < 1.0, f"${rate} per wk (below floor) must score between 0 and 1, got {s}"


def test_900_per_wk_concrete():
    # $900 per wk x52 = $46,800 — below $55k floor; without the fix it scores $900/55k ≈ 0.016
    job = {"salary": "$900 per wk"}
    s = _salary_score(job)
    # Must be scored as weekly (annualized), not as a raw $900 figure
    expected = 900 * 52 / SALARY_FLOOR
    assert abs(s - min(1.0, round(expected, 6))) < 0.01, (
        f"$900 per wk must be annualized (x52), got {s}"
    )


def test_1200_per_wk_above_floor_concrete():
    # $1,200 per wk x52 = $62,400 — above $55k floor
    job = {"salary": "$1200 per wk"}
    assert _salary_score(job) == 1.0, "$1200 per wk (=$62,400/yr) must score 1.0 vs $55k floor"


# --- per mo: monthly abbreviated form ---

def test_per_mo_above_floor_scores_1():
    rate = int(ABOVE_FLOOR_MONTHLY)
    job = {"salary": f"${rate} per mo"}
    assert _salary_score(job) == 1.0, f"${rate} per mo (above floor) must score 1.0"


def test_per_mo_below_floor_scores_proportional():
    rate = int(BELOW_FLOOR_MONTHLY)
    job = {"salary": f"${rate} per mo"}
    s = _salary_score(job)
    assert 0.0 < s < 1.0, f"${rate} per mo (below floor) must score between 0 and 1, got {s}"


def test_4500_per_mo_concrete():
    # $4,500 per mo x12 = $54,000 — below $55k floor
    job = {"salary": "$4500 per mo"}
    expected = 4500 * 12 / SALARY_FLOOR
    s = _salary_score(job)
    assert abs(s - min(1.0, round(expected, 6))) < 0.01, (
        f"$4500 per mo must be annualized (x12), got {s}"
    )


def test_5000_per_mo_above_floor_concrete():
    # $5,000 per mo x12 = $60,000 — above $55k floor
    job = {"salary": "$5000 per mo"}
    assert _salary_score(job) == 1.0, "$5000 per mo (=$60k/yr) must score 1.0 vs $55k floor"


# --- controls: existing anchored forms still work ---

def test_per_week_still_works():
    rate = int(ABOVE_FLOOR_WEEKLY)
    job = {"salary": f"${rate} per week"}
    assert _salary_score(job) == 1.0, "per week form must still work"


def test_per_month_still_works():
    rate = int(ABOVE_FLOOR_MONTHLY)
    job = {"salary": f"${rate} per month"}
    assert _salary_score(job) == 1.0, "per month form must still work"


def test_slash_wk_still_works():
    rate = int(ABOVE_FLOOR_WEEKLY)
    job = {"salary": f"${rate}/wk"}
    assert _salary_score(job) == 1.0, "/wk form must still work"


def test_slash_mo_still_works():
    rate = int(ABOVE_FLOOR_MONTHLY)
    job = {"salary": f"${rate}/mo"}
    assert _salary_score(job) == 1.0, "/mo form must still work"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
