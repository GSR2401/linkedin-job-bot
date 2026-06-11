# LinkedIn Job Discovery Bot

Automatically finds Easy Apply jobs on LinkedIn across 17 US cities every 4 hours and logs them to a Google Sheet. No LinkedIn login required — zero account ban risk.

---

## Setup (One-Time, ~15 minutes)

Follow these steps **in order**. Steps marked 🌐 require your browser. Steps marked 💻 are terminal commands.

---

### STEP 1 🌐 — Create a Google Cloud Project & Enable Sheets API

1. Go to: https://console.cloud.google.com
2. Click **Select a project** → **New Project**
3. Name it: `linkedin-job-bot` → Click **Create**
4. In the search bar, search: `Google Sheets API`
5. Click **Google Sheets API** → Click **Enable**

---

### STEP 2 🌐 — Create a Service Account & Download Key

1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
2. Make sure your `linkedin-job-bot` project is selected (top left)
3. Click **+ Create Service Account**
4. Name: `linkedin-bot-sa` → Click **Create and Continue** → Click **Done**
5. Click the service account you just created (the row in the table)
6. Click the **Keys** tab → **Add Key** → **Create new key** → **JSON** → **Create**
7. A JSON file downloads automatically — **keep it safe, never commit it**
8. Copy the `client_email` value from the JSON file (you'll need it in Step 3)

---

### STEP 3 🌐 — Create the Google Sheet & Share It

1. Go to: https://sheets.google.com
2. Click **+ Blank** to create a new spreadsheet
3. Rename it: `LinkedIn Jobs` (click on "Untitled spreadsheet" at top)
4. Copy the **Spreadsheet ID** from the URL:
   - URL looks like: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit`
   - Copy the long string between `/d/` and `/edit`
5. Click **Share** (top right) → paste the `client_email` from Step 2 → set role to **Editor** → **Send**

---

### STEP 4 💻 — Update config.yaml

Open `config.yaml` and replace `YOUR_SPREADSHEET_ID_HERE` with your actual Spreadsheet ID:

```yaml
google_sheets:
  spreadsheet_id: "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"  # ← your ID here
```

---

### STEP 5 💻 — Install dependencies & test locally

```bash
# Clone the project (or copy the folder)
cd linkedin-job-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Set your credentials (paste the ENTIRE contents of your JSON key file)
export GOOGLE_CREDENTIALS_JSON='{"type":"service_account","project_id":"..."}'

# Run the bot once to test
python src/main.py
```

**Expected output:**
```
============================================================
LinkedIn Job Discovery Bot
Run started: 2026-06-10 15:00 UTC
============================================================

Loading config...
  Roles: 5 | Locations: 17 | Total searches: 85

Connecting to Google Sheets...
  Connected to sheet: 1BxiMVs0XRA5...

Loading existing job URLs for deduplication...
  0 existing job(s) in tracker.

Starting LinkedIn scrape...
  [1/85] Searching: 'Software Engineer' in 'New York, NY'
    → 18 job(s) found
  ...

Scrape complete: 312 raw job(s) found.
Deduplicating...
  312 new job(s) to add.

Writing to Google Sheets...
  ✓ 312 new job(s) added to tracker.

============================================================
Run complete in 342.1s
  Raw jobs found : 312
  New jobs added : 312
  Dupes skipped  : 0
============================================================
```

Open your Google Sheet — you should see all jobs populated.

---

### STEP 6 💻 — Set up GitHub repo & deploy

```bash
# Install GitHub CLI (if not already installed)
brew install gh

# Login to GitHub
gh auth login

# Create private repo
gh repo create linkedin-job-bot --private --source=. --push

# Add your Google credentials as a secret
# (replace the value with the FULL contents of your JSON key file, on one line)
gh secret set GOOGLE_CREDENTIALS_JSON < /path/to/your/credentials.json
```

That's it. GitHub Actions will now run the bot every 4 hours automatically.

To trigger a manual run: go to your repo on GitHub → **Actions** tab → **LinkedIn Job Discovery** → **Run workflow**.

---

## Checking Runs

- GitHub Actions: `https://github.com/YOUR_USERNAME/linkedin-job-bot/actions`
- Each run shows how many jobs were found and added
- Google Sheet updates within minutes of each run

---

## Customizing

All settings are in `config.yaml` — no code changes needed:

- **Add a role**: Add a line under `search.roles`
- **Add a city**: Add a line under `locations`
- **Change run frequency**: Edit the cron in `.github/workflows/run.yml`
  - Every hour: `0 * * * *` (uses ~1440 Actions min/month — near the 2000 free limit)
  - Every 2 hours: `0 */2 * * *` (~720 min/month — safe)
  - Every 4 hours: `0 */4 * * *` (~360 min/month — default, very safe)

---

## Google Sheet Columns

| Column | Field | Description |
|--------|-------|-------------|
| A | Date Found | When the bot found this job |
| B | Job Title | e.g., Software Engineer II |
| C | Company | e.g., Stripe |
| D | Location | e.g., San Francisco, CA |
| E | LinkedIn URL | Direct link to apply |
| F | Easy Apply | Always "Yes" |
| G | Experience Level | Entry/Associate |
| H | Role Category | Which of the 5 role types |
| I | Status | Update manually: New → Applied / Skipped / Interview |
| J | Notes | Your notes |

---

## Troubleshooting

**"Login wall" warning in logs**
LinkedIn occasionally shows a login page even on public search. This is temporary — the next run usually works. If it persists, increase `delay_min_seconds` in config.yaml.

**0 jobs found in a run**
LinkedIn may have temporarily rate-limited the GitHub Actions IP. Wait for the next run. If it continues, open an issue.

**Google Sheets API error**
Make sure the service account email is shared as Editor on the spreadsheet. Double-check the `spreadsheet_id` in config.yaml.

**`GOOGLE_CREDENTIALS_JSON` not set**
Locally: run `export GOOGLE_CREDENTIALS_JSON='...'` before `python src/main.py`.
On GitHub Actions: run `gh secret set GOOGLE_CREDENTIALS_JSON < credentials.json`.
