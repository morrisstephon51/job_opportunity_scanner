"""
Formats scan results into a Markdown report and prints alerts.
"""
from __future__ import annotations
import os
from datetime import date
from config import ALERT_SCORE_THRESHOLD, SALARY_FLOOR


def write_report(top_jobs: list[dict], cover_letters: list[str]) -> str:
    """Write jobs/scan-YYYY-MM-DD.md and return the file path."""
    if len(cover_letters) != len(top_jobs):
        raise ValueError(
            "write_report expects one cover letter per job: got "
            f"{len(top_jobs)} jobs but {len(cover_letters)} cover letters. "
            "Refusing to write a report that would silently drop matches."
        )
    today = date.today().isoformat()
    out_dir = os.path.join(os.path.dirname(__file__), "jobs")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"scan-{today}.md")

    lines = [
        f"# Job Scan — {today}",
        "",
        f"**Sources:** ZipRecruiter, Indeed  ",
        f"**Tracks:** IT Support · EdTech/Training · AI/Tech Education · Healthcare IT  ",
        f"**Salary floor:** ${SALARY_FLOOR:,}  ",
        "",
        "---",
        "",
    ]

    for i, (job, letter) in enumerate(zip(top_jobs, cover_letters), 1):
        alert = " 🔔 HIGH FIT" if job["fit_score"] >= ALERT_SCORE_THRESHOLD else ""
        lines += [
            f"## Match #{i} — Fit Score: {job['fit_score']}/10{alert}",
            "",
            f"**Title:** {job.get('title', 'N/A')}  ",
            f"**Company:** {job.get('company', 'N/A')}  ",
            f"**Location:** {job.get('location', 'N/A')}  ",
            f"**Salary:** {job.get('salary') or 'Not listed'}  ",
            f"**Source:** {job.get('source', 'N/A')}  ",
            f"**Apply:** {job.get('url', 'N/A')}  ",
            f"**Why it fits:** {job.get('score_reason', '')}  ",
            "",
            "### Cover Letter",
            "",
            letter.strip(),
            "",
            "---",
            "",
        ]

    with open(path, "w") as f:
        f.write("\n".join(lines))

    return path


def print_alerts(top_jobs: list[dict]) -> None:
    for job in top_jobs:
        if job["fit_score"] >= ALERT_SCORE_THRESHOLD:
            print(
                f"\n🔔  ALERT — Score {job['fit_score']}/10: "
                f"{job['title']} @ {job['company']} | {job.get('url', '')}"
            )
