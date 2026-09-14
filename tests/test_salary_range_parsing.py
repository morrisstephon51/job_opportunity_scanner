"""
Regression tests for _salary_score range parsing (placeholder low bound + shared 'k').

The scorer read only the FIRST number in a salary string, which misfired on two
common real-world formats produced by ZipRecruiter/Indeed:

  1. Placeholder / negotiable low bound — "$0 - $200k DOE". The low bound is a
     literal 0, so the role scored as if it paid nothing (0/floor ≈ 0.0) and was
     effectively buried, even though it tops out at $200k.

  2. Shared 'k' on the range — "$85 - $110k". The 'k' rides only the upper bound,
     so the lower bound read as $85 (not $85,000) and cratered the score to ~0.

Fix (scorer.py, _salary_score only): parse every figure with its optional 'k',
apply a range's shared 'k' to a bare sub-1000 bound, and use the first figure as
the conservative low — falling back to the next POSITIVE figure only when the low
is a placeholder 0. A real low bound is never overridden, so trailing numbers
("401k" match, PTO weeks, a stray year) still cannot hijack the amount.

Self-contained: runs under pytest OR directly with
`python3 tests/test_salary_range_parsing.py` (the repo has no CI / test deps).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SALARY_FLOOR  # noqa: E402
from scorer import _salary_score  # noqa: E402


def _s(salary):
    return round(_salary_score({"salary": salary}), 6)


# (salary string, expected score, note)
CASES = [
    # --- the two bugs this file exists to lock down ---
    ("$0 - $200k DOE", 1.0, "placeholder $0 low no longer buries a $200k ceiling"),
    ("$85 - $110k", 1.0, "shared 'k' on the upper bound applies to the lower ($85k)"),
    ("$85 - $110k", 1.0, "-> low bound reads as $85,000, clears the floor"),

    # --- ranges with an explicit-below-floor low still score proportionally ---
    ("$0 - $80k", 1.0, "placeholder 0 -> ceiling $80k clears floor"),
    ("$30k - $120k", round(30_000 / SALARY_FLOOR, 6), "real low bound $30k is honored, not the ceiling"),

    # --- regression guards: stray numbers must NOT override a real low bound ---
    ("$50,000 (401k match)", round(50_000 / SALARY_FLOOR, 6), "401k benefit does not hijack a real $50k low"),
    ("$60,000 in 2026", 1.0, "a stray year is not treated as the salary"),
    ("$75k - $95k", 1.0, "ordinary k-range unchanged"),

    # --- everything below is unchanged behavior, re-asserted for safety ---
    ("$85k", 1.0, "single k figure"),
    ("$40k", round(40_000 / SALARY_FLOOR, 6), "below-floor k is proportional"),
    ("$85,000 - $110,000", 1.0, "comma range unchanged"),
    ("$30/hr", 1.0, "hourly annualizes (30*2080)"),
    ("$5,000/month", 1.0, "monthly annualizes (5000*12)"),
    ("$1,500/week", 1.0, "weekly annualizes (1500*52)"),
    ("", 0.5, "unlisted salary stays neutral"),
    ("DOE", 0.5, "no digits -> neutral"),
    ("$0", 0.5, "a lone placeholder 0 is uninformative -> neutral, not 0.0"),
]


def test_salary_range_cases():
    failures = []
    for salary, expected, note in CASES:
        got = _s(salary)
        if abs(got - expected) > 1e-6:
            failures.append(f"  {salary!r}: expected {expected}, got {got}  ({note})")
    assert not failures, "salary range parsing regressions:\n" + "\n".join(failures)


if __name__ == "__main__":
    test_salary_range_cases()
    print(f"  ok — {len(CASES)} salary range cases passed")
