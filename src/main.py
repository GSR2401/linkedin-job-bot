"""
LinkedIn Job Discovery Bot — Entry Point
Runs the full pipeline: scrape → deduplicate → write to Google Sheets.
"""

import asyncio
import random
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path so imports work from anywhere
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_loader import load_config
from src.scraper import scrape_jobs, fetch_description
from src.sheets import get_client, get_or_create_worksheet, get_existing_urls, append_jobs
from src.dedup import filter_new_jobs
from src.matcher import is_excluded_by_title, score_job, requires_citizenship
from playwright.async_api import async_playwright


def main():
    start = time.time()
    print(f"\n{'='*60}")
    print(f"LinkedIn Job Discovery Bot")
    print(f"Run started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}\n")

    # ── 1. Load config ──────────────────────────────────────────
    print("Loading config...")
    config = load_config("config.yaml")
    sheets_cfg = config["google_sheets"]
    roles = config["search"]["roles"]
    locations = config["locations"]
    print(f"  Roles: {len(roles)} | Locations: {len(locations)} | Total searches: {len(roles) * len(locations)}")

    # ── 2. Connect to Google Sheets ─────────────────────────────
    print("\nConnecting to Google Sheets...")
    client = get_client(sheets_cfg["credentials_env_var"])
    worksheet = get_or_create_worksheet(
        client,
        sheets_cfg["spreadsheet_id"],
        sheets_cfg["worksheet_name"],
    )
    print(f"  Connected to sheet: {sheets_cfg['spreadsheet_id']}")

    # ── 3. Load existing URLs for deduplication ─────────────────
    print("\nLoading existing job URLs for deduplication...")
    seen_urls = get_existing_urls(worksheet)
    print(f"  {len(seen_urls)} existing job(s) in tracker.")

    # ── 4. Scrape LinkedIn ──────────────────────────────────────
    print("\nStarting LinkedIn scrape...")
    raw_jobs = asyncio.run(scrape_jobs(config))
    print(f"\nScrape complete: {len(raw_jobs)} raw job(s) found across all searches.")

    # ── 5. Deduplicate ──────────────────────────────────────────
    print("\nDeduplicating...")
    new_jobs = filter_new_jobs(raw_jobs, seen_urls)
    print(f"  {len(new_jobs)} new job(s) after dedup.")

    # ── 6. Score jobs against resume ────────────────────────────
    min_score = config.get("matching", {}).get("min_match_score", 2)
    scraper_cfg = config.get("scraper", {})
    delay_min = scraper_cfg.get("delay_min_seconds", 2)
    delay_max = scraper_cfg.get("delay_max_seconds", 4)

    print(f"\nScoring jobs against resume (min score: {min_score})...")
    title_excluded = sum(1 for j in new_jobs if is_excluded_by_title(j.title))
    candidates = [j for j in new_jobs if not is_excluded_by_title(j.title)]
    print(f"  {title_excluded} job(s) excluded by title (iOS/Android/.NET/etc.)")
    print(f"  Fetching descriptions for {len(candidates)} job(s)...")

    async def score_all(jobs):
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
            )
            await context.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf}", lambda r: r.abort())
            page = await context.new_page()

            for i, job in enumerate(jobs, 1):
                desc = await fetch_description(page, job.url)
                if requires_citizenship(desc):
                    job.match_score = -1  # sentinel: skip this job
                else:
                    job.match_score, job.matched_skills = score_job(job.title, desc)
                if (i % 10) == 0 or i == len(jobs):
                    print(f"    Scored {i}/{len(jobs)}...")
                await asyncio.sleep(random.uniform(delay_min, delay_max))

            await browser.close()

    asyncio.run(score_all(candidates))

    citizenship_filtered = sum(1 for j in candidates if j.match_score == -1)
    matched_jobs = [j for j in candidates if j.match_score >= min_score]
    low_score = len(candidates) - len(matched_jobs) - citizenship_filtered
    print(f"  {citizenship_filtered} job(s) skipped (US citizenship / clearance required)")
    print(f"  {low_score} job(s) filtered out (score < {min_score})")
    print(f"  {len(matched_jobs)} job(s) matched your resume.")

    # ── 7. Write to Google Sheets ───────────────────────────────
    if matched_jobs:
        print("\nWriting to Google Sheets...")
        added = append_jobs(worksheet, matched_jobs)
        print(f"  ✓ {added} new job(s) added to tracker.")
    else:
        print("\nNo matching jobs to add.")

    # ── Summary ─────────────────────────────────────────────────
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"Run complete in {elapsed:.1f}s")
    print(f"  Raw jobs found    : {len(raw_jobs)}")
    print(f"  Dupes skipped     : {len(raw_jobs) - len(new_jobs)}")
    print(f"  Title excluded    : {title_excluded}")
    print(f"  Citizenship skip  : {citizenship_filtered}")
    print(f"  Low score filtered: {low_score}")
    print(f"  New jobs added    : {len(matched_jobs)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
