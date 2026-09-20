"""
Tests for the `"a year"` annual-marker guard (#49).

Without this fix, a salary string like "$42,000 a year, paid biweekly" bypasses
the annual-marker guard (which checked /year, /yr, per year, per yr, per annum,
yearly but NOT "a year") and reaches the biweekly branch, inflating $42k to
$1.09M and falsely clearing SALARY_FLOOR.

"a year" is the natural-English equivalent of "per year" and appears in job
postings as the annual-rate marker (e.g. "up to $75,000 a year"). It is not a
substring of any pay-cadence word, so it is safe to add bare.

Run:
    pytest tests/test_salary_a_year_annual_guard.py
    python tests/test_salary_a_year_annual_guard.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import _salary_score  # noqa: E402
from config import SALARY_FLOOR   # noqa: E402


# --- false-positive cases: "a year" + pay-frequency note (the bugs) ---

def test_a_year_biweekly_below_floor_not_inflated():
    """$42,000 a year, paid biweekly -> 42000 (below floor), NOT 42000*26=1.09M."""
    score = _salary_score({"salary": "$42,000 a year, paid biweekly"})
    expected = max(0.0, 42_000 / SALARY_FLOOR)
    assert abs(score - expected) < 0.01, (
        f"expected ~{expected:.3f} (42k below floor), got {score} — "
        "biweekly multiplier likely fired and inflated to 1.09M"
    )


def test_a_year_weekly_below_floor_not_inflated():
    """$30,000 a year, paid weekly -> 30000 (below floor), NOT 30000*52=1.56M."""
    score = _salary_score({"salary": "$30,000 a year, paid weekly"})
    expected = max(0.0, 30_000 / SALARY_FLOOR)
    assert abs(score - expected) < 0.01, (
        f"expected ~{expected:.3f} (30k below floor), got {score} — "
        "weekly multiplier likely fired and inflated to 1.56M"
    )


def test_a_year_biweekly_above_floor_not_inflated():
    """$75,000 a year, paid biweekly -> 75000 (annual, above floor) -> 1.0."""
    score = _salary_score({"salary": "$75,000 a year, paid biweekly"})
    assert score == 1.0, f"expected 1.0 (75k >= floor), got {score}"


def test_a_year_monthly_not_inflated():
    """$65,000 a year, monthly pay -> 65000 (annual), NOT 65000*12=780k."""
    score = _salary_score({"salary": "$65,000 a year, monthly pay"})
    assert score == 1.0, f"expected 1.0 (65k >= floor), got {score}"


# --- guard must not break genuine frequency-only salaries (no "a year" marker) ---

def test_genuine_biweekly_no_a_year_still_multiplied():
    """$3,500 biweekly (no "a year") -> 3500 * 26 = 91,000 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$3,500 biweekly"}) == 1.0


def test_genuine_weekly_no_a_year_still_multiplied():
    """$1,200/week (no "a year") -> 1200 * 52 = 62,400 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$1,200/week"}) == 1.0


# --- self-test runner ---

if __name__ == "__main__":
    tests = [
        test_a_year_biweekly_below_floor_not_inflated,
        test_a_year_weekly_below_floor_not_inflated,
        test_a_year_biweekly_above_floor_not_inflated,
        test_a_year_monthly_not_inflated,
        test_genuine_biweekly_no_a_year_still_multiplied,
        test_genuine_weekly_no_a_year_still_multiplied,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
    if passed != len(tests):
        raise SystemExit(1)
