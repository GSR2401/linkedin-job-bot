"""
FastAPI backend for the Scraped Job Feed dashboard.
Serves the job list read from the same Google Sheet the scraper writes to,
and lets the frontend triage (open/delete) jobs. Deletes are soft — see the
pending_deletes grace-window mechanism below — so Undo never has to touch
the sheet at all.
"""

import asyncio
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.config_loader import load_config
from src.sheets import get_client, get_or_create_worksheet, get_all_jobs, delete_jobs_by_urls

PENDING_DELETE_SECONDS = 5
SWEEP_INTERVAL_SECONDS = 1

# Populated at startup; module-level so all requests share one worksheet handle.
worksheet = None

# url -> expiry epoch time. The row is NOT removed from the sheet until the
# sweep loop finds it past expiry — so Undo is just deleting this entry,
# never a sheet write.
pending_deletes: dict = {}


async def _sweep_loop():
    while True:
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
        now = time.time()
        expired = [url for url, expires_at in pending_deletes.items() if expires_at <= now]
        if not expired:
            continue
        delete_jobs_by_urls(worksheet, expired)
        for url in expired:
            pending_deletes.pop(url, None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worksheet
    config = load_config(str(ROOT_DIR / "config.yaml"))
    sheets_cfg = config["google_sheets"]
    client = get_client(sheets_cfg["credentials_env_var"])
    worksheet = get_or_create_worksheet(
        client, sheets_cfg["spreadsheet_id"], sheets_cfg["worksheet_name"]
    )
    print(f"Connected to sheet '{sheets_cfg['worksheet_name']}'.")
    sweep_task = asyncio.create_task(_sweep_loop())
    yield
    sweep_task.cancel()


app = FastAPI(lifespan=lifespan)


def _parse_date_found(raw: str) -> str:
    """Scraper stores 'YYYY-MM-DD HH:MM UTC' — convert to real ISO 8601 so
    the frontend can just do `new Date(isoString)` reliably in any browser."""
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except ValueError:
        return raw


def _to_frontend_job(job: dict) -> dict:
    return {
        "id": job["url"],
        "title": job["title"],
        "company": job["company"],
        "location": job["location"],
        "linkedinUrl": job["url"],
        "easyApply": job["easy_apply"],
        "experienceLevel": job["experience_level"],
        "roleCategory": job["role_category"],
        "matchScore": job["match_score"],
        "matchedSkills": job["matched_skills"],
        "foundAt": _parse_date_found(job["date_found"]),
        "status": job["status"],
        "notes": job["notes"],
    }


@app.get("/api/jobs")
def list_jobs():
    jobs = get_all_jobs(worksheet)
    jobs = [j for j in jobs if j["url"] not in pending_deletes]
    frontend_jobs = [_to_frontend_job(j) for j in jobs]
    return {"jobs": frontend_jobs, "total": len(frontend_jobs)}


class UrlsRequest(BaseModel):
    urls: List[str]


@app.post("/api/jobs/delete")
def delete_jobs(body: UrlsRequest):
    expires_at = time.time() + PENDING_DELETE_SECONDS
    for url in body.urls:
        pending_deletes[url] = expires_at
    return {"pending": body.urls, "expiresInSeconds": PENDING_DELETE_SECONDS}


@app.post("/api/jobs/undo")
def undo_delete(body: UrlsRequest):
    restored, too_late = [], []
    for url in body.urls:
        if url in pending_deletes:
            del pending_deletes[url]
            restored.append(url)
        else:
            too_late.append(url)
    return {"restored": restored, "tooLate": too_late}


app.mount("/", StaticFiles(directory=str(Path(__file__).parent / "static"), html=True), name="static")
