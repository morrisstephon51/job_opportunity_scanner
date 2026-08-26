r"""
Guard tests for reporter.write_report() job/cover-letter length matching.

Bug: write_report zipped top_jobs with cover_letters. zip() stops at the
shorter list, so if the two ever diverged (e.g. one cover-letter generation
was skipped upstream) the report SILENTLY dropped the trailing matches --
including alert-worthy HIGH FIT jobs -- with no error. A daily scan would
quietly under-report its own top results.

Fix: write_report now raises ValueError up front when the counts differ,
turning invisible data loss into a loud, debuggable failure before any file
is written.

Runnable standalone (`python tests/test_report_cover_letter_count.py`) and
under pytest. Kept import-light so it runs with no third-party deps.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import reporter  # noqa: E402


def _jobs(n):
    """n scored jobs; the last one is a HIGH FIT (9/10) alert-worthy match."""
    jobs = [
        {"fit_score": 6, "title": f"Job {i}", "company": "Co", "url": "http://x"}
        for i in range(n - 1)
    ]
    jobs.append(
        {"fit_score": 9, "title": "AI Education Lead", "company": "C", "url": "http://c"}
    )
    return jobs


def test_more_jobs_than_letters_raises():
    try:
        reporter.write_report(_jobs(3), ["L1", "L2"])
    except ValueError as e:
        assert "3 jobs" in str(e) and "2 cover letters" in str(e)
    else:
        raise AssertionError("expected ValueError on 3 jobs / 2 cover letters")


def test_more_letters_than_jobs_raises():
    try:
        reporter.write_report(_jobs(2), ["L1", "L2", "L3"])
    except ValueError as e:
        assert "2 jobs" in str(e) and "3 cover letters" in str(e)
    else:
        raise AssertionError("expected ValueError on 2 jobs / 3 cover letters")


def test_guard_prevents_silent_high_fit_drop():
    # The exact pre-fix failure: 3 jobs incl. a 9/10 HIGH FIT match, but only
    # 2 cover letters. Old code wrote 2 matches and silently dropped the
    # HIGH FIT job. New code refuses instead of under-reporting.
    try:
        reporter.write_report(_jobs(3), ["L1", "L2"])
    except ValueError:
        pass  # correct: refused rather than dropping the HIGH FIT match
    else:
        raise AssertionError("HIGH FIT job would have been silently dropped")


def test_fail_fast_writes_no_file():
    # Guard must fire before any filesystem work. Trip a sentinel if makedirs
    # is ever reached on a mismatched call.
    reached = {"makedirs": False}
    real = reporter.os.makedirs

    def spy(*a, **k):
        reached["makedirs"] = True
        return real(*a, **k)

    reporter.os.makedirs = spy
    try:
        reporter.write_report(_jobs(3), ["only-one-letter"])
    except ValueError:
        pass
    finally:
        reporter.os.makedirs = real
    assert reached["makedirs"] is False, "report dir/file created despite mismatch"


def test_matched_lengths_write_every_match():
    # Guard is not a blanket reject: equal lengths still write ALL matches,
    # HIGH FIT job included.
    jobs = _jobs(3)
    path = reporter.write_report(jobs, ["L1", "L2", "L3"])
    try:
        body = open(path, encoding="utf-8").read()
        assert len(re.findall(r"## Match #\d+", body)) == 3
        assert "AI Education Lead" in body  # HIGH FIT match survived
    finally:
        if os.path.exists(path):
            os.remove(path)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")
