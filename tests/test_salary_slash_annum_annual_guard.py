"""
Tests for the "/annum" slash per-annum annual-marker guard (#57).

Without this fix, a salary string like "$42,000/annum, paid biweekly" bypasses
the annual-marker guard (which checked /year, /yr, per year, per yr, per annum,
yearly, a year, annually, a yr, p.a. but NOT "/annum") and reaches the biweekly
branch, inflating $42k to $1.09M and falsely clearing SALARY_FLOOR.

"/annum" is the slash form of "per annum", mirroring the "/yr" <-> "per yr"
<-> "per year" pattern. "per annum" was already guarded; "/annum" is its missing
slash-separated sibling. "annum" is not a substring of any pay-cadence word.

Run:
    pytest tests/test_salary_slash_annum_annual_guard.py
    python3 tests/test_salary_slash_annum_annual_guard.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import _salary_score  # noqa: E402
from config import SALARY_FLOOR   # noqa: E402


# --- false-positive cases: "/annum" + pay-frequency note (the bugs) ---

def test_slash_annum_biweekly_above_floor_not_inflated():
    """$90,000/annum, biweekly -> 90000 (annual), NOT 90000*26=2.34M."""
    score = _salary_score({"salary": "$90,000/annum, biweekly"})
    assert score == 1.0, f"expected 1.0 (90k >= floor), got {score} — biweekly multiplier likely fired"


def test_slash_annum_biweekly_below_floor_not_inflated():
    """$42,000/annum, paid biweekly -> ~0.76 (below floor), NOT 1.0 from 42k*26=1.09M."""
    score = _salary_score({"salary": "$42,000/annum, paid biweekly"})
    expected = max(0.0, 42_000 / SALARY_FLOOR)
    assert abs(score - expected) < 0.01, (
        f"expected ~{expected:.3f} (42k below floor), got {score} — "
        "biweekly multiplier likely fired and inflated to 1.09M"
    )


def test_slash_annum_semimonthly_not_inflated():
    """$120,000/annum, semimonthly -> 120000 (annual), NOT 120000*24=2.88M."""
    score = _salary_score({"salary": "$120,000/annum, semimonthly"})
    assert score == 1.0, f"expected 1.0 (120k >= floor), got {score}"


def test_slash_annum_weekly_not_inflated():
    """$95,000/annum, weekly -> 95000 (annual), NOT 95000*52=4.94M."""
    score = _salary_score({"salary": "$95,000/annum, weekly"})
    assert score == 1.0, f"expected 1.0 (95k >= floor), got {score}"


def test_slash_annum_space_variant_not_inflated():
    """$80,000 /annum, biweekly -> 80000 (annual) with space before slash."""
    score = _salary_score({"salary": "$80,000 /annum, biweekly"})
    assert score == 1.0, f"expected 1.0 (80k >= floor), got {score}"


# --- regression guards: sibling forms must still fire ---

def test_per_annum_prose_still_guarded():
    """Existing 'per annum' guard must still work after /annum addition."""
    score = _salary_score({"salary": "$75,000 per annum, paid biweekly"})
    assert score == 1.0, f"expected 1.0 (75k annual via per annum), got {score}"


def test_genuine_biweekly_still_multiplied():
    """$3000 biweekly (no /annum) -> 3000*26=78000 -> above floor -> 1.0"""
    score = _salary_score({"salary": "$3,000 biweekly"})
    assert score == 1.0, f"expected 1.0 (3k biweekly = 78k annual), got {score}"


def test_genuine_hourly_still_multiplied():
    """$75/hour (no /annum) -> 75*2080=156000 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$75 per hour"}) == 1.0


# --- self-test runner ---

if __name__ == "__main__":
    tests = [
        test_slash_annum_biweekly_above_floor_not_inflated,
        test_slash_annum_biweekly_below_floor_not_inflated,
        test_slash_annum_semimonthly_not_inflated,
        test_slash_annum_weekly_not_inflated,
        test_slash_annum_space_variant_not_inflated,
        test_per_annum_prose_still_guarded,
        test_genuine_biweekly_still_multiplied,
        test_genuine_hourly_still_multiplied,
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
