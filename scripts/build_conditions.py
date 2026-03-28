"""
Build condition taxonomy from trial data.
Normalizes condition names, merges near-duplicates, stores top 200.

Usage: python scripts/build_conditions.py
"""

import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "trials.db"

# Common near-duplicate mappings
MERGE_MAP = {
    "type ii diabetes": "type 2 diabetes",
    "type ii diabetes mellitus": "type 2 diabetes",
    "type 2 diabetes mellitus": "type 2 diabetes",
    "diabetes mellitus, type 2": "type 2 diabetes",
    "type i diabetes": "type 1 diabetes",
    "type i diabetes mellitus": "type 1 diabetes",
    "type 1 diabetes mellitus": "type 1 diabetes",
    "diabetes mellitus, type 1": "type 1 diabetes",
    "non-small cell lung cancer": "non-small cell lung cancer",
    "non small cell lung cancer": "non-small cell lung cancer",
    "nsclc": "non-small cell lung cancer",
    "breast neoplasms": "breast cancer",
    "breast carcinoma": "breast cancer",
    "colorectal neoplasms": "colorectal cancer",
    "colorectal carcinoma": "colorectal cancer",
    "colon cancer": "colorectal cancer",
    "prostatic neoplasms": "prostate cancer",
    "prostate neoplasm": "prostate cancer",
    "prostatic cancer": "prostate cancer",
    "lung neoplasms": "lung cancer",
    "pulmonary neoplasm": "lung cancer",
    "depressive disorder, major": "major depressive disorder",
    "major depression": "major depressive disorder",
    "hiv infections": "hiv",
    "hiv infection": "hiv",
    "hiv-1": "hiv",
    "human immunodeficiency virus": "hiv",
    "alzheimer disease": "alzheimer's disease",
    "alzheimers disease": "alzheimer's disease",
    "alzheimer's": "alzheimer's disease",
    "parkinson disease": "parkinson's disease",
    "parkinsons disease": "parkinson's disease",
    "parkinson's": "parkinson's disease",
    "heart failure, congestive": "heart failure",
    "congestive heart failure": "heart failure",
    "rheumatoid arthritis": "rheumatoid arthritis",
    "arthritis, rheumatoid": "rheumatoid arthritis",
    "multiple sclerosis": "multiple sclerosis",
    "ms (multiple sclerosis)": "multiple sclerosis",
    "crohn disease": "crohn's disease",
    "crohns disease": "crohn's disease",
    "crohn's": "crohn's disease",
    "systemic lupus erythematosus": "lupus",
    "sle": "lupus",
    "hepatitis c": "hepatitis c",
    "hepatitis c virus": "hepatitis c",
    "hcv": "hepatitis c",
    "atopic dermatitis": "eczema",
    "obesity, morbid": "obesity",
    "overweight and obesity": "obesity",
    "asthma, bronchial": "asthma",
    "bronchial asthma": "asthma",
    "chronic obstructive pulmonary disease": "copd",
    "copd (chronic obstructive pulmonary disease)": "copd",
    "acute myeloid leukemia": "acute myeloid leukemia",
    "aml": "acute myeloid leukemia",
    "chronic lymphocytic leukemia": "chronic lymphocytic leukemia",
    "cll": "chronic lymphocytic leukemia",
}

# Category mapping for top conditions
CATEGORY_MAP = {
    "cancer": ["cancer", "carcinoma", "neoplasm", "tumor", "tumour", "lymphoma",
               "leukemia", "leukaemia", "melanoma", "sarcoma", "myeloma", "glioblastoma",
               "glioma", "mesothelioma", "neuroblastoma"],
    "heart & blood": ["heart", "cardiac", "cardiovascular", "atrial", "coronary",
                      "hypertension", "blood pressure", "anemia", "anaemia", "thrombosis",
                      "stroke", "artery", "vascular"],
    "brain & nerves": ["alzheimer", "parkinson", "epilepsy", "seizure", "multiple sclerosis",
                       "neuropathy", "migraine", "dementia", "als", "amyotrophic",
                       "huntington", "brain", "neural", "neurolog"],
    "immune & inflammatory": ["lupus", "arthritis", "crohn", "colitis", "psoriasis",
                               "eczema", "dermatitis", "inflammatory", "autoimmune",
                               "immune", "allergy", "asthma"],
    "diabetes & metabolism": ["diabetes", "obesity", "metabolic", "thyroid", "insulin",
                               "glucose", "cholesterol", "lipid"],
    "rare diseases": ["rare", "orphan", "genetic", "hereditary", "congenital",
                      "cystic fibrosis", "sickle cell", "muscular dystrophy",
                      "hemophilia", "thalassemia"],
    "mental health": ["depression", "depressive", "anxiety", "bipolar", "schizophrenia",
                      "ptsd", "ocd", "adhd", "autism", "psychiatric", "mental"],
    "infectious disease": ["hiv", "hepatitis", "tuberculosis", "covid", "sars",
                           "infection", "infectious", "viral", "bacterial", "fungal",
                           "malaria", "sepsis"],
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.rstrip('-')


def normalize_condition(name: str) -> str:
    """Normalize a condition name."""
    name = name.lower().strip()
    name = re.sub(r'\s+', ' ', name)
    return MERGE_MAP.get(name, name)


def categorize_condition(name: str) -> str:
    """Assign a category to a condition."""
    name_lower = name.lower()
    for category, keywords in CATEGORY_MAP.items():
        for keyword in keywords:
            if keyword in name_lower:
                return category
    return "other"


def title_case_condition(name: str) -> str:
    """Smart title case for condition names."""
    small_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    words = name.split()
    result = []
    for i, word in enumerate(words):
        if i == 0 or word not in small_words:
            # Keep acronyms uppercase
            if word.upper() == word and len(word) <= 5:
                result.append(word.upper())
            else:
                result.append(word.capitalize())
        else:
            result.append(word)
    return ' '.join(result)


def build_conditions():
    conn = sqlite3.connect(str(DB_PATH))

    # Get all conditions from trials
    cursor = conn.execute("SELECT conditions_json FROM trials")
    counter = Counter()

    for (conditions_json,) in cursor:
        if not conditions_json:
            continue
        try:
            conditions = json.loads(conditions_json)
            for cond in conditions:
                normalized = normalize_condition(cond)
                counter[normalized] += 1
        except json.JSONDecodeError:
            continue

    # Get top 200 conditions
    top_200 = counter.most_common(200)

    # Clear and rebuild conditions table
    conn.execute("DELETE FROM conditions")

    for name, count in top_200:
        display_name = title_case_condition(name)
        slug = slugify(name)
        category = categorize_condition(name)

        conn.execute("""
            INSERT OR REPLACE INTO conditions (name, slug, trial_count)
            VALUES (?, ?, ?)
        """, (display_name, slug, count))

    conn.commit()

    print(f"Built condition taxonomy: {len(top_200)} conditions")
    print(f"\nTop 20 conditions:")
    for name, count in top_200[:20]:
        cat = categorize_condition(name)
        print(f"  {title_case_condition(name)}: {count} trials [{cat}]")

    conn.close()


if __name__ == "__main__":
    build_conditions()
