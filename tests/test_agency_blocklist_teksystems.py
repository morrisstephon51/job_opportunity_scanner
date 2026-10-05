"""
Tests for the TEKsystems AGENCY_BLOCKLIST spacing gap.

is_agency() does a case-insensitive substring match (block in company), which
is the right design for partial agency-name matching ("staffing" catches
"ABC Staffing Solutions"). But the blocklist token was "tek systems" (with a
space), while the actual firm — a top US IT staffing agency — registers as
"TEKsystems", one word. So "tek systems" in "teksystems" was False and every
TEKsystems posting slipped past the agency filter into the scored results.

Fix: correct the token to the real brand spelling "teksystems". Substring
matching then catches "TEKsystems", "TEKsystems, Inc.", "TEKsystems Global
Services", etc.

These assertions are config-only and disjoint from the scorer PRs, so they
hold regardless of merge order.

The repo has no CI; run either way:
    pytest tests/test_agency_blocklist_teksystems.py
    python tests/test_agency_blocklist_teksystems.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import is_agency  # noqa: E402
from config import AGENCY_BLOCKLIST  # noqa: E402


def _agency(company):
    return is_agency({"company": company})


def test_token_is_the_real_one_word_brand():
    assert "teksystems" in AGENCY_BLOCKLIST


def test_space_form_removed():
    # Regression guard: the broken space form must be gone, not kept alongside.
    assert "tek systems" not in AGENCY_BLOCKLIST


def test_canonical_teksystems_is_blocked():
    assert _agency("TEKsystems")


def test_teksystems_legal_suffix_is_blocked():
    assert _agency("TEKsystems, Inc.")


def test_teksystems_division_is_blocked():
    assert _agency("TEKsystems Global Services")


def test_non_agency_employer_still_passes():
    # A clear direct employer must not be filtered.
    assert not _agency("Acme EdTech")
    assert not _agency("BigHeart Health")


def test_other_blocklist_entries_unaffected():
    # The one-line token fix must not disturb the neighbors.
    assert _agency("Apex Systems")
    assert _agency("CyberCoders")
    assert _agency("Insight Global")


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
