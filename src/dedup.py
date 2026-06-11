"""
Deduplication logic.
Filters out jobs whose URLs are already in the Google Sheet.
"""

from typing import List, Set
from src.scraper import Job


def filter_new_jobs(jobs: List[Job], seen_urls: Set[str]) -> List[Job]:
    """Return only jobs not already tracked in the sheet."""
    new_jobs = []
    dupes = 0

    for job in jobs:
        normalized = job.url.rstrip("/")
        if normalized and normalized not in seen_urls:
            new_jobs.append(job)
            seen_urls.add(normalized)  # Prevent dupes within the same run
        else:
            dupes += 1

    if dupes:
        print(f"  Deduplicated: {dupes} already-seen job(s) skipped.")

    return new_jobs
