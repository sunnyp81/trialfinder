"""
Export trial data from SQLite to JSON files for Astro site.

Usage: python scripts/export_json.py
"""

import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "trials.db"
OUTPUT_DIR = Path(__file__).parent.parent / "site" / "src" / "data"

US_STATES = {
    "Alabama": "alabama", "Alaska": "alaska", "Arizona": "arizona",
    "Arkansas": "arkansas", "California": "california", "Colorado": "colorado",
    "Connecticut": "connecticut", "Delaware": "delaware", "Florida": "florida",
    "Georgia": "georgia", "Hawaii": "hawaii", "Idaho": "idaho",
    "Illinois": "illinois", "Indiana": "indiana", "Iowa": "iowa",
    "Kansas": "kansas", "Kentucky": "kentucky", "Louisiana": "louisiana",
    "Maine": "maine", "Maryland": "maryland", "Massachusetts": "massachusetts",
    "Michigan": "michigan", "Minnesota": "minnesota", "Mississippi": "mississippi",
    "Missouri": "missouri", "Montana": "montana", "Nebraska": "nebraska",
    "Nevada": "nevada", "New Hampshire": "new-hampshire", "New Jersey": "new-jersey",
    "New Mexico": "new-mexico", "New York": "new-york", "North Carolina": "north-carolina",
    "North Dakota": "north-dakota", "Ohio": "ohio", "Oklahoma": "oklahoma",
    "Oregon": "oregon", "Pennsylvania": "pennsylvania", "Rhode Island": "rhode-island",
    "South Carolina": "south-carolina", "South Dakota": "south-dakota",
    "Tennessee": "tennessee", "Texas": "texas", "Utah": "utah",
    "Vermont": "vermont", "Virginia": "virginia", "Washington": "washington",
    "West Virginia": "west-virginia", "Wisconsin": "wisconsin", "Wyoming": "wyoming",
    "District of Columbia": "district-of-columbia", "Puerto Rico": "puerto-rico",
}


def export_trials(conn: sqlite3.Connection) -> list[dict]:
    """Export all trials with rewritten eligibility."""
    cursor = conn.execute("""
        SELECT nct_id, brief_title, official_title, status, phase, study_type,
               conditions_json, interventions_json, locations_json,
               min_age, max_age, sex, healthy_volunteers,
               contact_name, contact_email, contact_phone,
               can_join, cannot_join, plain_summary,
               start_date, slug, brief_summary
        FROM trials
        ORDER BY status, brief_title
    """)

    trials = []
    for row in cursor:
        (nct_id, brief_title, official_title, status, phase, study_type,
         conditions_json, interventions_json, locations_json,
         min_age, max_age, sex, healthy_volunteers,
         contact_name, contact_email, contact_phone,
         can_join, cannot_join, plain_summary,
         start_date, slug, brief_summary) = row

        # Parse JSON fields
        conditions = json.loads(conditions_json) if conditions_json else []
        interventions = json.loads(interventions_json) if interventions_json else []
        locations = json.loads(locations_json) if locations_json else []
        can_join_list = json.loads(can_join) if can_join else []
        cannot_join_list = json.loads(cannot_join) if cannot_join else []

        # Get unique states from locations
        states = list({loc.get("state", "") for loc in locations if loc.get("state")})

        trial = {
            "nctId": nct_id,
            "briefTitle": brief_title,
            "officialTitle": official_title or "",
            "status": status,
            "phase": phase,
            "studyType": study_type or "",
            "conditions": conditions,
            "interventions": [
                {"name": i.get("name", ""), "type": i.get("type", "")}
                for i in interventions
            ] if interventions else [],
            "locations": locations,
            "states": sorted(states),
            "locationCount": len(locations),
            "minAge": min_age or "",
            "maxAge": max_age or "",
            "sex": sex or "ALL",
            "healthyVolunteers": healthy_volunteers or "",
            "contactName": contact_name or "",
            "contactEmail": contact_email or "",
            "contactPhone": contact_phone or "",
            "canJoin": can_join_list,
            "cannotJoin": cannot_join_list,
            "plainSummary": plain_summary or brief_summary or "",
            "startDate": start_date or "",
            "slug": slug,
        }
        trials.append(trial)

    return trials


def export_conditions(conn: sqlite3.Connection) -> list[dict]:
    """Export condition taxonomy."""
    cursor = conn.execute("""
        SELECT name, slug, trial_count
        FROM conditions
        ORDER BY trial_count DESC
    """)

    conditions = []
    for name, slug, count in cursor:
        conditions.append({
            "name": name,
            "slug": slug,
            "trialCount": count,
        })

    return conditions


def export_states(conn: sqlite3.Connection) -> list[dict]:
    """Export state data with trial counts."""
    cursor = conn.execute("""
        SELECT state, state_slug, COUNT(DISTINCT trial_id) as trial_count
        FROM locations
        WHERE state != '' AND state_slug != ''
        GROUP BY state
        ORDER BY trial_count DESC
    """)

    states = []
    for state, slug, count in cursor:
        # Only include recognized US states
        if state in US_STATES:
            states.append({
                "name": state,
                "slug": US_STATES[state],
                "trialCount": count,
            })

    return states


def export_cities(trials: list[dict]) -> list[dict]:
    """Build city data from trial locations."""
    city_map: dict[str, dict] = {}

    for trial in trials:
        for loc in trial.get("locations", []):
            city = loc.get("city", "")
            state = loc.get("state", "")
            if not city or not state:
                continue

            key = f"{city}, {state}"
            slug = f"{city}-{state}".lower().replace(' ', '-').replace('.', '')
            slug = ''.join(c for c in slug if c.isalnum() or c == '-')

            if key not in city_map:
                city_map[key] = {
                    "name": city,
                    "state": state,
                    "displayName": key,
                    "slug": slug,
                    "trialCount": 0,
                    "facilities": set(),
                }
            city_map[key]["trialCount"] += 1
            if loc.get("facility"):
                city_map[key]["facilities"].add(loc["facility"])

    cities = []
    for data in sorted(city_map.values(), key=lambda x: x["trialCount"], reverse=True):
        data["facilities"] = sorted(data["facilities"])
        data["facilityCount"] = len(data["facilities"])
        cities.append(data)

    return cities


def export_drugs(trials: list[dict]) -> list[dict]:
    """Build drug/intervention data from trials."""
    drug_map: dict[str, dict] = {}

    for trial in trials:
        for intv in trial.get("interventions", []):
            name = intv.get("name", "").strip()
            itype = intv.get("type", "").strip()
            if not name or len(name) < 3:
                continue

            key = name.lower()
            slug = key.replace(' ', '-').replace('/', '-').replace('.', '')
            slug = ''.join(c for c in slug if c.isalnum() or c == '-')
            slug = slug.strip('-')

            if key not in drug_map:
                drug_map[key] = {
                    "name": name,
                    "slug": slug,
                    "type": itype,
                    "trialCount": 0,
                }
            drug_map[key]["trialCount"] += 1
            # Keep the most common casing
            if drug_map[key]["trialCount"] == 1:
                drug_map[key]["name"] = name

    # Return top 500 by trial count (filter noise)
    drugs = sorted(drug_map.values(), key=lambda x: x["trialCount"], reverse=True)
    return [d for d in drugs[:500] if d["trialCount"] >= 2]


def export_phases(trials: list[dict]) -> list[dict]:
    """Build phase data from trials."""
    phase_map: dict[str, int] = {}
    for trial in trials:
        phase = trial.get("phase", "Not Applicable")
        if not phase:
            phase = "Not Applicable"
        # Normalize multi-phase entries
        for p in phase.split(", "):
            p = p.strip()
            if p:
                phase_map[p] = phase_map.get(p, 0) + 1

    phase_order = ["EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "Not Applicable"]
    phase_display = {
        "EARLY_PHASE1": "Early Phase 1",
        "PHASE1": "Phase 1",
        "PHASE2": "Phase 2",
        "PHASE3": "Phase 3",
        "PHASE4": "Phase 4",
        "Not Applicable": "Not Applicable",
    }

    phases = []
    for p in phase_order:
        if p in phase_map:
            slug = p.lower().replace('_', '-')
            phases.append({
                "name": phase_display.get(p, p),
                "key": p,
                "slug": slug,
                "trialCount": phase_map[p],
            })

    return phases


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))

    # Export trials
    print("Exporting trials...")
    trials = export_trials(conn)
    trials_path = OUTPUT_DIR / "trials.json"
    with open(trials_path, 'w', encoding='utf-8') as f:
        json.dump(trials, f, ensure_ascii=False)
    print(f"  {len(trials)} trials → {trials_path}")

    # Export conditions
    print("Exporting conditions...")
    conditions = export_conditions(conn)
    conditions_path = OUTPUT_DIR / "conditions.json"
    with open(conditions_path, 'w', encoding='utf-8') as f:
        json.dump(conditions, f, ensure_ascii=False, indent=2)
    print(f"  {len(conditions)} conditions → {conditions_path}")

    # Export states
    print("Exporting states...")
    states = export_states(conn)
    states_path = OUTPUT_DIR / "states.json"
    with open(states_path, 'w', encoding='utf-8') as f:
        json.dump(states, f, ensure_ascii=False, indent=2)
    print(f"  {len(states)} states → {states_path}")

    # Export cities
    print("Exporting cities...")
    cities = export_cities(trials)
    cities_path = OUTPUT_DIR / "cities.json"
    with open(cities_path, 'w', encoding='utf-8') as f:
        json.dump(cities, f, ensure_ascii=False, indent=2)
    print(f"  {len(cities)} cities → {cities_path}")

    # Export drugs/interventions
    print("Exporting drugs/interventions...")
    drugs = export_drugs(trials)
    drugs_path = OUTPUT_DIR / "drugs.json"
    with open(drugs_path, 'w', encoding='utf-8') as f:
        json.dump(drugs, f, ensure_ascii=False, indent=2)
    print(f"  {len(drugs)} drugs → {drugs_path}")

    # Export phases
    print("Exporting phases...")
    phases = export_phases(trials)
    phases_path = OUTPUT_DIR / "phases.json"
    with open(phases_path, 'w', encoding='utf-8') as f:
        json.dump(phases, f, ensure_ascii=False, indent=2)
    print(f"  {len(phases)} phases → {phases_path}")

    # Summary stats for site
    recruiting = sum(1 for t in trials if t["status"] == "RECRUITING")
    enrolling = sum(1 for t in trials if t["status"] == "NOT_YET_RECRUITING")
    print(f"\nSummary: {recruiting} recruiting, {enrolling} enrolling soon")
    print(f"Conditions: {len(conditions)}, States: {len(states)}")
    print(f"Cities: {len(cities)}, Drugs: {len(drugs)}, Phases: {len(phases)}")

    conn.close()


if __name__ == "__main__":
    main()
