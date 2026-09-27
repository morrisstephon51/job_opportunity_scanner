"""
Drift guard: the /scan prompt's search-query list vs config.SEARCH_KEYWORDS.

config.SEARCH_KEYWORDS has two consumers with opposite fates:

  1. scorer._keyword_score() — tested, reads the tuple, credits all 8 terms on
     the 30%-weighted keyword dimension.
  2. .claude/commands/scan.md — the ONLY thing that actually issues searches
     (there is no Python search driver; discovery happens through the
     ZipRecruiter/Indeed MCP calls the prompt makes).

When consumer 2 hardcodes its own list, a keyword added to config.py starts
contributing to a job's SCORE while never causing that job to be FOUND. That
was live: the prompt's Step 1 listed 6 queries and Step 2 listed 3 mashed-up
combinations, so "EdTech coordinator" and "learning experience designer"
appeared nowhere in the prompt at all, and "training specialist" /
"digital learning" were only sent with extra words ANDed on
("training specialist EdTech"), which is a narrower query than the configured
term. CLAUDE.md advertises SEARCH_KEYWORDS as the knob for "job keywords to
search" — it was inert on the documented run path.

Scope note: this guard deliberately covers only the Step 1 / Step 2 query
surface. TITLE_SIGNALS parity in the Step 4 criteria table and the
AGENCY_BLOCKLIST copy in Step 3 are reconciled by PRs #67 and #65; asserting
them here would make this file's result depend on merge order. Once both land,
extend _LISTS below.

The repo has no CI; run either way:
    pytest tests/test_scan_prompt_keyword_parity.py
    python tests/test_scan_prompt_keyword_parity.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SEARCH_KEYWORDS  # noqa: E402

PROMPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".claude", "commands", "scan.md",
)


def _prompt():
    with open(PROMPT, encoding="utf-8") as fh:
        return fh.read()


def _section(name, until):
    """Slice one '## Step N' section out of the prompt."""
    body = _prompt()
    assert name in body, f"{name} heading missing from scan.md"
    assert until in body, f"{until} heading missing from scan.md"
    return body.split(name, 1)[1].split(until, 1)[0]


def _numbered_queries(section):
    """The `N. "query"` lines of a numbered query list."""
    return [q.strip() for q in re.findall(r'^\d+\.\s*"([^"]+)"\s*$', section, re.M)]


def test_prompt_mentions_every_configured_keyword():
    body = _prompt().lower()
    missing = [k for k in SEARCH_KEYWORDS if k.lower() not in body]
    assert not missing, (
        "config.SEARCH_KEYWORDS entries absent from the /scan prompt, so they "
        f"are never searched even though _keyword_score() credits them: {missing}"
    )


def test_step1_lists_every_configured_keyword_as_its_own_query():
    queries = _numbered_queries(_section("## Step 1", "## Step 2"))
    lowered = {q.lower() for q in queries}
    missing = [k for k in SEARCH_KEYWORDS if k.lower() not in lowered]
    assert not missing, (
        "Step 1 must issue one query per config.SEARCH_KEYWORDS entry; "
        f"not listed as standalone queries: {missing}"
    )


def test_step1_adds_no_query_that_is_not_a_configured_keyword():
    """Catches re-introduction of narrowed mutations like 'training specialist EdTech'."""
    queries = _numbered_queries(_section("## Step 1", "## Step 2"))
    configured = {k.lower() for k in SEARCH_KEYWORDS}
    extra = [q for q in queries if q.lower() not in configured]
    assert not extra, (
        "Step 1 queries must match config.SEARCH_KEYWORDS verbatim — extra words "
        f"AND-narrow the search and drop postings the configured term targets: {extra}"
    )


# A line that actually issues a search: a numbered query item, or any line
# passing a `search:` / `search=` argument. Prose that merely quotes a bad
# example is not a query and must not trip the guard.
_QUERY_LINE = re.compile(r'^\s*(?:\d+\.|.*\bsearch\s*[:=])', re.I)


def test_step2_does_not_concatenate_keywords_into_one_query():
    section = _section("## Step 2", "## Step 3")
    offenders = []
    for line in section.splitlines():
        if not _QUERY_LINE.match(line):
            continue
        hits = [k for k in SEARCH_KEYWORDS if k.lower() in line.lower()]
        if len(hits) > 1:
            offenders.append((line.strip(), hits))
    assert not offenders, (
        "Indeed queries must be sent one keyword at a time; concatenating ANDs "
        f"the terms and loses single-term matches: {offenders}"
    )


def test_step2_defers_to_the_config_tuple():
    section = _section("## Step 2", "## Step 3")
    assert "SEARCH_KEYWORDS" in section, (
        "Step 2 must name config.SEARCH_KEYWORDS as the query source rather than "
        "hardcoding its own Indeed query list"
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
