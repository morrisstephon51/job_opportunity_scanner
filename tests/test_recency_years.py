"""
Tests for the is_recent() "X years ago" recency gap.

is_recent() gained "X weeks ago" / "X months ago" branches but stopped there.
A "1 year ago" / "2 years ago" repost (common for evergreen or re-listed roles)
matched none of the numeric branches, was not an ISO date, and fell through to
the include-by-default `return True` — so a 365+ day posting scored as fresh and
slipped past the MAX_DAYS_OLD = 7 filter. This is the exact same class of miss
the weeks/months fix called out, just one unit larger.

Fix (scorer.py, is_recent only): convert years->days (x365) and compare to
MAX_DAYS_OLD, mirroring the existing days/weeks/months branches.

Assertions derive the window from config.MAX_DAYS_OLD, so they hold if the
window is retuned. Different function than the open scorer PR (#25 _salary_score)
— no overlap, no merge conflict.

The repo has no CI; run either way:
    pytest tests/test_recency_years.py
    python tests/test_recency_years.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import is_recent, filter_and_score  # noqa: E402
from config import MAX_DAYS_OLD  # noqa: E402


def _recent(posted):
    return is_recent({"posted_date": posted})


# --- regression guards: existing behavior must not change ---
def test_days_within_window_still_recent():
    assert _recent(f"{MAX_DAYS_OLD} days ago") is True


def test_two_months_still_filtered():
    assert _recent("2 months ago") is False


# --- the fix: years beyond the window are now filtered ---
def test_one_year_is_filtered():
    # 1 year = 365 days — far past any realistic MAX_DAYS_OLD.
    assert _recent("1 year ago") is False


def test_two_years_is_filtered():
    assert _recent("2 years ago") is False


def test_singular_year_is_filtered():
    # "a year ago" has no digit, so it legitimately stays benefit-of-the-doubt;
    # but "1 year ago" (digit form) must be caught.
    assert _recent("1 year ago") is False


def test_years_math_matches_equivalent_days():
    # 1 year = 365 days; must agree with the equivalent "365 days ago".
    assert _recent("1 year ago") == (365 <= MAX_DAYS_OLD)
    assert _recent("1 year ago") == _recent("365 days ago")


# --- benefit-of-doubt for genuinely unknown / digitless formats is preserved ---
def test_digitless_year_still_included():
    assert _recent("posted this year") is True
    assert _recent("a year ago") is True


def test_iso_date_still_parsed_not_hijacked_by_year_branch():
    # An ISO timestamp carries no "year" word, so the new branch must not touch it.
    assert _recent("2020-01-15") is False   # ~years old -> filtered by ISO branch
    from datetime import datetime, timezone
    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert _recent(today_iso) is True


def test_filter_drops_stale_years_job_end_to_end():
    jobs = [
        {"title": "AI Educator", "posted_date": "3 days ago", "location": "Remote"},
        {"title": "AI Educator", "posted_date": "1 year ago", "location": "Remote"},
    ]
    kept_dates = [j["posted_date"] for j in filter_and_score(jobs)]
    assert "3 days ago" in kept_dates
    assert "1 year ago" not in kept_dates


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
