"""
Tests for the `"p.a."` per-annum abbreviation annual-marker guard (#55).

Without this fix, a salary string like "$85,000 p.a., paid biweekly" bypasses
the annual-marker guard (which checked /year, /yr, per year, per yr, per annum,
yearly, a year, annually, a yr but NOT "p.a.") and reaches the biweekly branch,
inflating $85k to $2.21M and falsely clearing SALARY_FLOOR.

"p.a." is the Latin abbreviation for "per annum", common in formal corporate
and public-sector job postings. The raw string is lowercased but periods are
retained, so "p.a." matches intact. It is not a substring of any pay-cadence
word, so it is safe to add bare.

Run:
    pytest tests/test_salary_pa_annual_guard.py
    python tests/test_salary_pa_annual_guard.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import _salary_score  # noqa: E402
from config import SALARY_FLOOR   # noqa: E402


# --- false-positive cases: "p.a." + pay-frequency note (the bugs) ---

def test_pa_biweekly_above_floor_not_inflated():
    """$85,000 p.a., paid biweekly -> 85000 (annual), NOT 85000*26=2.21M."""
    score = _salary_score({"salary": "$85,000 p.a., paid biweekly"})
    assert score == 1.0, f"expected 1.0 (85k >= floor), got {score} — biweekly multiplier likely fired"


def test_pa_biweekly_below_floor_not_inflated():
    """$50,000 p.a., biweekly -> 50000 (below floor), NOT 50000*26=1.3M."""
    score = _salary_score({"salary": "$50,000 p.a., biweekly"})
    expected = max(0.0, 50_000 / SALARY_FLOOR)
    assert abs(score - expected) < 0.01, (
        f"expected ~{expected:.3f} (50k below floor), got {score} — "
        "biweekly multiplier likely fired and inflated to 1.3M"
    )


def test_pa_semimonthly_not_inflated():
    """$120,000 p.a., semimonthly -> 120000 (annual), NOT 120000*24=2.88M."""
    score = _salary_score({"salary": "$120,000 p.a., semimonthly"})
    assert score == 1.0, f"expected 1.0 (120k >= floor), got {score}"


def test_pa_weekly_not_inflated():
    """$95,000 p.a., weekly -> 95000 (annual), NOT 95000*52=4.94M."""
    score = _salary_score({"salary": "$95,000 p.a., weekly"})
    assert score == 1.0, f"expected 1.0 (95k >= floor), got {score}"


# --- regression guards: unrelated cadences must still fire ---

def test_genuine_hourly_still_multiplied():
    """$75/hour (no "p.a.") -> 75 * 2080 = 156000 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$75 per hour"}) == 1.0


def test_genuine_daily_still_multiplied():
    """$400 daily rate (no "p.a.") -> 400 * 260 = 104000 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$400 daily rate"}) == 1.0


# --- self-test runner ---

if __name__ == "__main__":
    tests = [
        test_pa_biweekly_above_floor_not_inflated,
        test_pa_biweekly_below_floor_not_inflated,
        test_pa_semimonthly_not_inflated,
        test_pa_weekly_not_inflated,
        test_genuine_hourly_still_multiplied,
        test_genuine_daily_still_multiplied,
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
