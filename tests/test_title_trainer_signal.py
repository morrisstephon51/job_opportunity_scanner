"""
Tests for the "trainer" TITLE_SIGNALS gap.

"training" was in TITLE_SIGNALS but does not substring-match "trainer", so
titles like "Corporate Trainer" / "AI Trainer" / "Healthcare IT Trainer" —
the exact role in RESUME_TRACKS ("EdTech / Training") and the
"healthcare IT trainer" search keyword — got no credit on the 40%-weighted
title dimension. Adding "trainer" fixes that.

Assertions are written to hold under BOTH the current substring matcher and
the word-boundary matcher (see fix/title-score-ai-substring): they compare a
trainer title against a signal-free control rather than asserting an absolute
score, so merge order does not matter.

The repo has no CI; run either way:
    pytest tests/test_title_trainer_signal.py
    python tests/test_title_trainer_signal.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import _title_score, score_job  # noqa: E402
from config import TITLE_SIGNALS  # noqa: E402


def _t(title):
    return _title_score({"title": title})


def test_trainer_is_a_signal():
    assert "trainer" in TITLE_SIGNALS


def test_training_signal_still_present():
    # Regression guard: the new word must be added, not swap out "training".
    assert "training" in TITLE_SIGNALS


def test_trainer_adds_title_credit():
    # "Corporate Trainer" must out-score a signal-free control by the trainer
    # word alone. True under substring matching (0.667 vs 0.0) and under
    # word-boundary matching (0.333 vs 0.0).
    assert _t("Corporate Trainer") > _t("Corporate Manager")


def test_healthcare_it_trainer_beats_control():
    # The literal "healthcare IT trainer" search keyword as a title.
    assert _t("Healthcare IT Trainer") > _t("Healthcare IT Manager")


def test_score_job_credits_a_trainer_role_end_to_end():
    # A remote healthcare IT trainer with a real salary should out-score the
    # same posting stripped of its trainer/signal words.
    good = {
        "title": "Healthcare IT Trainer",
        "description": "clinical systems training and digital learning",
        "location": "Remote",
        "salary": "$85k",
    }
    control = {
        "title": "Operations Manager",
        "description": "clinical systems training and digital learning",
        "location": "Remote",
        "salary": "$85k",
    }
    good_score, _ = score_job(good)
    control_score, _ = score_job(control)
    assert good_score > control_score


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
