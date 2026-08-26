"""
Regression tests for reporter.print_alerts field-access contract.

The scorer (filter_and_score) guarantees `fit_score` on every job but treats
`title` and `company` as OPTIONAL (it reads them with .get()). write_report
already renders title/company defensively as 'N/A'. print_alerts must use the
SAME contract, or a top-scoring job whose source omitted title/company gets
written to the report file and then crashes the on-screen alert with KeyError --
silently losing the 🔔 HIGH-FIT alert for exactly the best match.

fit_score stays a hard key on purpose: the scorer always sets it, so a missing
fit_score is a real upstream contract violation that must fail loud, not be
masked with a default (which is the silent-data-loss antipattern).

Runs standalone (`python3 tests/test_print_alerts_missing_fields.py`) and under
pytest.
"""
import io
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import reporter
from config import ALERT_SCORE_THRESHOLD

HIGH = ALERT_SCORE_THRESHOLD  # a score that triggers an alert
LOW = ALERT_SCORE_THRESHOLD - 1


def _alerts_for(jobs):
    buf = io.StringIO()
    with redirect_stdout(buf):
        reporter.print_alerts(jobs)
    return buf.getvalue()


def test_missing_both_title_and_company_does_not_crash():
    # In-contract job (scorer uses job.get for title/company) missing both.
    job = {"fit_score": HIGH, "url": "http://x", "score_reason": "strong"}
    out = _alerts_for([job])
    assert "ALERT" in out, "the high-fit alert must still be emitted"
    assert "N/A @ N/A" in out, f"expected N/A placeholders, got: {out!r}"


def test_missing_only_company_keeps_title():
    job = {"fit_score": HIGH, "title": "AI Trainer", "url": "http://x"}
    out = _alerts_for([job])
    assert "AI Trainer @ N/A" in out, f"got: {out!r}"


def test_below_threshold_emits_no_alert():
    job = {"fit_score": LOW, "url": "http://x"}
    out = _alerts_for([job])
    assert out.strip() == "", f"no alert expected below threshold, got: {out!r}"


def test_complete_job_renders_real_values():
    job = {"fit_score": HIGH, "title": "ML Engineer", "company": "Acme", "url": "http://x"}
    out = _alerts_for([job])
    assert "ML Engineer @ Acme" in out, f"got: {out!r}"


def test_missing_fit_score_still_fails_loud():
    # fit_score is guaranteed by the scorer; a missing one is a real bug and
    # must raise, NOT be silently defaulted. Guards against a future "fix" that
    # would reintroduce silent data loss.
    job = {"title": "AI Trainer", "company": "Acme", "url": "http://x"}
    try:
        _alerts_for([job])
    except KeyError:
        return
    raise AssertionError("expected KeyError on missing fit_score (fail-fast contract)")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
