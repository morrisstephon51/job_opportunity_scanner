"""
Tests for the is_recent() weeks/months recency gap.

is_recent() parsed "X days ago" with a numeric "(digits) day" regex but had
no branch for "X weeks ago" / "X months ago". Those strings matched none of the
branches and fell through to the include-by-default `return True`, so stale
postings ("6 weeks ago" = 42 days, "2 months ago" = ~60 days) slipped past the
MAX_DAYS_OLD = 7 filter and got scored as if fresh.

Fix (scorer.py, is_recent only): convert weeks->days (x7) and months->days
(x30) and compare to MAX_DAYS_OLD, mirroring the existing "days" branch.

Assertions derive the window from config.MAX_DAYS_OLD, so they hold if the
window is retuned. Different file + different function than the open scorer
PRs (#7 _location, #8 _title, #9 _salary, #10 config TITLE_SIGNALS) — no
overlap, no merge conflict.

The repo has no CI; run either way:
    pytest tests/test_recency_weeks_months.py
    python tests/test_recency_weeks_months.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import is_recent, filter_and_score  # noqa: E402
from config import MAX_DAYS_OLD  # noqa: E402


def _recent(posted):
    return is_recent({"posted_date": posted})


# --- regression guards: existing "days" behavior must not change ---
def test_days_within_window_still_recent():
    assert _recent(f"{MAX_DAYS_OLD} days ago") is True


def test_days_beyond_window_still_filtered():
    assert _recent(f"{MAX_DAYS_OLD + 3} days ago") is False


# --- the fix: weeks/months beyond the window are now filtered ---
def test_six_weeks_is_filtered():
    # 6 weeks = 42 days — the exact case from the bug report.
    assert _recent("6 weeks ago") is False


def test_three_weeks_is_filtered():
    assert _recent("3 weeks ago") is False


def test_one_month_is_filtered():
    assert _recent("1 month ago") is False


def test_two_months_is_filtered():
    assert _recent("2 months ago") is False


def test_one_week_boundary_matches_day_math():
    # 1 week = 7 days; must agree with the equivalent "7 days ago".
    assert _recent("1 week ago") == (7 <= MAX_DAYS_OLD)
    assert _recent("1 week ago") == _recent("7 days ago")


# --- benefit-of-doubt for genuinely unknown formats is preserved ---
def test_unknown_format_still_included():
    assert _recent("sometime last quarter") is True
    assert _recent("") is True


def test_filter_drops_stale_weeks_job_end_to_end():
    jobs = [
        {"title": "AI Educator", "posted_date": "2 days ago", "location": "Remote"},
        {"title": "AI Educator", "posted_date": "8 weeks ago", "location": "Remote"},
    ]
    kept_dates = [j["posted_date"] for j in filter_and_score(jobs)]
    assert "2 days ago" in kept_dates
    assert "8 weeks ago" not in kept_dates


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
