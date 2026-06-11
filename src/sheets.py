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
