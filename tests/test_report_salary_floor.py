r"""
Tests for the report's hardcoded "Salary floor" line.

reporter.write_report() printed the salary floor as a literal:
    f"**Salary floor:** $55,000  "
while config.SALARY_FLOOR (explicitly "Mark as adjustable") is the real knob
the scan filters on. If the floor is retuned, the header lied about it — the
report said $55,000 while jobs were being filtered at, say, $70,000.

Fix (reporter.py only): render the line from config —
    f"**Salary floor:** ${SALARY_FLOOR:,}  "
so the header always tracks the configured floor, comma-formatted.

Note: reporter binds SALARY_FLOOR at import (`from config import ...`), so a
retune is simulated by patching reporter.SALARY_FLOOR, which is exactly the
value the header now reads. The default-value assertion derives from
config.SALARY_FLOOR, so it holds if the floor is retuned in config.

Distinct from the open scorer PRs (#7-#13), which all touch scorer.py; this is
the only change to reporter.py — no overlap, no merge conflict.

The repo has no CI; run either way:
    pytest tests/test_report_salary_floor.py
    python tests/test_report_salary_floor.py
"""
import contextlib
import os
import sys
from datetime import date as _real_date

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import reporter  # noqa: E402
from config import SALARY_FLOOR  # noqa: E402


@contextlib.contextmanager
def _fixed_report_date():
    # Pin the output filename so tests never collide with a real scan file.
    class _FixedDate(_real_date):
        @classmethod
        def today(cls):
            return _real_date(1970, 1, 1)

    orig = reporter.date
    reporter.date = _FixedDate
    try:
        yield
    finally:
        reporter.date = orig


@contextlib.contextmanager
def _floor(value):
    # Simulate a retuned floor. reporter reads its own imported binding.
    orig = reporter.SALARY_FLOOR
    reporter.SALARY_FLOOR = value
    try:
        yield
    finally:
        reporter.SALARY_FLOOR = orig


def _salary_floor_line():
    with _fixed_report_date():
        path = reporter.write_report([], [])
    try:
        content = open(path, encoding="utf-8").read()
    finally:
        if os.path.exists(path):
            os.remove(path)
    lines = [ln for ln in content.splitlines() if ln.startswith("**Salary floor:**")]
    assert len(lines) == 1, f"expected exactly one salary-floor line, got {lines!r}"
    return lines[0]


# --- default: the line is sourced from config, comma-formatted ---
def test_line_matches_config_value_by_default():
    assert _salary_floor_line() == f"**Salary floor:** ${SALARY_FLOOR:,}  "


def test_line_shows_thousands_separator():
    with _floor(120_000):
        assert _salary_floor_line() == "**Salary floor:** $120,000  "


# --- the fix: a retuned floor is reflected, not the old literal ---
def test_line_tracks_retuned_floor():
    with _floor(70_000):
        line = _salary_floor_line()
    assert "$70,000" in line
    assert "55,000" not in line


def test_source_has_no_hardcoded_floor_literal():
    src = open(os.path.join(REPO, "reporter.py"), encoding="utf-8").read()
    assert "$55,000" not in src, (
        "salary floor must render from config.SALARY_FLOOR, not a literal"
    )


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
