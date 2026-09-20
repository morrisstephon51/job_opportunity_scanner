"""
Pure-Python job fit scorer. No API calls — fully free.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from config import (
    SALARY_FLOOR, LOCATIONS, TITLE_SIGNALS, SEARCH_KEYWORDS,
    AGENCY_BLOCKLIST, MAX_DAYS_OLD, SCORE_WEIGHTS, ALERT_SCORE_THRESHOLD,
)


def is_agency(job: dict) -> bool:
    company = (job.get("company") or "").lower()
    return any(block in company for block in AGENCY_BLOCKLIST)


def is_recent(job: dict) -> bool:
    """Return True if posted within MAX_DAYS_OLD days. Passes through if date unknown."""
    raw = job.get("posted_date") or ""
    if not raw:
        return True  # give benefit of the doubt
    raw = raw.lower().strip()
    # Handle "X days ago" / "X hours ago" / "today" / "just posted"
    if any(x in raw for x in ("today", "just posted", "hours ago", "hour ago")):
        return True
    # Allow an optional "+" between the number and "day" so Indeed's most common
    # stale label, "30+ days ago", is filtered exactly like "30 days ago".
    # A bare r"(\d+)\s+day" never matched the "+" form, so 30/45/60+ day
    # postings fell through to the include-by-default return and scored as fresh.
    m = re.search(r"(\d+)\+?\s*day", raw)
    if m:
        return int(m.group(1)) <= MAX_DAYS_OLD
    # "X weeks ago" / "X months ago" — the day regex above never matches these,
    # so without these branches they fall through to include-by-default and
    # stale postings (e.g. "6 weeks ago" = 42 days) slip past MAX_DAYS_OLD.
    m = re.search(r"(\d+)\s+week", raw)
    if m:
        return int(m.group(1)) * 7 <= MAX_DAYS_OLD
    m = re.search(r"(\d+)\s+month", raw)
    if m:
        return int(m.group(1)) * 30 <= MAX_DAYS_OLD
    # Try ISO date. This branch was dead code from two bugs: (1) raw[:len(fmt)]
    # truncated the date because a spec like "%Y-%m-%d" is 8 format chars but
    # matches a 10-char date, so strptime always raised; (2) raw was lower()-cased
    # above, so the literal 'T'/'Z' in the formats never matched. Match the full,
    # re-uppercased string instead — otherwise a 2020 job scored as if fresh.
    iso = raw.upper()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            posted = datetime.strptime(iso, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        return (datetime.now(timezone.utc) - posted).days <= MAX_DAYS_OLD
    return True  # unknown format — include


def _title_score(job: dict) -> float:
    title = (job.get("title") or "").lower()
    # Match each signal as a whole word/phrase, not a bare substring. Otherwise
    # short signals like "ai" match inside unrelated titles (retAIl,
    # mAIntenance, repAIr, hAIr), inflating the heaviest-weighted score.
    hits = sum(1 for s in TITLE_SIGNALS if re.search(rf"\b{re.escape(s)}\b", title))
    return min(hits / 3, 1.0)  # cap at 1.0; 3+ hits = perfect


def _keyword_score(job: dict) -> float:
    text = " ".join([
        job.get("title") or "",
        job.get("description") or "",
    ]).lower()
    hits = sum(1 for kw in SEARCH_KEYWORDS if kw.lower() in text)
    return min(hits / 4, 1.0)  # 4+ keyword hits = perfect


def _location_score(job: dict) -> float:
    loc = (job.get("location") or "").lower()
    if "remote" in loc:
        return 1.0
    # Match the Illinois state code as a whole token, not a bare substring.
    # `"il" in loc` wrongly matched Nashville, Philadelphia, Milwaukee, Mobile,
    # etc. ("-ville"/"mil"/"phil"/"bil" all contain "il"), inflating their score.
    if "chicago" in loc or re.search(r"\bil\b", loc) or "illinois" in loc:
        return 1.0
    if "hybrid" in loc:
        return 0.7
    return 0.2  # unknown/other location


def _salary_score(job: dict) -> float:
    raw = (job.get("salary") or "").lower().replace(",", "")
    # Grab the first number, keeping any 'k' thousands suffix. A bare r"\d+"
    # reads "$85k" as 85 dollars, scoring a strong salary far below floor;
    # capture the "k" so "$85k" resolves to 85,000.
    m = re.search(r"(\d+(?:\.\d+)?)\s*(k)?", raw)
    if not m:
        return 0.5  # no salary listed — neutral
    low = float(m.group(1))
    if m.group(2):  # "k" suffix -> thousands
        low *= 1000
    # Normalize to an annual figure before comparing to the floor.
    # Check compound pay cadences BEFORE the bare "week"/"month" branches. A bare
    # `in` substring test is the recurring collision bug this file already fixed
    # for "il"/Nashville and "ai"/retail: it reads "biweekly" as weekly (x52, ~2x
    # too HIGH -> an underpaid role can false-clear the floor and fire an alert)
    # and "semimonthly" as monthly (x12, ~2x too LOW -> a genuine above-floor role
    # is scored under the floor and buried). Bi-weekly pays 26 periods/yr and
    # semi-monthly 24/yr; match those specific forms first so the generic branches
    # below only ever see true weekly/monthly strings. (Municipal/county postings
    # -- Cook County included -- routinely quote pay "Bi-weekly".)
    # Guard all three orthographic forms of "bi-weekly" before the generic
    # "weekly" branch: "biweekly", "bi-weekly", and "bi weekly" (space, common
    # on municipal/county job boards -- Cook County included). Without the space
    # form, "bi weekly" falls through to "weekly" x52, doubling the multiplier.
    # Same fix applied to "semi monthly" -> semimonthly x24 (else monthly x12,
    # a 0.5x undercount that buries above-floor roles). See issue #32.
    # Guard: explicit per-year markers mean the amount is already annual — skip all
    # frequency multipliers. Without this guard, a salary string like
    # "$75,000/year, paid biweekly" picks up "biweekly" and applies x26, inflating
    # a $75k annual salary to $1.95M and falsely triggering ALERT_SCORE_THRESHOLD.
    # Same class as PR #31 (bare "hour") and PR #29 ("week"/"month"): subsidiary
    # salary text triggering the wrong cadence branch. PR #28 flagged this case as
    # out-of-scope ("annual figure carrying a cadence note"); filing now as #43.
    # Avoid bare "annual": it is a substring of "semi-annual" and would silently
    # skip the x24 semimonthly multiplier for a $2k semi-annual posting. Use only
    # unambiguous anchored forms. "yearly" is safe — it is not a substring of any
    # other pay-cadence word, unlike "annual" (inside "semi-annual"). See #45.
    # "per yr" is the abbreviated "per year" form (e.g. "$75k per yr, biweekly").
    # "/yr" already covers the slash form ("$80k/yr"); "per year" covers the full
    # space form — but the hybrid "per yr" matches neither and falls through to the
    # biweekly 26x branch, falsely inflating $75k → $1.95M. See #47.
    # "a year" is the natural-English equivalent of "per year" (e.g. "$42k a year,
    # paid biweekly"). Without this guard "a year" falls through to the biweekly
    # branch and multiplies by 26, inflating a below-floor annual salary to
    # a false ALERT. "a year" is not a substring of any cadence word. See #49.
    # "annually" is the adverbial form of "annual" (e.g. "$65k annually, biweekly").
    # Like "yearly" and "a year", it is not a substring of any cadence branch word
    # (biweekly, semimonthly, weekly, monthly, hourly, daily) — safe to add bare.
    # Note: "annual" alone is avoided because it appears inside "semi-annual"; but
    # "annually" as a cadence override does not exist in the codebase. See #51.
    # "a yr" is the abbreviated form of "a year" (e.g. "$42k a yr, biweekly"),
    # paralleling "per yr" vs "per year" (#47). Without this guard "a yr" falls
    # through to the biweekly branch and multiplies by 26, inflating $42k -> $1.09M.
    # "a yr" is not a substring of any cadence word. See #53.
    if ("/year" in raw or "/yr" in raw or "per year" in raw or "per yr" in raw
            or "per annum" in raw or "yearly" in raw or "a year" in raw
            or "annually" in raw or "a yr" in raw):
        pass  # amount already annual; no frequency multiplier needed
    elif "biweekly" in raw or "bi-weekly" in raw or "bi weekly" in raw:
        low *= 26
    elif "semimonthly" in raw or "semi-monthly" in raw or "semi monthly" in raw:
        low *= 24
    # Drop bare "hour" substring test: it fires on "flexible hours", "24-hour
    # on-call", "office hours" etc., inflating an annual salary by x2080 and
    # falsely clearing SALARY_FLOOR. Use anchored forms only, same approach as
    # PR #29 used for week/month.
    elif "/hour" in raw or "/hr" in raw or "per hour" in raw or "hourly" in raw or "per hr" in raw:
        low *= 2080
    # Drop bare "week"/"month" substring tests: they fire on compensation
    # descriptions like "3 weeks PTO" or "12 months health coverage", turning
    # an annual $48k salary into $48k * 52 = $2.5M/yr and falsely clearing
    # SALARY_FLOOR. Use anchored forms only: /week, /wk, per week, weekly
    # (and the month equivalents). Same substring-collision class already
    # fixed here for "il"/Nashville, "ai"/retail, "biweekly"/"semimonthly".
    # Day-rate contracts (e.g. "$400/day", "$250 per day", "$200 daily") must be
    # multiplied by 260 working days/year before comparing to SALARY_FLOOR.
    # Without this branch a $400/day rate scores as $400 annual (~0), burying
    # a $104k/yr consulting engagement. Same missing-cadence class as the
    # hourly/weekly/monthly siblings fixed in PRs #29/#31/#33/#37/#39.
    # Placed before the weekly branch to preserve specificity-first ordering.
    # Drop bare `"daily" in raw`: it fires on non-cadence descriptions like
    # "$75,000 + daily pay advance" or "DailyPay app access", inflating an
    # annual salary by 260x. Same class as PR #31 (bare "hour") and PR #29
    # (bare "week"/"month"). Require "daily" to be immediately preceded by a
    # digit (with only whitespace/commas/dots between) so "$400 daily" and
    # "$400.00 daily" still match while descriptive uses do not.
    elif "/day" in raw or "per day" in raw or re.search(r"\d[\s,.]*daily\b", raw):
        low *= 260
    elif "/week" in raw or "/wk" in raw or "per week" in raw or "weekly" in raw or "per wk" in raw:
        low *= 52
    elif "/month" in raw or "/mo" in raw or "per month" in raw or "monthly" in raw or "per mo" in raw:
        low *= 12
    return 1.0 if low >= SALARY_FLOOR else max(0.0, low / SALARY_FLOOR)


def score_job(job: dict) -> tuple[int, str]:
    """Return (fit_score 1-10, reason_string)."""
    w = SCORE_WEIGHTS
    t = _title_score(job)
    k = _keyword_score(job)
    l = _location_score(job)
    s = _salary_score(job)

    raw = (t * w["title_match"] + k * w["keyword_match"] +
           l * w["location_match"] + s * w["salary_match"])
    score = max(1, min(10, round(raw * 10)))

    reasons = []
    if t >= 0.67:
        reasons.append("strong title match")
    if k >= 0.5:
        reasons.append("multiple keyword hits")
    if l == 1.0:
        reasons.append("location fits")
    if s == 1.0:
        reasons.append("salary meets floor")
    elif s < 0.5:
        reasons.append("salary below floor or unlisted")
    reason = "; ".join(reasons) if reasons else "partial match"
    return score, reason


def filter_and_score(jobs: list[dict]) -> list[dict]:
    """Remove agencies + stale jobs, add fit_score and reason, sort descending."""
    results = []
    for job in jobs:
        if is_agency(job):
            continue
        if not is_recent(job):
            continue
        score, reason = score_job(job)
        results.append({**job, "fit_score": score, "score_reason": reason})
    results.sort(key=lambda j: j["fit_score"], reverse=True)
    return results
