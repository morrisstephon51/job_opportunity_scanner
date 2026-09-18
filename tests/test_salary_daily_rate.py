"""
Regression tests: daily pay rates must be annualized (x260) in _salary_score.

Without a /day cadence branch, a $400/day role scores near 0 ($400 vs $55k
floor) even though $400 x 260 = $104k is well above SALARY_FLOOR.

Runs standalone (python3 tests/test_salary_daily_rate.py) or under pytest.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import _salary_score
from config import SALARY_FLOOR

ABOVE_FLOOR_DAILY = SALARY_FLOOR / 260 + 1   # daily rate that clears floor
BELOW_FLOOR_DAILY = SALARY_FLOOR / 260 - 10  # daily rate that does not


def test_per_day_above_floor_scores_1():
    rate = int(ABOVE_FLOOR_DAILY)
    job = {"salary": f"${rate} per day"}
    assert _salary_score(job) == 1.0, "per-day salary above floor must score 1.0"


def test_slash_day_above_floor_scores_1():
    rate = int(ABOVE_FLOOR_DAILY)
    job = {"salary": f"${rate}/day"}
    assert _salary_score(job) == 1.0, "$X/day above floor must score 1.0"


def test_daily_keyword_above_floor_scores_1():
    rate = int(ABOVE_FLOOR_DAILY)
    job = {"salary": f"${rate} daily"}
    assert _salary_score(job) == 1.0, "$X daily above floor must score 1.0"


def test_per_day_below_floor_scores_less_than_1():
    rate = max(1, int(BELOW_FLOOR_DAILY))
    job = {"salary": f"${rate} per day"}
    s = _salary_score(job)
    assert 0.0 < s < 1.0, f"per-day below floor must score between 0 and 1, got {s}"


def test_400_per_day_concrete_above_55k():
    # $400/day x 260 = $104k — well above $55k floor
    job = {"salary": "$400 per day"}
    assert _salary_score(job) == 1.0, "$400/day (=$104k/yr) must score 1.0 vs $55k floor"


def test_200_per_day_concrete_below_55k():
    # $200/day x 260 = $52k — below $55k floor
    job = {"salary": "$200 per day"}
    s = _salary_score(job)
    assert s < 1.0, "$200/day (=$52k/yr) should score below 1.0"
    assert s > 0.0, "$200/day should not score 0"


def test_hourly_not_affected():
    job = {"salary": "$25 per hour"}
    s = _salary_score(job)
    # $25 x 2080 = $52k < $55k floor
    assert s < 1.0, "hourly path must be unchanged"


def test_no_salary_still_neutral():
    job = {"salary": None}
    assert _salary_score(job) == 0.5, "no salary must remain neutral"


if __name__ == "__main__":
    tests = [fn for name, fn in globals().items() if name.startswith("test_")]
    passed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {fn.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
