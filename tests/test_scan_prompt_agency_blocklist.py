"""
Tests for the /scan prompt's inline AGENCY_BLOCKLIST spelling.

Background
----------
`.claude/commands/scan.md` is the slash-command prompt that actually runs the
scan. Per issue #66 it re-implements the filter/score rules inline and drifts
from `config.py` / `scorer.py`. Two drifts were already fixed:

  * #64 / PR #65 corrected `config.AGENCY_BLOCKLIST` from the spaced token
    "tek systems" to the real one-word brand "teksystems" (a top US IT staffing
    firm registers as "TEKsystems", one word, so the spaced form never
    substring-matched and its postings slipped past is_agency()).
  * #66 / PR #67 re-synced the prompt's *title-signal* list to config and added
    "defer to the code" notes.

But PR #67 left the prompt's Step 3 *agency blocklist* line untouched, so it
still listed the spaced "tek systems" even though #65 fixed that exact spelling
in the code. A human/LLM scanning off the prompt's inline list (the documented
failure mode of #66) therefore re-introduces the #64 bug: TEKsystems postings
evade the agency filter.

This fix corrects the prompt's inline token to the real one-word brand so it
mirrors the code. These assertions are self-contained (they do not depend on
whether #65 has merged) so they hold regardless of merge order.

Run either way (the repo has no CI):
    python3 run_tests.py
    python3 tests/test_scan_prompt_agency_blocklist.py
"""
import os

PROMPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".claude", "commands", "scan.md",
)


def _prompt_text():
    with open(PROMPT, encoding="utf-8") as f:
        return f.read().lower()


def test_prompt_uses_real_one_word_teksystems():
    # The real firm registers as one word; the inline blocklist must use it so a
    # scan driven off the prompt still catches TEKsystems postings.
    assert "teksystems" in _prompt_text()


def test_prompt_has_no_spaced_tek_systems():
    # The spaced form never substring-matches "teksystems" -> the #64 evasion.
    assert "tek systems" not in _prompt_text()


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("all passed")
