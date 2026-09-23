"""
Regression tests for _keyword_score whole-word matching.

_keyword_score contributes 30% of the fit score. It previously matched each
SEARCH_KEYWORDS entry with a bare `kw in text` substring test — the exact
collision class already fixed in _title_score ("ai" -> retAIl) and
_location_score ("il" -> NashvILle), but left in place here. SEARCH_KEYWORDS is
user-tunable (config.py invites editing it), so a short keyword like "AI" / "IT"
silently fires inside digITal / retAIl / emAIl and inflates the score on
irrelevant jobs. This test pins two guarantees:

  1. No regression: for the current multi-word phrase keywords, word-boundary
     matching is identical to the old substring behavior.
  2. The fix: short single-token keywords no longer collide inside longer words.

Self-contained: runs under pytest OR directly with
`python3 tests/test_keyword_boundary.py` (the repo has no CI / third-party deps).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scorer  # noqa: E402
from scorer import _keyword_score  # noqa: E402


def _score(title, description, keywords):
    """Score with a temporary SEARCH_KEYWORDS override."""
    saved = scorer.SEARCH_KEYWORDS
    scorer.SEARCH_KEYWORDS = keywords
    try:
        return round(_keyword_score({"title": title, "description": description}), 6)
    finally:
        scorer.SEARCH_KEYWORDS = saved


CURRENT = [
    "AI educator", "instructional designer", "training specialist",
    "digital learning", "EdTech coordinator", "community tech educator",
    "healthcare IT trainer", "learning experience designer",
]


def test_no_regression_on_current_phrase_keywords():
    # Two genuine phrase hits out of 4-needed -> 0.5, exactly as before the fix.
    got = _score("Instructional Designer", "digital learning programs", CURRENT)
    assert got == round(2 / 4, 6), f"phrase keywords regressed: {got}"
    # A job with none of the phrases scores 0 under both old and new matchers.
    assert _score("Retail Associate", "email marketing, maintain register", CURRENT) == 0.0


def test_short_keyword_no_longer_collides():
    # User tunes config with short tokens (config header explicitly invites this).
    tuned = CURRENT + ["AI", "IT"]
    # An irrelevant retail job: "retail"/"email"/"maintain" contain "ai",
    # "digital" contains "it". Old substring matcher would count 2 false hits
    # (-> 0.5). Whole-word matching counts 0.
    got = _score("Retail Associate",
                 "email marketing, maintain the register, digital signage", tuned)
    assert got == 0.0, f"short keyword still collides: {got}"
    # A genuine "AI" title still matches as a whole word.
    assert _score("AI Engineer", "build AI tools", tuned) > 0.0


if __name__ == "__main__":
    test_no_regression_on_current_phrase_keywords()
    test_short_keyword_no_longer_collides()
    print("test_keyword_boundary: all cases pass")
