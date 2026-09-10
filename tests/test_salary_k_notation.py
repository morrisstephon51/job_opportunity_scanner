"""
Tests for scorer._salary_score — focused on the "$85k" thousands-suffix bug.

The repo has no CI; run either way:
    pytest tests/test_salary_score.py
    python tests/test_salary_score.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import _salary_score, score_job  # noqa: E402
from config import SALARY_FLOOR  # noqa: E402


def _s(salary):
    return _salary_score({"salary": salary})


def test_k_notation_reads_as_thousands():
    # The bug: "$85k" was read as 85 dollars -> ~0.0015. Now it is 85,000.
    assert _s("$85k") == 1.0
    assert _s("$90k - $120k") == 1.0
    assert _s("80K/year") == 1.0
    assert _s("$100k+") == 1.0


def test_below_floor_k_is_proportional():
    # $40k is real money but below the $55k floor -> proportional, not ~0.
    assert abs(_s("$40k") - (40_000 / SALARY_FLOOR)) < 1e-6


def test_plain_and_comma_notation_unchanged():
    assert _s("$85,000 - $110,000") == 1.0
    assert abs(_s("$50,000/year") - (50_000 / SALARY_FLOOR)) < 1e-6


def test_hourly_unchanged():
    assert _s("$60/hr") == 1.0          # 60 * 2080 = 124,800
    assert _s("$28.50/hour") == 1.0     # 28.50 * 2080 = 59,280


def test_unlisted_is_neutral():
    assert _s("") == 0.5
    assert _s("DOE") == 0.5
    assert _s(None) == 0.5


def test_401k_does_not_hijack_the_amount():
    # First number wins; the "401k" must not turn $50,000 into millions.
    assert abs(_s("$50,000 (401k match)") - (50_000 / SALARY_FLOOR)) < 1e-6


def test_score_job_reason_reflects_real_k_salary():
    # End-to-end: a "$95k" AI trainer role should read salary as meeting the
    # floor, not "below floor or unlisted".
    job = {
        "title": "AI Training Specialist",
        "description": "instructional design, digital learning",
        "location": "Chicago, IL",
        "salary": "$95k",
    }
    score, reason = score_job(job)
    assert "salary meets floor" in reason
    assert "below floor" not in reason
    assert score >= 8


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(fns) - failures}/{len(fns)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run())
