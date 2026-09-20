"""
Tests for the `"per yr"` annual-marker guard (#47).

Without this fix, a salary string like "$75,000 per yr, paid biweekly" bypasses
the annual-marker guard (which checked /year, /yr, per year, per annum, yearly
but NOT "per yr") and reaches the biweekly branch, inflating $75k to $1.95M
and falsely clearing SALARY_FLOOR.

"/yr" covers the slash form ("$80k/yr") and "per year" covers the full spelled
form — but "per yr" (abbreviated "per" + "yr") matches neither and is the gap.
"per yr" is safe to add — not a substring of any pay-cadence word.

Run:
    pytest tests/test_salary_per_yr_annual_guard.py
    python tests/test_salary_per_yr_annual_guard.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import _salary_score  # noqa: E402
from config import SALARY_FLOOR   # noqa: E402


# --- false-positive cases: "per yr" + pay-frequency note (the bugs) ---

def test_per_yr_biweekly_not_inflated():
    """$75,000 per yr, paid biweekly -> 75000 (annual), NOT 75000*26=1.95M."""
    score = _salary_score({"salary": "$75,000 per yr, paid biweekly"})
    assert score == 1.0, f"expected 1.0 (75k >= floor), got {score}"


def test_per_yr_biweekly_below_floor_not_inflated():
    """$42,000 per yr, biweekly -> 42000 (below floor), NOT 42000*26=1.09M (above)."""
    score = _salary_score({"salary": "$42,000 per yr, biweekly"})
    expected = max(0.0, 42_000 / SALARY_FLOOR)
    assert abs(score - expected) < 0.01, (
        f"expected ~{expected:.3f} (42k below floor), got {score} — "
        "biweekly multiplier likely fired and inflated to 1.09M"
    )


def test_per_yr_weekly_not_inflated():
    """$65k per yr, weekly pay -> 65000 (annual), NOT 65000*52=3.38M."""
    score = _salary_score({"salary": "$65k per yr, weekly pay"})
    assert score == 1.0, f"expected 1.0 (65k >= floor), got {score}"


def test_per_yr_monthly_not_inflated():
    """$70,000 per yr, monthly deposits -> 70000 (annual), NOT 70000*12=840k."""
    score = _salary_score({"salary": "$70,000 per yr, monthly deposits"})
    assert score == 1.0, f"expected 1.0 (70k >= floor), got {score}"


# --- guard must not break genuine frequency-only salaries (no per yr marker) ---

def test_genuine_biweekly_no_per_yr_still_multiplied():
    """$3,500 biweekly (no per yr) -> 3500 * 26 = 91,000 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$3,500 biweekly"}) == 1.0


def test_genuine_weekly_no_per_yr_still_multiplied():
    """$1,200/week (no per yr) -> 1200 * 52 = 62,400 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$1,200/week"}) == 1.0


# --- self-test runner ---

if __name__ == "__main__":
    tests = [
        test_per_yr_biweekly_not_inflated,
        test_per_yr_biweekly_below_floor_not_inflated,
        test_per_yr_weekly_not_inflated,
        test_per_yr_monthly_not_inflated,
        test_genuine_biweekly_no_per_yr_still_multiplied,
        test_genuine_weekly_no_per_yr_still_multiplied,
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
