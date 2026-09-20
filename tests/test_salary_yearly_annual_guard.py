"""
Tests for the `"yearly"` annual-marker guard (#45).

Without this fix, a salary string like "$80,000 yearly, paid biweekly" bypasses
the annual-marker guard (which only checked /year, /yr, per year, per annum) and
reaches the biweekly branch, inflating $80k to $2.08M and falsely clearing
SALARY_FLOOR.

"yearly" is safe to add to the guard — it is not a substring of any other
pay-cadence word (unlike bare "annual", which appears inside "semi-annual").

Run:
    pytest tests/test_salary_yearly_annual_guard.py
    python tests/test_salary_yearly_annual_guard.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import _salary_score  # noqa: E402
from config import SALARY_FLOOR   # noqa: E402


# --- false-positive cases: "yearly" + pay-frequency note (the bugs) ---

def test_yearly_biweekly_not_inflated():
    """$80,000 yearly, paid biweekly -> 80000 (annual), NOT 80000*26=2.08M."""
    score = _salary_score({"salary": "$80,000 yearly, paid biweekly"})
    assert score == 1.0, f"expected 1.0 (80k >= floor), got {score}"


def test_yearly_biweekly_below_floor_not_inflated():
    """$45,000 yearly, biweekly -> 45000 (below floor), NOT 45000*26=1.17M (above)."""
    score = _salary_score({"salary": "$45,000 yearly, biweekly"})
    expected = max(0.0, 45_000 / SALARY_FLOOR)
    assert abs(score - expected) < 0.01, (
        f"expected ~{expected:.3f} (45k below floor), got {score} — "
        "biweekly multiplier likely fired and inflated to 1.17M"
    )


def test_yearly_weekly_not_inflated():
    """$60k yearly, weekly pay -> 60000 (annual), NOT 60000*52=3.12M."""
    score = _salary_score({"salary": "$60k yearly, weekly pay"})
    assert score == 1.0, f"expected 1.0 (60k >= floor), got {score}"


def test_yearly_monthly_not_inflated():
    """$72,000 yearly, monthly deposits -> 72000 (annual), NOT 72000*12=864k."""
    score = _salary_score({"salary": "$72,000 yearly, monthly deposits"})
    assert score == 1.0, f"expected 1.0 (72k >= floor), got {score}"


# --- guard must not break genuine frequency-only salaries (no yearly marker) ---

def test_genuine_biweekly_no_yearly_still_multiplied():
    """$3,500 biweekly (no yearly) -> 3500 * 26 = 91,000 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$3,500 biweekly"}) == 1.0


def test_genuine_weekly_no_yearly_still_multiplied():
    """$1,200/week (no yearly) -> 1200 * 52 = 62,400 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$1,200/week"}) == 1.0


# --- self-test runner ---

if __name__ == "__main__":
    tests = [
        test_yearly_biweekly_not_inflated,
        test_yearly_biweekly_below_floor_not_inflated,
        test_yearly_weekly_not_inflated,
        test_yearly_monthly_not_inflated,
        test_genuine_biweekly_no_yearly_still_multiplied,
        test_genuine_weekly_no_yearly_still_multiplied,
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
