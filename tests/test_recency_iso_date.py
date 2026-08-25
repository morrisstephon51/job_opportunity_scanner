"""
Tests for the is_recent() ISO-date branch.

The ISO branch was dead code from two bugs:
  1. raw[:len(fmt)] truncated the date. A format like "%Y-%m-%d" is 8 chars but
     matches a 10-char date ("%Y" is 2 format chars, 4 digits), so strptime was
     handed "2026-08-" and always raised ValueError.
  2. raw is lower()-cased earlier in is_recent, so the literal 'T'/'Z' in the
     formats never matched a real "...T...Z" timestamp.
Both paths fell through to the include-by-default `return True`, so any job with
an ISO posted_date skipped the MAX_DAYS_OLD filter — a 2020 posting scored as
fresh.

Fix (scorer.py, is_recent only): match the full re-uppercased string with
strptime instead of the truncated lowercase slice.

Assertions derive the window from config.MAX_DAYS_OLD and build dates relative
to "now", so they hold if the window is retuned. Different function/branch than
the open scorer PRs (#7 _location, #8 _title, #9 _salary, #10 TITLE_SIGNALS,
#11 weeks/months relative dates) — no overlap, no merge conflict.

The repo has no CI; run either way:
    pytest tests/test_recency_iso_date.py
    python tests/test_recency_iso_date.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import is_recent, filter_and_score  # noqa: E402
from config import MAX_DAYS_OLD  # noqa: E402


def _recent(posted):
    return is_recent({"posted_date": posted})


def _iso_days_ago(days, suffix=""):
    d = datetime.now(timezone.utc) - timedelta(days=days)
    if suffix == "date":
        return d.strftime("%Y-%m-%d")
    if suffix == "z":
        return d.strftime("%Y-%m-%dT%H:%M:%SZ")
    return d.strftime("%Y-%m-%dT%H:%M:%S")


# --- the fix: a genuinely old ISO date is now filtered out ---
def test_old_plain_iso_date_is_filtered():
    # Was the core bug: this used to fall through to True and score as fresh.
    assert _recent("2020-01-01") is False


def test_old_iso_timestamp_with_z_is_filtered():
    assert _recent("2020-01-01T10:30:00Z") is False


def test_old_iso_timestamp_no_z_is_filtered():
    assert _recent("2019-06-15T08:00:00") is False


# --- fresh ISO dates in every supported shape stay recent ---
def test_fresh_plain_iso_date_is_recent():
    assert _recent(_iso_days_ago(1, "date")) is True


def test_fresh_iso_timestamp_is_recent():
    assert _recent(_iso_days_ago(1)) is True


def test_fresh_iso_timestamp_with_z_is_recent():
    assert _recent(_iso_days_ago(1, "z")) is True


# --- window boundary is honored, derived from config ---
def test_just_inside_window_is_recent():
    assert _recent(_iso_days_ago(MAX_DAYS_OLD, "date")) is True


def test_just_outside_window_is_filtered():
    assert _recent(_iso_days_ago(MAX_DAYS_OLD + 2, "date")) is False


# --- benefit-of-doubt for genuinely unparseable input is preserved ---
def test_unknown_format_still_included():
    assert _recent("garbled-not-a-date") is True
    assert _recent("") is True


def test_filter_drops_stale_iso_job_end_to_end():
    fresh = _iso_days_ago(2, "z")
    jobs = [
        {"title": "AI Educator", "posted_date": fresh, "location": "Remote"},
        {"title": "AI Educator", "posted_date": "2020-01-01T00:00:00Z", "location": "Remote"},
    ]
    kept = [j["posted_date"] for j in filter_and_score(jobs)]
    assert fresh in kept
    assert "2020-01-01T00:00:00Z" not in kept


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
