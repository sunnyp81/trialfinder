#!/bin/bash
# TrialFinder — Weekly Auto-Update
# Fetches fresh trial data, rebuilds site, deploys to Cloudflare Pages
# Schedule: Windows Task Scheduler runs this every Sunday at 3am
#
# Zero cost. No API keys needed (only Wrangler login, done once).

set -e

PROJECT_DIR="C:/Users/sunny/projects/trialfinder"
LOG_FILE="$PROJECT_DIR/scripts/data/update.log"

echo "========================================" >> "$LOG_FILE"
echo "Update started: $(date)" >> "$LOG_FILE"

cd "$PROJECT_DIR"

# Step 1: Fetch fresh trials from ClinicalTrials.gov (~30 min)
echo "[1/5] Fetching trials..." >> "$LOG_FILE"
python scripts/fetch_trials.py >> "$LOG_FILE" 2>&1

# Step 2: Build condition taxonomy
echo "[2/5] Building conditions..." >> "$LOG_FILE"
python scripts/build_conditions.py >> "$LOG_FILE" 2>&1

# Step 3: Export JSON
echo "[3/5] Exporting JSON..." >> "$LOG_FILE"
python scripts/export_json.py >> "$LOG_FILE" 2>&1

# Step 4: Build Astro site
echo "[4/5] Building site..." >> "$LOG_FILE"
cd site
npm run build >> "$LOG_FILE" 2>&1

# Step 5: Deploy to Cloudflare Pages
echo "[5/5] Deploying..." >> "$LOG_FILE"
npx wrangler pages deploy dist --project-name trialfinder --commit-dirty=true >> "$LOG_FILE" 2>&1

echo "Update complete: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
