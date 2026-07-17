"""
Google Sheets read/write operations via gspread.
Uses a Service Account for authentication (no OAuth prompt needed).
"""

import json
import os
import time
from typing import List, Set

import gspread
from google.oauth2.service_account import Credentials

from src.scraper import normalize_job_url

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

HEADER_ROW = [
    "Date Found",
    "Job Title",
    "Company",
    "Location",
    "LinkedIn URL",
    "Easy Apply",
    "Experience Level",
    "Role Category",
    "Match Score",
    "Matched Skills",
    "Status",
    "Notes",
]

# Column index (0-based) for the URL — used for deduplication
URL_COL_INDEX = 4


def get_client(credentials_env_var: str) -> gspread.Client:
    """Authenticate with Google Sheets API using Service Account credentials."""
    creds_json = os.environ.get(credentials_env_var)
    if not creds_json:
        raise EnvironmentError(
            f"Environment variable '{credentials_env_var}' is not set. "
            "Set it to the contents of your Google Service Account JSON key."
        )

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_worksheet(client: gspread.Client, spreadsheet_id: str, worksheet_name: str) -> gspread.Worksheet:
    """Open the target worksheet, creating it with headers if it doesn't exist."""
    spreadsheet = client.open_by_key(spreadsheet_id)

    try:
        ws = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=len(HEADER_ROW))
        ws.append_row(HEADER_ROW, value_input_option="RAW")
        _format_header(ws)
        print(f"  Created worksheet '{worksheet_name}' with headers.")

    # Ensure header row exists even on existing sheets
    existing = ws.row_values(1)
    if not existing or existing[0] != "Date Found":
        ws.insert_row(HEADER_ROW, index=1, value_input_option="RAW")
        _format_header(ws)

    return ws


def get_existing_urls(ws: gspread.Worksheet) -> Set[str]:
    """Return a set of all job URLs already in the sheet (for deduplication)."""
    try:
        # Fetch only column E (URLs) — much faster than fetching all data
        url_col = ws.col_values(URL_COL_INDEX + 1)  # gspread is 1-indexed
        # Skip header row
        return {url.strip().rstrip("/") for url in url_col[1:] if url.strip()}
    except Exception as e:
        print(f"  Warning: Could not fetch existing URLs: {e}")
        return set()


def append_jobs(ws: gspread.Worksheet, jobs: list) -> int:
    """Append a list of Job objects to the sheet. Returns number of rows added."""
    if not jobs:
        return 0

    rows = [
        [
            job.date_found,
            job.title,
            job.company,
            job.location,
            job.url,
            "Yes",
            job.experience_level,
            job.role_category,
            job.match_score,
            job.matched_skills,
            job.status,
            job.notes,
        ]
        for job in jobs
    ]

    # Batch append with retry
    for attempt in range(3):
        try:
            ws.append_rows(rows, value_input_option="RAW", insert_data_option="INSERT_ROWS")
            return len(rows)
        except gspread.exceptions.APIError as e:
            if attempt < 2:
                print(f"  Sheets API error (attempt {attempt + 1}/3): {e}. Retrying in 10s...")
                time.sleep(10)
            else:
                raise

    return 0


def get_all_jobs(ws: gspread.Worksheet) -> List[dict]:
    """Read every data row in the sheet and return one dict per job.

    Skips rows with no URL (blank/malformed rows). URL is normalized the same
    way the scraper/dedup logic does, since it's the natural unique key.
    """
    values = ws.get_all_values()
    if len(values) <= 1:
        return []

    jobs = []
    for row in values[1:]:
        row = row + [""] * (len(HEADER_ROW) - len(row))  # pad short rows
        url = normalize_job_url(row[4].strip())
        if not url:
            continue
        try:
            match_score = int(row[8])
        except ValueError:
            match_score = 0
        jobs.append({
            "date_found": row[0],
            "title": row[1],
            "company": row[2],
            "location": row[3],
            "url": url,
            "easy_apply": row[5].strip().lower() == "yes",
            "experience_level": row[6],
            "role_category": row[7],
            "match_score": match_score,
            "matched_skills": row[9],
            "status": row[10],
            "notes": row[11],
        })
    return jobs


def delete_job_by_url(ws: gspread.Worksheet, url: str) -> bool:
    """Delete the single row matching `url`. Re-resolves the row index from a
    fresh read every call — never relies on a cached row number, since indices
    shift after any deletion. Returns True if a matching row was found and
    deleted, False if the URL wasn't present (already gone / race)."""
    target = normalize_job_url(url)
    url_col = ws.col_values(URL_COL_INDEX + 1)  # 1-indexed
    for i, cell in enumerate(url_col[1:], start=2):  # row 1 is header
        if normalize_job_url(cell.strip()) == target:
            ws.delete_rows(i)
            return True
    return False


def delete_jobs_by_urls(ws: gspread.Worksheet, urls: List[str]) -> int:
    """Delete every row whose URL is in `urls`. Resolves all matching row
    indices from a single fresh read, then deletes in descending order so
    earlier deletions don't shift the indices of rows still pending deletion.
    Returns the count actually deleted (ignores URLs no longer present)."""
    targets = {normalize_job_url(u) for u in urls}
    if not targets:
        return 0

    url_col = ws.col_values(URL_COL_INDEX + 1)
    matched_rows = [
        i for i, cell in enumerate(url_col[1:], start=2)
        if normalize_job_url(cell.strip()) in targets
    ]
    for row_idx in sorted(matched_rows, reverse=True):
        ws.delete_rows(row_idx)
    return len(matched_rows)


def _format_header(ws: gspread.Worksheet):
    """Apply basic formatting to the header row."""
    try:
        ws.format("A1:L1", {
            "backgroundColor": {"red": 0.12, "green": 0.31, "blue": 0.49},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "horizontalAlignment": "CENTER",
        })
        # Freeze header row
        ws.spreadsheet.batch_update({
            "requests": [{
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": ws.id,
                        "gridProperties": {"frozenRowCount": 1},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            }]
        })
    except Exception:
        pass  # Formatting is cosmetic — don't fail if it errors
