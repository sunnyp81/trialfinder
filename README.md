# TrialFinder — Clinical Trials in Plain English

Static site that pulls recruiting US clinical trials from ClinicalTrials.gov, rewrites eligibility criteria into plain English using Claude, and serves them as an Astro site on Cloudflare Pages.

## Setup

### 1. Python Pipeline

```bash
cd scripts
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your keys:
- `ANTHROPIC_API_KEY` — get at [console.anthropic.com](https://console.anthropic.com)
- `STATIC_FORMS_KEY` — get at [staticforms.dev](https://staticforms.dev)

### 2. Fetch Trial Data

```bash
python scripts/fetch_trials.py
```

Pulls all recruiting/enrolling US trials from ClinicalTrials.gov API. Takes ~30 minutes. No API key needed.

### 3. Rewrite Eligibility (AI)

```bash
python scripts/rewrite_eligibility.py
```

Rewrites eligibility criteria into plain English using Claude Sonnet. Estimated cost: ~$0.002 per trial.

### 4. Build Conditions & Export

```bash
python scripts/build_conditions.py
python scripts/export_json.py
```

### 5. Build & Deploy Site

```bash
cd site
npm install
npm run build
npm run deploy
```

Deploy command: `npx wrangler pages deploy dist --project-name trialfinder`

### 6. Cloudflare Pages Setup

Connect GitHub repo in Cloudflare dashboard:
- Build command: `npm run build`
- Output directory: `dist`
- Root directory: `site`

## Stack

- **Data**: Python + SQLite + ClinicalTrials.gov v2 API
- **AI**: Anthropic Claude (eligibility rewriting)
- **Site**: Astro 5 + Tailwind CSS v4
- **Hosting**: Cloudflare Pages
- **Forms**: StaticForms

## Data Refresh

Run the pipeline periodically to update trial data:

```bash
python scripts/fetch_trials.py
python scripts/rewrite_eligibility.py  # only rewrites new trials
python scripts/build_conditions.py
python scripts/export_json.py
cd site && npm run build && npm run deploy
```
