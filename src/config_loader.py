"""Load and validate config.yaml."""

import yaml
import sys
from pathlib import Path


def load_config(path: str = "config.yaml") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        print(f"[ERROR] Config file not found: {path}")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    _validate(config)
    return config


def _validate(config: dict):
    errors = []

    if not config.get("search", {}).get("roles"):
        errors.append("search.roles is empty or missing")

    if not config.get("locations"):
        errors.append("locations is empty or missing")

    sheet_id = config.get("google_sheets", {}).get("spreadsheet_id", "")
    if not sheet_id or sheet_id == "YOUR_SPREADSHEET_ID_HERE":
        errors.append(
            "google_sheets.spreadsheet_id is not set. "
            "Replace YOUR_SPREADSHEET_ID_HERE with your actual Sheet ID."
        )

    if errors:
        print("[ERROR] Invalid config.yaml:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
