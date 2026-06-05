"""
Job Scanner Configuration — edit this file to tune your search.
"""

# --- Resume tracks (used for scoring context) ---
RESUME_TRACKS = [
    "IT Support",
    "EdTech / Training",
    "AI / Tech Education",
    "Healthcare IT",
]

# --- Search keywords (each is its own search query) ---
SEARCH_KEYWORDS = [
    "AI educator",
    "instructional designer",
    "training specialist",
    "digital learning",
    "EdTech coordinator",
    "community tech educator",
    "healthcare IT trainer",
    "learning experience designer",
]

# --- Location ---
LOCATIONS = ["Chicago, IL", "remote"]
RADIUS_MILES = 35  # for Chicago metro searches

# --- Filters ---
SALARY_FLOOR = 55_000       # Mark as adjustable
MAX_DAYS_OLD = 7            # Only jobs posted within last 7 days
ALERT_SCORE_THRESHOLD = 8   # Print alert + flag in report if score >= this

# --- Staffing agencies to skip (partial name match, case-insensitive) ---
AGENCY_BLOCKLIST = [
    "staffing",
    "recruiting",
    "talent solutions",
    "manpower",
    "randstad",
    "robert half",
    "adecco",
    "kelly services",
    "insight global",
    "apex systems",
    "tek systems",
    "cybercoders",
]

# --- Your background (injected into cover letter prompt) ---
BACKGROUND = """
- Founder of The Plug AI, a community-focused AI education initiative
- Training & onboarding specialist at BigHeart Health
- Google IT Support Certificate + IBM AI Fundamentals Certificate holder
- Current Computer Science student
- Experienced in curriculum design, digital learning tools, and community tech outreach
- Strong communicator with a track record of making technical topics accessible to non-technical audiences
"""

# --- Scoring weights (must sum to 1.0) ---
SCORE_WEIGHTS = {
    "title_match": 0.40,
    "keyword_match": 0.30,
    "location_match": 0.20,
    "salary_match": 0.10,
}

# --- Title keywords that signal strong fit ---
TITLE_SIGNALS = [
    "ai", "educator", "education", "instructional", "designer", "training",
    "learning", "edtech", "digital", "curriculum", "healthcare it",
    "community", "coordinator", "specialist", "facilitator", "developer",
]
