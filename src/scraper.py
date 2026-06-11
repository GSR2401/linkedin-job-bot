"""
LinkedIn public job search scraper.
No login required — only accesses publicly visible job listings.
"""

import asyncio
import random
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from playwright.async_api import async_playwright, Page, Browser

# LinkedIn experience level codes
EXP_LEVEL_CODES = {
    "entry_level": "1",
    "associate": "2",
    "mid_senior": "3",
    "director": "4",
    "executive": "5",
}

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


def _is_us_location(location: str) -> bool:
    """Return True if location appears to be in the United States."""
    if not location:
        return True  # keep jobs with no location rather than discard
    loc = location.strip()
    if loc.lower() in ("remote", "united states", "usa", "us"):
        return True
    if "united states" in loc.lower():
        return True
    # Match ", NY" / ", CA" etc. at end or before further text
    parts = [p.strip() for p in loc.replace(",", " ").split()]
    for part in parts:
        if part.upper() in US_STATES:
            return True
    return False


USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    date_found: str
    easy_apply: bool
    experience_level: str
    role_category: str
    status: str = "New"
    notes: str = ""
    match_score: int = 0
    matched_skills: str = ""


def build_search_url(role: str, location: str, exp_codes: str, posted_within_hours: int, page_num: int = 0) -> str:
    """Build a LinkedIn public job search URL with all filters."""
    params = {
        "keywords": role,
        "location": location,
        "f_AL": "true",                                      # Easy Apply only
        "f_TPR": f"r{posted_within_hours * 3600}",           # Time filter (seconds)
        "f_E": exp_codes,                                     # Experience level
        "position": str(page_num * 25 + 1),
        "pageNum": str(page_num),
        "origin": "JOB_SEARCH_PAGE_JOB_FILTER",
    }
    query = urllib.parse.urlencode(params)
    return f"https://www.linkedin.com/jobs/search/?{query}"


def normalize_job_url(url: str) -> str:
    """Extract canonical job URL (strip tracking params)."""
    if not url:
        return ""
    # Keep only the base path (e.g., https://www.linkedin.com/jobs/view/1234567890/)
    if "?" in url:
        url = url.split("?")[0]
    if "&" in url:
        url = url.split("&")[0]
    return url.rstrip("/")


async def scrape_jobs(config: dict) -> List[Job]:
    """Main entry point: scrapes all role × location combinations."""
    all_jobs: List[Job] = []

    exp_codes = ",".join(
        EXP_LEVEL_CODES[e]
        for e in config["search"].get("experience_levels", ["entry_level"])
        if e in EXP_LEVEL_CODES
    )

    scraper_cfg = config.get("scraper", {})
    headless = scraper_cfg.get("headless", True)
    delay_min = scraper_cfg.get("delay_min_seconds", 3)
    delay_max = scraper_cfg.get("delay_max_seconds", 7)
    max_pages = scraper_cfg.get("max_pages_per_search", 2)
    posted_within = config["search"].get("posted_within_hours", 24)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        # Block images and fonts to speed up loading
        await context.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf}", lambda route: route.abort())

        page = await context.new_page()

        roles = config["search"]["roles"]
        locations = config["locations"]
        total = len(roles) * len(locations)
        done = 0

        for role in roles:
            for location in locations:
                done += 1
                print(f"  [{done}/{total}] Searching: {role!r} in {location!r}")
                jobs = await _scrape_one(
                    page, role, location, exp_codes, posted_within, max_pages
                )
                all_jobs.extend(jobs)
                print(f"    → {len(jobs)} job(s) found")

                # Human-like delay between searches
                delay = random.uniform(delay_min, delay_max)
                await asyncio.sleep(delay)

        await browser.close()

    return all_jobs


async def _scrape_one(
    page: Page,
    role: str,
    location: str,
    exp_codes: str,
    posted_within: int,
    max_pages: int,
) -> List[Job]:
    """Scrape one role × location combination across multiple pages."""
    jobs: List[Job] = []

    for page_num in range(max_pages):
        url = build_search_url(role, location, exp_codes, posted_within, page_num)
        page_jobs = await _scrape_page(page, url, role)
        jobs.extend(page_jobs)

        # If fewer results than expected, no point fetching next page
        if len(page_jobs) < 10:
            break

        await asyncio.sleep(random.uniform(2, 4))

    return jobs


async def _scrape_page(page: Page, url: str, role_category: str) -> List[Job]:
    """Scrape a single search results page."""
    jobs: List[Job] = []

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # Wait a moment for JS to render job cards
        await asyncio.sleep(2.5)

        # Try to find job cards (LinkedIn uses several selectors depending on layout)
        card_selectors = [
            ".base-card",
            ".jobs-search__results-list > li",
            "[data-entity-urn]",
        ]

        cards = []
        for selector in card_selectors:
            cards = await page.query_selector_all(selector)
            if cards:
                break

        if not cards:
            # May have hit a rate limit or login wall — log and move on
            page_title = await page.title()
            if "Sign In" in page_title or "Log In" in page_title:
                print("    ⚠ LinkedIn is requesting login — skipping this search.")
            return jobs

        for card in cards:
            job = await _parse_card(card, role_category)
            if job:
                jobs.append(job)

    except Exception as e:
        print(f"    ⚠ Error scraping page: {e}")

    return jobs


async def fetch_description(page: Page, url: str) -> str:
    """Fetch the full job description text from a LinkedIn job page."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(1.5)

        selectors = [
            ".description__text",
            ".show-more-less-html__markup",
            ".jobs-description__content",
            "[data-testid='job-details-description']",
            ".job-details-jobs-unified-top-card__job-insight",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    text = await el.inner_text()
                    if text and len(text.strip()) > 50:
                        return text.strip()
            except Exception:
                continue
    except Exception:
        pass
    return ""


async def _parse_card(card, role_category: str) -> Optional[Job]:
    """Extract job data from a single job card element."""
    try:
        # Try multiple selector variants for resilience
        title = await _get_text(card, [
            ".base-search-card__title",
            "h3.base-search-card__title",
            ".job-search-card__title",
            "h3",
        ])
        company = await _get_text(card, [
            ".base-search-card__subtitle",
            "h4.base-search-card__subtitle",
            ".job-search-card__company-name",
            "h4",
        ])
        location = await _get_text(card, [
            ".job-search-card__location",
            ".base-search-card__metadata span",
        ])
        url = await _get_attr(card, [
            "a.base-card__full-link",
            "a[data-tracking-control-name]",
            "a",
        ], "href")

        if not title or not company or not url:
            return None

        if not _is_us_location(location or ""):
            return None

        return Job(
            title=title.strip(),
            company=company.strip(),
            location=(location or "").strip(),
            url=normalize_job_url(url),
            date_found=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            easy_apply=True,
            experience_level="Entry/Associate",
            role_category=role_category,
        )
    except Exception:
        return None


async def _get_text(element, selectors: List[str]) -> Optional[str]:
    for sel in selectors:
        try:
            el = await element.query_selector(sel)
            if el:
                text = await el.inner_text()
                if text and text.strip():
                    return text.strip()
        except Exception:
            continue
    return None


async def _get_attr(element, selectors: List[str], attr: str) -> Optional[str]:
    for sel in selectors:
        try:
            el = await element.query_selector(sel)
            if el:
                val = await el.get_attribute(attr)
                if val:
                    return val
        except Exception:
            continue
    return None
