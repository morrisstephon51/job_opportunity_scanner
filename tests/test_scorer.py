"""
Regression tests for scorer._title_score token matching.

Runs with pytest OR as a plain script (`python3 tests/test_scorer.py`) so it
needs no dependencies — the repo has no CI, so keep this self-contained.

Guards against the 2-char-substring bug: TITLE_SIGNALS contains "ai", and a
bare `s in title` check matched it inside unrelated titles (retAIl,
mAIntenance, repAIr, hAIr, chAIr, trAIner), inflating the heaviest-weighted
(40%) score and corrupting the top-3 ranking.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import _title_score  # noqa: E402


def _s(title):
    return _title_score({"title": title})


def test_ai_substring_does_not_false_match():
    # None of these are AI/EdTech roles; each merely contains the substring "ai".
    for title in [
        "Retail Sales Associate",
        "Maintenance Technician",
        "Auto Repair Mechanic",
        "Hair Stylist",
        "Airport Ramp Agent",
        "Chairperson of the Board",
    ]:
        assert _s(title) == 0.0, f"{title!r} should not match any TITLE_SIGNAL"


def test_real_signals_still_score():
    # (title, expected) — expected reflects genuine whole-token signal hits / 3.
    cases = [
        ("AI Educator", 2 / 3),             # ai + educator
        ("Instructional Designer", 2 / 3),  # instructional + designer
        ("AI/ML Learning Specialist", 1.0),  # ai + learning + specialist
        ("Training Coordinator", 2 / 3),    # training + coordinator
        ("Healthcare IT Trainer", 1 / 3),    # healthcare it (only real token)
    ]
    for title, expected in cases:
        assert abs(_s(title) - expected) < 1e-9, f"{title!r} -> {_s(title)} != {expected}"


def test_ai_as_standalone_word_matches():
    # "ai" must still count when it's a real word, incl. next to punctuation.
    assert _s("AI Educator") > 0.0
    assert _s("AI/ML Learning Specialist") == 1.0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS  {fn.__name__}")
    print(f"\n{len(fns)} passed")
