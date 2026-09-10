r"""
Tests for the is_recent() "X+ days ago" recency gap.

is_recent() parsed relative day counts with r"(\d+)\s+day", which requires
whitespace immediately after the digits. Indeed's most common stale-listing
label is "Posted 30+ days ago" — the "+" sits between the number and the
space, so the regex never matched. Execution fell through to the
include-by-default `return True`, and 30/45/60+ day postings were scored as
if fresh, past the MAX_DAYS_OLD = 7 window.

Fix (scorer.py, is_recent only): allow an optional "+" between the number and
"day" — r"(\d+)\+?\s*day" — so "30+ days ago" is filtered exactly like
"30 days ago".

Assertions derive the window from config.MAX_DAYS_OLD, so they hold if the
window is retuned. Different line + different case than the open recency PRs
(#11 weeks/months, #12 ISO dates both leave the day regex untouched) and the
scorer PRs (#7 _location, #8 _title, #9 _salary, #10 TITLE_SIGNALS) — no
overlap, no merge conflict.

The repo has no CI; run either way:
    pytest tests/test_recency_plus_days.py
    python tests/test_recency_plus_days.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import is_recent, filter_and_score  # noqa: E402
from config import MAX_DAYS_OLD  # noqa: E402


def _recent(posted):
    return is_recent({"posted_date": posted})


# --- regression guards: existing plain "days" behavior must not change ---
def test_plain_days_within_window_still_recent():
    assert _recent(f"{MAX_DAYS_OLD} days ago") is True


def test_plain_days_beyond_window_still_filtered():
    assert _recent(f"{MAX_DAYS_OLD + 3} days ago") is False


def test_recent_days_unaffected():
    assert _recent("2 days ago") is True


# --- the fix: "X+ days ago" beyond the window is now filtered ---
def test_thirty_plus_days_is_filtered():
    # Indeed's canonical stale label — the exact case from the bug report.
    assert _recent("30+ days ago") is False


def test_forty_five_plus_days_is_filtered():
    assert _recent("45+ days ago") is False


def test_plus_matches_plain_beyond_window():
    # "30+ days ago" must agree with the equivalent "30 days ago".
    assert _recent("30+ days ago") == _recent("30 days ago")


def test_plus_within_window_still_recent():
    # A small "+" count inside the window stays recent, mirroring plain days.
    assert _recent("1+ days ago") == (1 <= MAX_DAYS_OLD)
    assert _recent("1+ days ago") is True


def test_no_space_plus_variant_filtered():
    # Defensive: "30+days ago" (no space) is handled by \s* too.
    assert _recent("30+days ago") is False


# --- benefit-of-doubt for genuinely unknown formats is preserved ---
def test_unknown_format_still_included():
    assert _recent("sometime last quarter") is True
    assert _recent("") is True


def test_filter_drops_stale_plus_days_job_end_to_end():
    jobs = [
        {"title": "AI Educator", "posted_date": "2 days ago", "location": "Remote"},
        {"title": "AI Educator", "posted_date": "30+ days ago", "location": "Remote"},
    ]
    kept_dates = [j["posted_date"] for j in filter_and_score(jobs)]
    assert "2 days ago" in kept_dates
    assert "30+ days ago" not in kept_dates


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
