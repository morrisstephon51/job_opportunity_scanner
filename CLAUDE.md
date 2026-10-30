# Job Opportunity Scanner

Daily AI/EdTech/Healthcare IT job scanner. Surfaces top 3 matches with fit scores and tailored cover letters.

## How to run a scan

```
/scan
```

This slash command searches ZipRecruiter + Indeed, scores results, picks top 3, writes cover letters, and saves to `jobs/scan-YYYY-MM-DD.md`.

## Output location

All scan results are saved to `jobs/` as dated Markdown files.

## Configuration

Edit `config.py` to change:
- `SALARY_FLOOR` — minimum acceptable salary (default: $55,000)
- `SEARCH_KEYWORDS` — job keywords to search
- `LOCATIONS` — target cities/remote
- `ALERT_SCORE_THRESHOLD` — score that triggers an alert (default: 8)
- `AGENCY_BLOCKLIST` — staffing agency names to exclude
- `BACKGROUND` — your bio injected into cover letter prompts

## Scoring logic

See `scorer.py`. Weights: title match (40%), keyword match (30%), location (20%), salary (10%).

## Constraints

- Jobs posted within last 7 days only
- No staffing agency postings
- Cover letters are tailored per job — no generic templates
- Does not auto-apply — you click Apply

## Tools used (all free)

- ZipRecruiter MCP — job search
- Indeed MCP — job search
- Claude Code — scoring + cover letter generation

## Token discipline: look things up through the indexes

Morris's notes and Drive files are cataloged, so never crawl them to find something.

- **Obsidian vault** (`morrisstephon51/obsidian-kai`, branch `main`): read `_INDEX.md` at the vault root first, then open only the note it points to. Don't list, glob or grep the vault to find a note.
- **Google Drive**: read the Google Doc `_CLAUDE_INDEX — Google Drive` (id `17IdsMTLVIbhBv8RtF-qlQkZUrupBIqptowSW5_qHY9Q`) first, then fetch the file by its id. Whenever you list or search Drive, pass `excludeContentSnippets: true`.
- If the index doesn't have the item, run one targeted search for it, not a sweep, and tell Morris the index needs a rebuild.
- Rebuilds and the full protocol are in `.claude/skills/remote-control/` (`/remote-control index`).
