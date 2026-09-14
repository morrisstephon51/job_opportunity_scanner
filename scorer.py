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
    # A salary is usually a range, so parse every figure (each with its optional
    # 'k' thousands suffix) instead of blindly trusting the first number. Reading
    # only the first number misfired on two common real-world formats:
    #   • "$0 - $200k DOE" — the low bound is a placeholder 0 (negotiable / DOE),
    #     so the role scored as if it paid nothing and got buried despite topping
    #     out at $200k.
    #   • "$85 - $110k" — the 'k' rides only the upper bound, so the lower bound
    #     read as $85 (not $85k) and cratered the score.
    tokens = re.findall(r"(\d+(?:\.\d+)?)\s*(k)?", raw)
    if not tokens:
        return 0.5  # no salary listed — neutral

    any_k = any(k for _, k in tokens)

    def to_dollars(num: str, k: str) -> float:
        val = float(num)
        if k:                          # explicit "k" -> thousands
            val *= 1000
        elif any_k and val < 1000:     # bare bound sharing a range's "k" ("85 - 110k")
            val *= 1000
        return val

    # Score off the conservative low bound = the first figure. Only when that low
    # is a placeholder 0 do we fall back to the next positive figure so the
    # ceiling still counts. A real low bound is never overridden, so trailing
    # numbers ("401k" match, PTO weeks, a year) can't hijack the amount.
    low = to_dollars(*tokens[0])
    if low <= 0:
        for num, k in tokens[1:]:
            candidate = to_dollars(num, k)
            if candidate > 0:
                low = candidate
                break
    if low <= 0:
        return 0.5  # only placeholders present — uninformative, treat as unlisted

    # Normalize to an annual figure before comparing to the floor.
    if "hour" in raw or "/hr" in raw or "per hour" in raw:
        low *= 2080
    elif "week" in raw or "/wk" in raw or "per week" in raw:
        low *= 52
    elif "month" in raw or "/mo" in raw or "per month" in raw:
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
