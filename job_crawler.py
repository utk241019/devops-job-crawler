import json
import os
import smtplib
import time
from email.message import EmailMessage
import requests
from bs4 import BeautifulSoup

# ==========================================
# 1. CONFIGURATION
# ==========================================
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

# Target Locations
ALLOWED_LOCATIONS = ["pune", "mumbai", "bengaluru", "bangalore", "hyderabad", "remote", "wfh"]

ROLE_KEYWORDS = [
    "devops", "sre", "site reliability", "linux", "systems engineer", 
    "system engineer", "system administrator", "sysadmin", 
    "infrastructure", "cloud", "platform engineer"
]

LEVEL_KEYWORDS = [
    "intern", "internship", "fresher", "junior", "entry level", 
    "associate", "trainee", "early career", "2025", "2026", "graduate"
]

SEEN_JOBS_FILE = "seen_jobs.json"

# ==========================================
# 2. FILTERING LOGIC
# ==========================================
def is_location_relevant(location_str):
    """Checks if the job location is within our target list."""
    loc = location_str.lower()
    return any(target in loc for target in ALLOWED_LOCATIONS)

def is_relevant_job(title, location=""):
    """Checks for role, level, and location relevance."""
    title_lower = title.lower()
    matches_role = any(kw in title_lower for kw in ROLE_KEYWORDS)
    matches_level = any(kw in title_lower for kw in LEVEL_KEYWORDS)
    matches_loc = is_location_relevant(location) if location else True # Default True if location unknown
    return matches_role and matches_level and matches_loc

# [Keep the rest of your existing helper functions here...]

def fetch_workday_jobs(company_name, tenant, path, search_term="Linux"):
    print(f"[*] Checking {company_name}...")
    url = f"https://{tenant}.wd5.myworkdayjobs.com/wday/cxs/{tenant}/{path}/jobs"
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": search_term}
    
    jobs = []
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            for item in res.json().get("jobPostings", []):
                title = item.get("title", "")
                loc_text = item.get("locationsText", "")
                if is_relevant_job(title, loc_text):
                    job_path = item.get("externalPath", "")
                    jobs.append({
                        "id": f"{company_name.lower()}_{job_path}",
                        "company": company_name,
                        "title": title,
                        "location": loc_text,
                        "url": f"https://{tenant}.wd5.myworkdayjobs.com/en-US/{path}{job_path}",
                        "source": f"{company_name} Portal"
                    })
    except Exception as e:
        print(f"[-] Error fetching {company_name}: {e}")
    return jobs

# [Include your other fetch functions here, ensuring they call is_relevant_job(title, location)]

# ==========================================
# 3. EXECUTION
# ==========================================
def run_crawler():
    # ... (Keep the main run_crawler logic from before)
    pass
