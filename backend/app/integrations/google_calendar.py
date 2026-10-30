from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import httplib2
from google_auth_httplib2 import AuthorizedHttp

from app.config import ROOT, settings

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


def _credentials_file() -> Path:
    path = Path(settings.google_credentials_path)
    if not path.is_absolute():
        path = ROOT / path
    return path


def _token_file() -> Path:
    path = Path(settings.google_token_path)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _client_config() -> dict[str, Any]:
    creds_path = _credentials_file()
    if creds_path.exists():
        return json.loads(creds_path.read_text())
    if settings.google_client_id and settings.google_client_secret:
        return {
            "installed": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
    raise RuntimeError("Нет Google credentials: положите credentials.json или задайте GOOGLE_CLIENT_ID/SECRET")


def load_credentials() -> Optional[Credentials]:
    token = _token_file()
    if not token.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(token), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token.write_text(creds.to_json())
    return creds


def is_connected() -> bool:
    creds = load_credentials()
    return bool(creds and creds.valid)


def start_oauth() -> Credentials:
    flow = InstalledAppFlow.from_client_config(_client_config(), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    _token_file().write_text(creds.to_json())
    return creds


def calendar_service():
    creds = load_credentials()
    if not creds or not creds.valid:
        raise RuntimeError("Google Calendar не подключён")
    http = AuthorizedHttp(creds, http=httplib2.Http(timeout=5))
    return build("calendar", "v3", http=http, cache_discovery=False)


def list_events(time_min: datetime, time_max: datetime) -> list[dict[str, Any]]:
    service = calendar_service()
    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=250,
        )
        .execute()
    )
    items = []
    for ev in result.get("items", []):
        start = ev.get("start", {})
        end = ev.get("end", {})
        items.append(
            {
                "id": ev.get("id"),
                "title": ev.get("summary") or "Без названия",
                "start": start.get("dateTime") or start.get("date"),
                "end": end.get("dateTime") or end.get("date"),
                "htmlLink": ev.get("htmlLink"),
            }
        )
    return items


def create_event(payload: dict[str, Any]) -> dict[str, Any]:
    service = calendar_service()
    body: dict[str, Any] = {
        "summary": payload["title"],
        "description": payload.get("description") or "",
        "start": {"dateTime": payload["start"], "timeZone": payload.get("timezone") or "Europe/Moscow"},
        "end": {"dateTime": payload["end"], "timeZone": payload.get("timezone") or "Europe/Moscow"},
    }
    if payload.get("recurrence"):
        body["recurrence"] = payload["recurrence"]
    created = service.events().insert(calendarId="primary", body=body).execute()
    return {
        "id": created.get("id"),
        "title": created.get("summary"),
        "htmlLink": created.get("htmlLink"),
    }
