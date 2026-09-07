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
    m = re.search(r"(\d+)\s+day", raw)
    if m:
        return int(m.group(1)) <= MAX_DAYS_OLD
    # Try ISO date
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            posted = datetime.strptime(raw[:len(fmt)], fmt).replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - posted
            return delta.days <= MAX_DAYS_OLD
        except ValueError:
            continue
    return True  # unknown format — include


def _title_score(job: dict) -> float:
    title = (job.get("title") or "").lower()
    hits = sum(1 for s in TITLE_SIGNALS if s in title)
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
    if "chicago" in loc or "il" in loc:
        return 1.0
    if "hybrid" in loc:
        return 0.7
    return 0.2  # unknown/other location


def _salary_score(job: dict) -> float:
    raw = (job.get("salary") or "").lower().replace(",", "")
    nums = re.findall(r"\d+", raw)
    if not nums:
        return 0.5  # no salary listed — neutral
    low = int(nums[0])
    # Normalize to an annual figure before comparing to the floor.
    if "hour" in raw or "/hr" in raw or "per hour" in raw:
        low = low * 2080
    elif "week" in raw or "/wk" in raw or "per week" in raw:
        low = low * 52
    elif "month" in raw or "/mo" in raw or "per month" in raw:
        low = low * 12
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
