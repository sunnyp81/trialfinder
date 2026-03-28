"""
Fetch recruiting US clinical trials from ClinicalTrials.gov v2 API.
Stores results in SQLite database.

Usage: python scripts/fetch_trials.py
"""

import json
import re
import sqlite3
import time
from pathlib import Path

import requests

DB_PATH = Path(__file__).parent / "data" / "trials.db"
API_BASE = "https://clinicaltrials.gov/api/v2/studies"

FIELDS = ",".join([
    "protocolSection.identificationModule",
    "protocolSection.statusModule",
    "protocolSection.descriptionModule",
    "protocolSection.conditionsModule",
    "protocolSection.designModule",
    "protocolSection.eligibilityModule",
    "protocolSection.contactsLocationsModule",
    "protocolSection.armsInterventionsModule",
])


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:80].rstrip('-')


def init_db(conn: sqlite3.Connection):
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS trials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nct_id TEXT UNIQUE NOT NULL,
            brief_title TEXT,
            official_title TEXT,
            status TEXT,
            phase TEXT,
            study_type TEXT,
            conditions_json TEXT,
            interventions_json TEXT,
            locations_json TEXT,
            min_age TEXT,
            max_age TEXT,
            sex TEXT,
            healthy_volunteers TEXT,
            contact_name TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            raw_eligibility TEXT,
            plain_eligibility TEXT,
            plain_summary TEXT,
            can_join TEXT,
            cannot_join TEXT,
            start_date TEXT,
            slug TEXT,
            brief_summary TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS conditions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            trial_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trial_id TEXT NOT NULL,
            city TEXT,
            state TEXT,
            state_slug TEXT,
            facility TEXT,
            zip TEXT,
            FOREIGN KEY (trial_id) REFERENCES trials(nct_id)
        );

        CREATE TABLE IF NOT EXISTS error_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trial_id TEXT,
            error_type TEXT,
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_trials_nct ON trials(nct_id);
        CREATE INDEX IF NOT EXISTS idx_trials_status ON trials(status);
        CREATE INDEX IF NOT EXISTS idx_trials_slug ON trials(slug);
        CREATE INDEX IF NOT EXISTS idx_locations_trial ON locations(trial_id);
        CREATE INDEX IF NOT EXISTS idx_locations_state ON locations(state_slug);
        CREATE INDEX IF NOT EXISTS idx_conditions_slug ON conditions(slug);
    """)
    conn.commit()


def parse_date(date_struct: dict | None) -> str:
    """Parse date from API response (handles both YYYY-MM and YYYY-MM-DD)."""
    if not date_struct:
        return ""
    return date_struct.get("date", "")


def extract_contact(contacts_module: dict) -> tuple[str, str, str]:
    """Extract primary contact info."""
    central = contacts_module.get("centralContacts", [])
    if central:
        c = central[0]
        return (
            c.get("name", ""),
            c.get("email", ""),
            c.get("phone", ""),
        )
    return ("", "", "")


def extract_us_locations(contacts_module: dict) -> list[dict]:
    """Filter locations to US only."""
    locs = contacts_module.get("locations", [])
    us_locs = []
    for loc in locs:
        if loc.get("country") == "United States":
            us_locs.append({
                "city": loc.get("city", ""),
                "state": loc.get("state", ""),
                "facility": loc.get("facility", ""),
                "zip": loc.get("zip", ""),
            })
    return us_locs


def process_study(study: dict, conn: sqlite3.Connection) -> bool:
    """Process a single study and insert into DB. Returns True if US trial."""
    proto = study.get("protocolSection", {})

    ident = proto.get("identificationModule", {})
    status_mod = proto.get("statusModule", {})
    desc = proto.get("descriptionModule", {})
    conds = proto.get("conditionsModule", {})
    design = proto.get("designModule", {})
    elig = proto.get("eligibilityModule", {})
    contacts = proto.get("contactsLocationsModule", {})
    arms = proto.get("armsInterventionsModule", {})

    # Filter: must have at least one US location
    us_locations = extract_us_locations(contacts)
    if not us_locations:
        return False

    nct_id = ident.get("nctId", "")
    brief_title = ident.get("briefTitle", "")
    official_title = ident.get("officialTitle", "")
    overall_status = status_mod.get("overallStatus", "")
    start_date = parse_date(status_mod.get("startDateStruct"))

    phases = design.get("phases", [])
    phase = ", ".join(phases) if phases else "Not Applicable"
    study_type = design.get("studyType", "")

    conditions_list = conds.get("conditions", [])
    interventions_list = arms.get("interventions", [])

    contact_name, contact_email, contact_phone = extract_contact(contacts)

    slug = slugify(brief_title)
    # Ensure unique slug by appending nct_id suffix
    slug = f"{slug}-{nct_id.lower()}"

    try:
        conn.execute("""
            INSERT OR REPLACE INTO trials (
                nct_id, brief_title, official_title, status, phase, study_type,
                conditions_json, interventions_json, locations_json,
                min_age, max_age, sex, healthy_volunteers,
                contact_name, contact_email, contact_phone,
                raw_eligibility, start_date, slug, brief_summary, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            nct_id, brief_title, official_title, overall_status, phase, study_type,
            json.dumps(conditions_list), json.dumps(interventions_list),
            json.dumps(us_locations),
            elig.get("minimumAge", ""), elig.get("maximumAge", ""),
            elig.get("sex", "ALL"), elig.get("healthyVolunteers", ""),
            contact_name, contact_email, contact_phone,
            elig.get("eligibilityCriteria", ""),
            start_date, slug,
            desc.get("briefSummary", ""),
        ))

        # Insert US locations
        conn.execute("DELETE FROM locations WHERE trial_id = ?", (nct_id,))
        for loc in us_locations:
            state_slug = slugify(loc["state"]) if loc["state"] else ""
            conn.execute("""
                INSERT INTO locations (trial_id, city, state, state_slug, facility, zip)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nct_id, loc["city"], loc["state"], state_slug, loc["facility"], loc["zip"]))

        return True
    except sqlite3.Error as e:
        conn.execute(
            "INSERT INTO error_log (trial_id, error_type, error_message) VALUES (?, ?, ?)",
            (nct_id, "insert_error", str(e))
        )
        return False


def fetch_all_trials():
    """Fetch all recruiting US trials from ClinicalTrials.gov API."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    params = {
        "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING",
        "pageSize": 1000,
        "fields": FIELDS,
    }

    total_fetched = 0
    total_us = 0
    page = 0
    next_token = None

    print("Starting ClinicalTrials.gov data fetch...")
    print(f"Database: {DB_PATH}")

    while True:
        page += 1
        if next_token:
            params["pageToken"] = next_token
        elif "pageToken" in params:
            del params["pageToken"]

        try:
            resp = requests.get(API_BASE, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"  API error on page {page}: {e}")
            print("  Retrying in 5s...")
            time.sleep(5)
            continue

        studies = data.get("studies", [])
        if not studies:
            break

        for study in studies:
            total_fetched += 1
            if process_study(study, conn):
                total_us += 1

        conn.commit()

        if total_fetched % 100 == 0 or len(studies) < 1000:
            print(f"  Page {page}: fetched {total_fetched} total, {total_us} US trials")

        next_token = data.get("nextPageToken")
        if not next_token:
            break

        time.sleep(1.5)  # Rate limiting

    conn.commit()

    # Print summary
    cursor = conn.execute("SELECT COUNT(*) FROM trials")
    trial_count = cursor.fetchone()[0]
    cursor = conn.execute("SELECT COUNT(*) FROM locations")
    loc_count = cursor.fetchone()[0]

    print(f"\nDone! {trial_count} US trials stored with {loc_count} locations.")
    print(f"Total studies scanned: {total_fetched}")

    conn.close()


if __name__ == "__main__":
    fetch_all_trials()
