"""
Consolidated regression tests for _salary_score pay-cadence annualization.

Background
----------
Pay cadence (annual / hourly / daily / weekly / monthly, plus the compound
bi-weekly and semi-monthly) is a *category* that shows up in many surface forms.
The scorer used to detect each form with a literal `"<form>" in raw` substring
test, which (a) is the substring-collision bug already fixed here for
"il"->Nashville and "ai"->retail, and (b) never terminates — every new spelling
("/yr", "per annum", "p.a.", "a year", "annualized", ...) needed its own branch
and its own one-off test file.

scorer.py now detects each cadence with a single anchored regex family. This one
file supersedes the per-string test files by covering the whole family at once:
  * PARITY   — every enumerated variant that had its own guard still resolves.
  * GENERAL  — un-enumerated variants the regex now catches for free (proof the
               category is handled, not just the spellings someone happened to file).
  * NEGATIVE — collision cases that must NOT trigger a cadence multiplier
               (descriptive "3 weeks PTO", "24-hour support", state code "PA",
               "semi-annually", "DailyPay", ...).

Self-contained: runs under pytest OR directly with
`python3 tests/test_salary_cadence.py` (the repo has no CI / test deps).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SALARY_FLOOR  # noqa: E402
from scorer import _salary_score  # noqa: E402

FLOOR = SALARY_FLOOR


def _score(salary):
    return round(_salary_score({"salary": salary}), 6)


def _prop(annual):
    """Expected proportional score for a below-floor annual figure."""
    return round(annual / FLOOR, 6)


# (salary string, expected score, note)
CASES = [
    # --- PARITY: already-annual guard wins over a co-occurring cadence note ---
    ("$75,000/year, paid biweekly", 1.0, "slash-year annual guard beats biweekly x26"),
    ("$75,000 per year, paid biweekly", 1.0, "per year"),
    ("$75,000 per yr, paid biweekly", 1.0, "per yr (#47)"),
    ("$42,000 a year, paid biweekly", _prop(42000), "a year, below floor, NOT x26 (#49)"),
    ("$42,000 a yr, biweekly", _prop(42000), "a yr (#53)"),
    ("$80,000 yearly, paid biweekly", 1.0, "yearly (#45)"),
    ("$65,000 annually, paid biweekly", 1.0, "annually (#51)"),
    ("$65,000 annualized, biweekly", 1.0, "annualized (#59)"),
    ("$90,000/annum, biweekly", 1.0, "/annum (#57)"),
    ("$85,000 p.a., paid biweekly", 1.0, "p.a. per-annum abbrev (#55)"),
    ("$90,000 per annum, paid biweekly", 1.0, "per annum"),

    # --- PARITY: compound cadences resolve to the right multiplier ---
    ("$2,300 biweekly", 1.0, "bi-weekly x26 = $59,800 clears floor (#28)"),
    ("$2,300 bi-weekly", 1.0, "hyphen form"),
    ("$2,300 bi weekly", 1.0, "space form (#32)"),
    ("$3,000 semimonthly", 1.0, "semi-monthly x24 = $72k clears floor"),
    ("$3,000 semi-monthly", 1.0, "hyphen form"),
    ("$3,000 semi monthly", 1.0, "space form (#32)"),

    # --- PARITY: base cadences (unchanged from the original scorer) ---
    ("$5,000/month", 1.0, "monthly x12 = $60k"),
    ("$1,500/week", 1.0, "weekly x52 = $78k"),
    ("$30/hr", 1.0, "hourly x2080 = $62.4k"),
    ("$60,000", 1.0, "annual at/above floor"),
    ("$40,000/year", _prop(40000), "below-floor annual scored proportionally"),
    ("$2,000/month", _prop(24000), "monthly below floor"),
    ("$800/week", _prop(41600), "weekly below floor"),
    ("", 0.5, "unlisted salary neutral"),

    # --- PARITY: day-rate + abbreviated hourly/weekly/monthly (#34/#36/#38) ---
    ("$400/day", 1.0, "day-rate x260 = $104k (#34)"),
    ("$250 per day", 1.0, "per day x260 = $65k"),
    ("$200 daily", _prop(52000), "digit-anchored daily x260 = $52k, below floor (#41)"),
    ("$30 per hr", 1.0, "per hr abbrev (#36)"),
    ("$900 per wk", _prop(46800), "per wk abbrev x52, below floor (#38)"),
    ("$4,500 per mo", _prop(54000), "per mo abbrev x12, below floor (#38)"),

    # --- GENERAL: un-enumerated variants the regex handles for free ---
    ("$70,000/yr", 1.0, "slash-yr not individually filed"),
    ("$70,000 hourly", 1.0, "'hourly' word form -> x2080"),
    ("$50/hour", 1.0, "full '/hour' -> x2080"),
    ("$1,200 weekly", 1.0, "'weekly' word form -> x52 = $62.4k"),
    ("$5,000 monthly", 1.0, "'monthly' word form -> x12 = $60k"),

    # --- NEGATIVE: descriptive text must NOT trigger a cadence multiplier ---
    ("$48,000, 3 weeks PTO", _prop(48000), "'3 weeks PTO' is not weekly pay (no x52)"),
    ("$50,000, 12 months health coverage", _prop(50000), "'12 months' is not monthly pay (no x12)"),
    ("$40,000 salary, 24-hour support desk", _prop(40000), "'24-hour' is not hourly pay (no x2080)"),
    ("$45,000, flexible hours", _prop(45000), "'flexible hours' is not hourly pay"),
    ("$80,000 with DailyPay app access", 1.0, "'DailyPay' benefit is not a day rate; stays $80k"),
    ("$75,000 + daily pay advance", 1.0, "'daily pay advance' benefit is not a day rate; stays $75k"),
    ("$2,000 semi-annually, paid monthly", 1.0, "semi-annually is NOT already-annual; monthly x12=$24k... "),
]

# Note on the last case: "semi-annually" must NOT be swallowed by the annual
# guard (the literal-substring approach would, since "annually" is inside
# "semi-annually"). With the guard correctly not firing, "paid monthly" applies
# x12 -> $2,000 * 12 = $24,000. Fix the expectation to match that path.
CASES[-1] = ("$2,000 semi-annually, paid monthly", _prop(24000),
             "semi-annually NOT annual-guarded; monthly x12 = $24k applies")


def test_salary_cadence_cases():
    failures = []
    for salary, expected, note in CASES:
        got = _score(salary)
        exp = round(expected, 6)
        if got != exp:
            failures.append(f"  {salary!r}: got {got}, expected {exp}  ({note})")
    assert not failures, "salary cadence mismatches:\n" + "\n".join(failures)


if __name__ == "__main__":
    test_salary_cadence_cases()
    print(f"OK - {len(CASES)} salary-cadence cases passed")
