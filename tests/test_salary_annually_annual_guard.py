"""
Tests for the `"annually"` annual-marker guard (#51).

Without this fix, a salary string like "$65,000 annually, paid biweekly" bypasses
the annual-marker guard (which checked /year, /yr, per year, per yr, per annum,
yearly, a year — but NOT "annually") and reaches the biweekly branch, inflating
$65k to $1.69M and falsely clearing SALARY_FLOOR.

"annually" is the adverbial form of "annual". It is not a substring of any cadence
branch word (biweekly, semimonthly, weekly, monthly, hourly, daily), so it is safe
to add bare.

Run:
    pytest tests/test_salary_annually_annual_guard.py
    python tests/test_salary_annually_annual_guard.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import _salary_score  # noqa: E402
from config import SALARY_FLOOR   # noqa: E402


# --- false-positive cases: "annually" + pay-frequency note (the bugs) ---

def test_annually_biweekly_below_floor_not_inflated():
    """$42,000 annually, paid biweekly -> 42000 (below floor), NOT 42000*26=1.09M."""
    score = _salary_score({"salary": "$42,000 annually, paid biweekly"})
    expected = max(0.0, 42_000 / SALARY_FLOOR)
    assert abs(score - expected) < 0.01, (
        f"expected ~{expected:.3f} (42k below floor), got {score} — "
        "biweekly multiplier likely fired and inflated to 1.09M"
    )


def test_annually_biweekly_above_floor_not_inflated():
    """$80k annually, bi-weekly -> 80000 (annual, above floor) -> 1.0."""
    score = _salary_score({"salary": "$80k annually, bi-weekly"})
    assert score == 1.0, f"expected 1.0 (80k >= floor), got {score}"


def test_annually_weekly_not_inflated():
    """$72,000 annually, weekly pay -> 72000 (annual, above floor) -> 1.0."""
    score = _salary_score({"salary": "$72,000 annually, weekly pay"})
    assert score == 1.0, f"expected 1.0 (72k >= floor), got {score}"


def test_annually_monthly_not_inflated():
    """$65,000 annually, monthly payroll -> 65000 (annual) -> 1.0."""
    score = _salary_score({"salary": "$65,000 annually, monthly payroll"})
    assert score == 1.0, f"expected 1.0 (65k >= floor), got {score}"


# --- guard must not break genuine frequency-only salaries (no "annually") ---

def test_genuine_biweekly_no_annually_still_multiplied():
    """$3,500 biweekly (no "annually") -> 3500 * 26 = 91,000 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$3,500 biweekly"}) == 1.0


def test_genuine_weekly_no_annually_still_multiplied():
    """$1,200/week (no "annually") -> 1200 * 52 = 62,400 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$1,200/week"}) == 1.0


# --- self-test runner ---

if __name__ == "__main__":
    tests = [
        test_annually_biweekly_below_floor_not_inflated,
        test_annually_biweekly_above_floor_not_inflated,
        test_annually_weekly_not_inflated,
        test_annually_monthly_not_inflated,
        test_genuine_biweekly_no_annually_still_multiplied,
        test_genuine_weekly_no_annually_still_multiplied,
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
