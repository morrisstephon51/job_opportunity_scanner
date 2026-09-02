"""
Consolidated regression tests for the scorer/config fixes integrated on
fix/scorer-consolidated. Supersedes the per-PR test files by covering all
seven fixes together, proving they compose without conflict.

The repo has no CI; run either way:
    pytest tests/test_scorer_consolidated.py
    python3 tests/test_scorer_consolidated.py

Fixes covered (original issue/PR numbers):
  #7  _location_score  — "il" matched as a whole token, not a substring
  #8  _title_score     — TITLE_SIGNALS matched as whole words, not substrings
  #9  _salary_score    — "$85k" read as 85,000 not 85
  #10 config           — "trainer" added to TITLE_SIGNALS
  #11 is_recent        — "X weeks/months ago" filtered past the window
  #12 is_recent        — ISO posted_date honored (branch was dead code)
  #13 is_recent        — "30+ days ago" filtered like "30 days ago"
  #17 _salary_score    — weekly/monthly pay periods normalized to annual
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import _title_score, _location_score, _salary_score, is_recent  # noqa: E402
from config import TITLE_SIGNALS, MAX_DAYS_OLD, SALARY_FLOOR  # noqa: E402

failures = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


# --- #8: title token matching ---
# Control: a title with no signal words at all scores 0.
check("#8 no-signal title scores 0", _title_score({"title": "Retail Sales Associate"}) == 0.0)
check("#8 'ai' does not match inside 'retail'", _title_score({"title": "Retail Clerk"}) == 0.0)
check("#8 'ai' does not match inside 'maintenance/repair'",
      _title_score({"title": "Maintenance Repair Worker"}) == 0.0)
# Real signal words still score.
check("#8 real 'AI Educator' scores > 0", _title_score({"title": "AI Educator"}) > 0.0)

# --- #10: trainer signal ---
check("#10 'trainer' in TITLE_SIGNALS", "trainer" in TITLE_SIGNALS)
check("#10 'training' still present (added, not swapped)", "training" in TITLE_SIGNALS)
check("#10 'Corporate Trainer' now scores > control",
      _title_score({"title": "Corporate Trainer"}) > _title_score({"title": "Warehouse Picker"}))

# --- #7: location token matching ---
check("#7 'il' does not match 'Nashville, TN'",
      _location_score({"location": "Nashville, TN"}) == 0.2)
check("#7 'Philadelphia, PA' not treated as IL",
      _location_score({"location": "Philadelphia, PA"}) == 0.2)
check("#7 real 'Chicago, IL' scores 1.0",
      _location_score({"location": "Chicago, IL"}) == 1.0)
check("#7 'Springfield, IL' token match scores 1.0",
      _location_score({"location": "Springfield, IL"}) == 1.0)

# --- #9 + #17: salary k-notation and pay-period normalization ---
check("#9 '$85k' reads as 85,000 (>= floor)", _salary_score({"salary": "$85k"}) == 1.0)
check("#9 '$90k - $120k' >= floor", _salary_score({"salary": "$90k - $120k"}) == 1.0)
check("#9 '80K/year' >= floor", _salary_score({"salary": "80K/year"}) == 1.0)
check("#17 '$30/hour' annualizes above floor", _salary_score({"salary": "$30/hour"}) == 1.0)
check("#17 '$5000/month' == $60k/yr >= floor", _salary_score({"salary": "$5000/month"}) == 1.0)
check("#17 '$1500/week' annualizes above floor", _salary_score({"salary": "$1500/week"}) == 1.0)
check("#9 plain low salary '$20000' below floor",
      _salary_score({"salary": "$20000"}) < 1.0)
check("#9 no salary is neutral 0.5", _salary_score({"salary": ""}) == 0.5)

# --- #13: 30+ days ago ---
check("#13 '30+ days ago' is stale", is_recent({"posted_date": "Posted 30+ days ago"}) is False)
check("#13 '3 days ago' still recent", is_recent({"posted_date": "3 days ago"}) is True)

# --- #11: weeks/months ---
check("#11 '6 weeks ago' is stale", is_recent({"posted_date": "6 weeks ago"}) is False)
check("#11 '2 months ago' is stale", is_recent({"posted_date": "2 months ago"}) is False)

# --- #12: ISO date honored ---
old = (datetime.now(timezone.utc) - timedelta(days=MAX_DAYS_OLD + 30)).strftime("%Y-%m-%d")
fresh = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
old_iso = (datetime.now(timezone.utc) - timedelta(days=MAX_DAYS_OLD + 30)).strftime("%Y-%m-%dT%H:%M:%SZ")
check("#12 old ISO date is stale", is_recent({"posted_date": old}) is False)
check("#12 fresh ISO date is recent", is_recent({"posted_date": fresh}) is True)
check("#12 old ISO timestamp (with T/Z) is stale", is_recent({"posted_date": old_iso}) is False)

# --- baseline sanity ---
check("baseline: unknown date included", is_recent({"posted_date": ""}) is True)
check("baseline: 'today' included", is_recent({"posted_date": "Posted today"}) is True)

print()
if failures:
    print(f"{len(failures)} FAILURE(S): " + ", ".join(failures))
    sys.exit(1)
print("ALL PASSED")
