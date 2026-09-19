"""
Tests for the bare `"daily" in raw` substring-collision fix (#41).

PR #40 added the day-rate cadence branch with `"daily" in raw`. That bare
substring fires on non-cadence salary descriptions like "$75,000 + daily pay
advance" or "DailyPay app access", multiplying an annual salary by 260x and
causing a false salary-floor pass. Same class as PR #31 (bare "hour") and PR
#29 (bare "week"/"month").

Fix: replace bare `"daily"` with `re.search(r"\\d[\\s,.]*daily\\b", raw)` --
requires a digit immediately before "daily" (with only whitespace/commas/dots
between), so "$400 daily" matches while descriptive uses do not.

The repo has no CI; run either way:
    pytest tests/test_salary_daily_bare_substring.py
    python tests/test_salary_daily_bare_substring.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import _salary_score  # noqa: E402
from config import SALARY_FLOOR   # noqa: E402


# --- true day-rate formats must still score correctly ---

def test_slash_day_scores_correctly():
    """$400/day -> 400 * 260 = 104,000 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$400/day"}) == 1.0


def test_per_day_scores_correctly():
    """$300 per day -> 300 * 260 = 78,000 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$300 per day"}) == 1.0


def test_digit_space_daily_scores_correctly():
    """$250 daily -> 250 * 260 = 65,000 -> above floor -> 1.0"""
    assert _salary_score({"salary": "$250 daily"}) == 1.0


def test_decimal_daily_scores_correctly():
    """$400.00 daily -> digit before daily -> 400 * 260 = 104,000 -> 1.0"""
    assert _salary_score({"salary": "$400.00 daily"}) == 1.0


def test_range_daily_scores_correctly():
    """$300-400 daily -> first number 300, 300 * 260 = 78,000 -> 1.0"""
    assert _salary_score({"salary": "$300-400 daily"}) == 1.0


# --- bare "daily" in non-cadence context must NOT inflate salary ---

def test_daily_pay_advance_does_not_inflate():
    """$75,000 + daily pay advance -> should score as annual $75k, not $75k*260"""
    score = _salary_score({"salary": "$75,000 + daily pay advance option"})
    expected = min(1.0, 75_000 / SALARY_FLOOR)
    assert score == pytest_approx(expected, abs=0.01), (
        f"Expected ~{expected:.2f} (annual $75k), got {score} — "
        "bare 'daily' inflated an annual salary by 260x"
    )


def test_dailypay_app_does_not_inflate():
    """$50,000 annual + DailyPay app -> 'daily' in 'dailypay', must not fire"""
    score = _salary_score({"salary": "$50,000 annual, DailyPay app access"})
    expected = min(1.0, 50_000 / SALARY_FLOOR)
    assert score == pytest_approx(expected, abs=0.01), (
        f"Expected ~{expected:.2f}, got {score}"
    )


def test_daily_duties_does_not_inflate():
    """$60,000 — 'daily duties' in description leaking into salary field"""
    score = _salary_score({"salary": "$60,000 — daily duties and check-ins"})
    expected = min(1.0, 60_000 / SALARY_FLOOR)
    assert score == pytest_approx(expected, abs=0.01)


# ---------------------------------------------------------------------------
# Tiny self-runner so the file works without pytest installed
# ---------------------------------------------------------------------------
def pytest_approx(value, abs=0.01):
    class Approx:
        def __eq__(self, other):
            return builtins_abs(other - value) <= abs
    import builtins
    builtins_abs = builtins.abs
    return Approx()


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        raise SystemExit(1)
