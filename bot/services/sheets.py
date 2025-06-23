"""Google Sheets integration.

Uses Service Account JSON stored in env var `GSERVICE_KEY` (base64-encoded) 
+ env `GSHEET_ID` (Spreadsheet ID created manually). 

Provides helper `append_lead(application)` which writes a row with
 timestamp, category, name, phone, e-mail, description, price, status.
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from functools import lru_cache
from typing import TYPE_CHECKING, Any, List

import gspread  # sync lib – fast enough for single row writes
from google.oauth2.service_account import Credentials

if TYPE_CHECKING:  # cyclic-safe import
    from bot.services.db import Application, Category, User


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


@lru_cache(maxsize=1)
def _get_client() -> gspread.Client:
    key_b64 = os.getenv("GSERVICE_KEY")
    sheet_id = os.getenv("GSHEET_ID")
    if not key_b64 or not sheet_id:
        raise RuntimeError("GSERVICE_KEY or GSHEET_ID not set")

    # the key is expected to be base64-encoded JSON
    key_json = base64.b64decode(key_b64).decode()
    info = json.loads(key_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


@lru_cache(maxsize=1)
def _get_sheet():
    client = _get_client()
    sheet_id = os.getenv("GSHEET_ID")
    spreadsheet = client.open_by_key(sheet_id)
    # sheet name leads like "Leads202506" – current year+month
    tab_name = "Leads" + datetime.utcnow().strftime("%Y%m")
    try:
        return spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        # create sheet with headers
        ws = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="20")
        ws.append_row(
            [
                "CreatedAt",
                "Category",
                "Subcategory",
                "Name",
                "Phone",
                "E-mail",
                "Description",
                "Price",
                "Status",
            ],
            value_input_option="USER_ENTERED",
        )
        return ws


def append_lead(app: "Application", user: "User", category: "Category") -> None:
    """Append new lead to Google Sheet. Works synchronously (fast single row)."""
    ws = _get_sheet()
    row: List[Any] = [
        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        category.name if category else "-",
        app.subcategory or "-",
        f"{user.first_name or ''} {user.last_name or ''}".strip() or "-",
        user.phone or "-",
        user.email or "-",
        (app.description or "-")[:500],
        str(app.price or "-"),
        app.status,
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
