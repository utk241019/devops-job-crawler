import json
import os
import smtplib
import time
from email.message import EmailMessage
import requests
from bs4 import BeautifulSoup

# ==========================================
# 1. CONFIGURATION & KEYWORDS
# ==========================================
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

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
# 2. STATE & RELEVANCE FILTER
# ==========================================
def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen_jobs(seen_jobs):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen_jobs), f, indent=2)

def is_relevant_job(title):
    title_lower = title.lower()
    matches_role = any(kw in title_lower for kw in ROLE_KEYWORDS)
    matches_level = any(kw in title_lower for kw in LEVEL_KEYWORDS)
    return matches_role and matches_level

# ==========================================
# 3. NOTIFICATION SYSTEM
# ==========================================
def send_email_alert(new_jobs):
    if not new_jobs or not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("[-] Skipping email alert (no new jobs or missing email environment credentials).")
        return

    msg = EmailMessage()
    msg['Subject'] = f"🚨 {len(new_jobs)} New DevOps / SRE / Linux Job Openings Found!"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER or EMAIL_SENDER

    body = "Here are the latest matching openings for DevOps, SRE, and Linux / Systems Engineers:\n\n"
    for job in new_jobs:
        body += f"• [{job['company']}] {job['title']}\n"
        body += f"  Location: {job.get('location', 'N/A')}\n"
        body += f"  Source: {job['source']}\n"
        body += f"  Link: {job['url']}\n\n"

    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print(f"[+] Email alert sent for {len(new_jobs)} jobs.")
    except Exception as e:
        print(f"[-] Email sending failed: {e}")

# ==========================================
# 4. COMPANY SCRAPERS & ATS INTEGRATIONS
# ==========================================

def fetch_workday_jobs(company_name, tenant, path, search_term="Linux"):
    """Fetcher for Workday ATS sites (NVIDIA, Red Hat, Cisco, etc.)"""
    print(f"[*] Checking {company_name} Career Page...")
    url = f"https://{tenant}.wd5.myworkdayjobs.com/wday/cxs/{tenant}/{path}/jobs"
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": search_term}
    
    jobs = []
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            for item in res.json().get("jobPostings", []):
                title = item.get("title", "")
                if is_relevant_job(title):
                    job_path = item.get("externalPath", "")
                    job_url = f"https://{tenant}.wd5.myworkdayjobs.com/en-US/{path}{job_path}"
                    jobs.append({
                        "id": f"{company_name.lower()}_{job_path}",
                        "company": company_name,
                        "title": title,
                        "location": item.get("locationsText", "Various"),
                        "url": job_url,
                        "source": f"{company_name} Career Portal"
                    })
    except Exception as e:
        print(f"[-] Error fetching {company_name}: {e}")
    return jobs

def fetch_greenhouse_jobs(company_name, board_token):
    """Fetcher for Greenhouse ATS sites (Cloudflare, Datadog, etc.)"""
    print(f"[*] Checking {company_name} Career Page...")
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    jobs = []
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            for item in res.json().get("jobs", []):
                title = item.get("title", "")
                if is_relevant_job(title):
                    jobs.append({
                        "id": f"{company_name.lower()}_{item.get('id')}",
                        "company": company_name,
                        "title": title,
                        "location": item.get("location", {}).get("name", "Various"),
                        "url": item.get("absolute_url", ""),
                        "source": f"{company_name} Career Portal"
                    })
    except Exception as e:
        print(f"[-] Error fetching {company_name}: {e}")
    return jobs

def fetch_akamai_jobs():
    """Fetcher for Akamai Technologies Jobs Portal (Oracle CX Cloud backend)"""
    print("[*] Checking Akamai Career Page...")
    url = "https://jobs.akamai.com/en/sites/CX_1/jobs?keyword=Engineer"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    jobs = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            listings = soup.find_all("li")
            for item in listings:
                link = item.find("a")
                if link and link.get("href"):
                    title = link.get_text(strip=True)
                    if is_relevant_job(title):
                        job_url = "https://jobs.akamai.com" + link["href"] if link["href"].startswith("/") else link["href"]
                        job_id = f"akamai_{job_url.split('/')[-1]}"
                        jobs.append({
                            "id": job_id,
                            "company": "Akamai",
                            "title": title,
                            "location": "Check Listing",
                            "url": job_url,
                            "source": "Akamai Career Site"
                        })
    except Exception as e:
        print(f"[-] Error fetching Akamai: {e}")
    return jobs

def fetch_simplify_early_career_feed():
    """Aggregates early-career tech postings across 500+ top tech companies"""
    print("[*] Checking Simplify Early-Career Aggregator Feed...")
    url = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/main/.github/scripts/data.json"
    jobs = []
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            for item in res.json():
                title = item.get("title", "")
                company = item.get("company_name", "Tech Company")
                if is_relevant_job(title):
                    job_url = item.get("url", "")
                    job_id = f"simplify_{item.get('id', hash(job_url))}"
                    jobs.append({
                        "id": job_id,
                        "company": company,
                        "title": title,
                        "location": ", ".join(item.get("locations", ["Multiple"])),
                        "url": job_url,
                        "source": "Early Career Feed"
                    })
    except Exception as e:
        print(f"[-] Error fetching Simplify Feed: {e}")
    return jobs

def fetch_linkedin_public_jobs():
    """Queries LinkedIn guest search API across multiple targeted search queries"""
    print("[*] Checking LinkedIn Public Job Feeds...")
    jobs = []
    queries = [
        "DevOps Intern", "Site Reliability Engineer Intern", 
        "Linux Engineer Intern", "Systems Engineer Fresher", "Cloud Engineer Intern"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    for query in queries:
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={requests.utils.quote(query)}&start=0"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                for card in soup.find_all("li"):
                    title_elem = card.find("h3", class_="base-search-card__title")
                    company_elem = card.find("h4", class_="base-search-card__subtitle")
                    link_elem = card.find("a", class_="base-card__full-link")
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                        link = link_elem["href"].split("?")[0]
                        job_id = f"linkedin_{link.split('/')[-1]}"
                        
                        if is_relevant_job(title):
                            jobs.append({
                                "id": job_id,
                                "company": company,
                                "title": title,
                                "location": "Check Listing",
                                "url": link,
                                "source": "LinkedIn Public Feed"
                            })
        except Exception as e:
            print(f"[-] Error searching LinkedIn '{query}': {e}")
        time.sleep(1)
        
    return jobs

# ==========================================
# 5. MAIN EXECUTION ENGINE
# ==========================================
def run_crawler():
    print(f"\n--- Starting Job Crawler Scan [{time.strftime('%Y-%m-%d %H:%M:%S')}] ---")
    seen_jobs = load_seen_jobs()
    
    all_fetched_jobs = []
    
    # Workday Portals
    all_fetched_jobs.extend(fetch_workday_jobs("NVIDIA", "nvidia", "NVIDIAExternalCareerSite"))
    all_fetched_jobs.extend(fetch_workday_jobs("Red Hat", "redhat", "jobs"))
    all_fetched_jobs.extend(fetch_workday_jobs("Cisco", "cisco", "Cisco_Careers"))

    # Greenhouse Portals
    all_fetched_jobs.extend(fetch_greenhouse_jobs("Cloudflare", "cloudflare"))
    all_fetched_jobs.extend(fetch_greenhouse_jobs("Datadog", "datadog"))

    # Akamai Custom Engine
    all_fetched_jobs.extend(fetch_akamai_jobs())

    # Aggregator & Social Feeds
    all_fetched_jobs.extend(fetch_simplify_early_career_feed())
    all_fetched_jobs.extend(fetch_linkedin_public_jobs())

    # Filter out seen postings
    new_discoveries = []
    for job in all_fetched_jobs:
        if job["id"] not in seen_jobs:
            seen_jobs.add(job["id"])
            new_discoveries.append(job)

    if new_discoveries:
        print(f"[!] Found {len(new_discoveries)} NEW relevant job postings!")
        send_email_alert(new_discoveries)
        save_seen_jobs(seen_jobs)
    else:
        print("[=] Scan complete. No new openings found.")

if __name__ == "__main__":
    run_crawler()
