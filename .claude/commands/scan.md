# Job Opportunity Scanner

Run a full job scan across ZipRecruiter and Indeed. Follow every step below exactly and in order.

---

## Your background (use in every cover letter)
- Founder of The Plug AI — community AI education initiative
- Training & onboarding specialist at BigHeart Health
- Google IT Support Certificate + IBM AI Fundamentals Certificate
- Current Computer Science student
- Skilled in curriculum design, digital learning tools, community tech outreach
- Makes technical topics accessible to non-technical audiences

---

## Step 1 — Search ZipRecruiter

Call `mcp__ZipRecruiter__search_jobs` for EACH of the following queries. Use `salary_min: 55000`, `max_posted_minutes_ago: 10080` (7 days), location `Chicago, IL`, radius `35`. Also run each with `location_types: ["REMOTE"]` (no location field for remote).

Queries:
1. "AI educator"
2. "instructional designer"
3. "training specialist EdTech"
4. "digital learning coordinator"
5. "healthcare IT trainer"
6. "community tech educator"

Collect all results into a list. Deduplicate by job title + company name.

---

## Step 2 — Search Indeed

Call `mcp__Indeed__search_jobs` for EACH of the following. Use `country_code: "US"`, `job_type: "fulltime"`.

Queries (run each for location `"Chicago, IL"` AND `"remote"`):
1. `search: "AI educator instructional designer"`
2. `search: "training specialist EdTech digital learning"`
3. `search: "healthcare IT training coordinator"`

Collect and deduplicate results (title + company).

---

## Step 3 — Combine & Filter

Merge both source lists. Then remove any job where:
- Company name contains any of: staffing, recruiting, talent solutions, manpower, randstad, robert half, adecco, kelly services, insight global, apex systems, tek systems, cybercoders
- Posted more than 7 days ago (skip if date unknown — include it)

---

## Step 4 — Score Each Job (1–10)

Score each remaining job using these weighted criteria:

| Criterion | Weight | Full score if... |
|-----------|--------|-----------------|
| Title match | 40% | Title contains 3+ of: ai, educator, education, instructional, designer, training, learning, edtech, digital, curriculum, healthcare it, coordinator, specialist, facilitator |
| Keyword match | 30% | Description/title contains 4+ of the search keywords above |
| Location | 20% | Remote = 10/10; Chicago/IL = 10/10; Hybrid = 7/10; Other = 2/10 |
| Salary | 10% | Listed salary ≥ $55,000 = 10/10; Not listed = 5/10; Below floor = proportional |

Multiply each component × weight, sum, multiply by 10, round to nearest integer (min 1, max 10).

---

## Step 5 — Pick Top 3

Select the 3 highest-scoring jobs. If a tie, prefer the one with a listed salary ≥ $55k, then prefer remote/Chicago.

---

## Step 6 — Write Cover Letters

For each of the top 3 jobs, write a tailored cover letter that:
- Opens by naming the **specific job title** and **company** — never generic
- Paragraph 1: Why this role excites you (tie to the company's mission if inferable)
- Paragraph 2: Most relevant background (pick 2-3 items from your background above that directly match the role's likely needs)
- Paragraph 3: One concrete example of impact (The Plug AI, BigHeart Health, or a learning project)
- Closing: Confident, brief — express interest in next steps
- Tone: Professional but warm, first-person, ~250 words
- Do NOT use phrases like "I am writing to apply for", "I believe I would be a great fit", or other clichés

---

## Step 7 — Write Output File

Write the results to `jobs/scan-YYYY-MM-DD.md` (use today's date).

Format:

```
# Job Scan — YYYY-MM-DD

**Sources:** ZipRecruiter, Indeed
**Tracks:** IT Support · EdTech/Training · AI/Tech Education · Healthcare IT
**Salary floor:** $55,000

---

## Match #1 — Fit Score: X/10 [🔔 HIGH FIT if score ≥ 8]

**Title:** ...
**Company:** ...
**Location:** ...
**Salary:** ...
**Source:** ZipRecruiter / Indeed
**Apply:** [URL]
**Why it fits:** [one-line reason]

### Cover Letter

[letter text]

---

## Match #2 — Fit Score: X/10
...

## Match #3 — Fit Score: X/10
...
```

---

## Step 8 — Print Summary

After writing the file, print to terminal:

```
✅ Scan complete — YYYY-MM-DD
📄 Report: jobs/scan-YYYY-MM-DD.md
🏆 Top match: [Title] @ [Company] — Score: X/10
```

If any job scored 8 or higher, also print:
```
🔔 ALERT: [Title] @ [Company] — Score X/10 — [Apply URL]
```

---

**Constraint reminders:**
- Only jobs posted within the last 7 days
- No staffing agency postings
- Cover letters must name the specific title and company
- Do not apply — output only
