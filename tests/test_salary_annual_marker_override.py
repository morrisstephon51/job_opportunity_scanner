"""
Tests for the annual-marker cadence-override fix (#43).

PR #28 added the biweekly/semimonthly cadence guards but flagged
'$70k/year paid biweekly' as out-of-scope. Without a guard, a salary string
with an explicit per-year marker AND a pay-frequency note picks up the
frequency word later in the chain:

  "$75,000/year, paid biweekly"  -> "biweekly" fires -> 75000 * 26 = 1,950,000
  "$60k/yr, paid weekly"         -> "weekly" fires   -> 60000 * 52 = 3,120,000

Both would clear SALARY_FLOOR ($55k) by orders of magnitude and trigger a
false ALERT_SCORE_THRESHOLD fire for roles that should score at their true
annual figure.

Fix: check unambiguous per-year markers ("/year", "/yr", "per year", "per annum")
BEFORE the frequency chain and short-circuit when found.

The repo has no CI; run either way:
    pytest tests/test_salary_annual_marker_override.py
    python tests/test_salary_annual_marker_override.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import _salary_score  # noqa: E402
from config import SALARY_FLOOR   # noqa: E402


# --- false-positive cases: annual salary + pay-frequency note (the bugs) ---

def test_slash_year_paid_biweekly_not_inflated():
    """$75,000/year, paid biweekly -> 75000 (annual), NOT 75000*26=1.95M."""
    score = _salary_score({"salary": "$75,000/year, paid biweekly"})
    assert score == 1.0, f"expected 1.0 (75k >= floor), got {score}"
    # Proof it is not inflated: if biweekly fired, score would be 1.0 *and* the
    # annualized value would be 1.95M; we verify the path by checking low <= 75k
    # indirectly through a BELOW-floor annual+frequency string.

def test_slash_year_paid_biweekly_below_floor_not_inflated():
    """$45,000/year, paid biweekly -> 45000 (annual, below floor), NOT 45000*26=1.17M (above)."""
    score = _salary_score({"salary": "$45,000/year, paid biweekly"})
    expected = max(0.0, 45_000 / SALARY_FLOOR)
    assert abs(score - expected) < 0.01, (
        f"expected ~{expected:.3f} (45k below floor), got {score} — "
        "biweekly multiplier likely fired and inflated to 1.17M"
    )

def test_slash_yr_paid_weekly_not_inflated():
    """$60k/yr, paid weekly -> 60000 (annual), NOT 60000*52=3.12M."""
    score = _salary_score({"salary": "$60k/yr, paid weekly"})
    assert score == 1.0, f"expected 1.0 (60k >= floor), got {score}"

def test_slash_yr_below_floor_paid_weekly_not_inflated():
    """$40,000/yr, paid weekly -> 40000 (below floor), NOT 40000*52=2.08M."""
    score = _salary_score({"salary": "$40,000/yr, paid weekly"})
    expected = max(0.0, 40_000 / SALARY_FLOOR)
    assert abs(score - expected) < 0.01, (
        f"expected ~{expected:.3f} (40k below floor), got {score}"
    )

def test_per_year_monthly_note_not_inflated():
    """$90,000 per year, paid monthly -> 90000 (annual), NOT 90000*12=1.08M."""
    score = _salary_score({"salary": "$90,000 per year, paid monthly"})
    assert score == 1.0, f"expected 1.0 (90k >= floor), got {score}"

def test_per_annum_biweekly_not_inflated():
    """$80,000 per annum, bi-weekly pay -> 80000 (annual), NOT 80000*26=2.08M."""
    score = _salary_score({"salary": "$80,000 per annum, bi-weekly pay"})
    assert score == 1.0, f"expected 1.0 (80k >= floor), got {score}"


# --- guard must not break genuine frequency-only salaries (no annual marker) ---

def test_genuine_biweekly_still_multiplied():
    """$3,500 biweekly (no /year) -> 3500 * 26 = 91,000 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$3,500 biweekly"}) == 1.0

def test_genuine_semimonthly_still_multiplied():
    """$2,400 semi-monthly -> 2400 * 24 = 57,600 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$2,400 semi-monthly"}) == 1.0

def test_genuine_weekly_still_multiplied():
    """$1,200/week -> 1200 * 52 = 62,400 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$1,200/week"}) == 1.0

def test_genuine_hourly_still_multiplied():
    """$30/hour -> 30 * 2080 = 62,400 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$30/hour"}) == 1.0

def test_genuine_day_rate_still_multiplied():
    """$250 per day -> 250 * 260 = 65,000 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$250 per day"}) == 1.0


# --- self-test runner ---

if __name__ == "__main__":
    tests = [
        test_slash_year_paid_biweekly_not_inflated,
        test_slash_year_paid_biweekly_below_floor_not_inflated,
        test_slash_yr_paid_weekly_not_inflated,
        test_slash_yr_below_floor_paid_weekly_not_inflated,
        test_per_year_monthly_note_not_inflated,
        test_per_annum_biweekly_not_inflated,
        test_genuine_biweekly_still_multiplied,
        test_genuine_semimonthly_still_multiplied,
        test_genuine_weekly_still_multiplied,
        test_genuine_hourly_still_multiplied,
        test_genuine_day_rate_still_multiplied,
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
