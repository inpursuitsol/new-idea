from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from pehli_salary.config import ROOT, SCOPES, YOUTUBE_CATEGORY_EDUCATION
from pehli_salary.copy import description_for, validate_title, youtube_tags
from pehli_salary.queue import QueueItem


class MissingYouTubeCredentials(RuntimeError):
    pass


def load_credentials() -> Credentials:
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    if client_id and client_secret and refresh:
        creds = Credentials(
            token=None,
            refresh_token=refresh,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
        creds.refresh(Request())
        return creds
    token_path = ROOT / "token.json"
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json(), encoding="utf-8")
        if creds:
            return creds
    raise MissingYouTubeCredentials(
        "Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN "
        "or run: python3 -m pehli_salary.cli auth"
    )


def run_auth_flow(client_secrets: Path) -> Path:
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
    creds = flow.run_local_server(port=0)
    dest = ROOT / "token.json"
    dest.write_text(creds.to_json(), encoding="utf-8")
    return dest


def build_status(item: QueueItem, *, privacy: str, now: datetime | None = None) -> dict:
    status = {
        "privacyStatus": privacy,
        "selfDeclaredMadeForKids": False,
    }
    publish_at = item.publish_at().astimezone(timezone.utc)
    current = now or datetime.now(timezone.utc)
    if privacy == "private" and publish_at > current:
        status["publishAt"] = publish_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    elif privacy == "private" and publish_at <= current:
        status["privacyStatus"] = "public"
    return status


def upload_video(item: QueueItem, video_path: Path, *, privacy: str = "private") -> dict:
    creds = load_credentials()
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    status = build_status(item, privacy=privacy)
    body = {
        "snippet": {
            "title": validate_title(item.title),
            "description": description_for(item),
            "tags": youtube_tags(item),
            "categoryId": YOUTUBE_CATEGORY_EDUCATION,
            "defaultLanguage": "hi",
            "defaultAudioLanguage": "hi",
        },
        "status": status,
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response
