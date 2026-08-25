from __future__ import annotations

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from pehli_salary.config import ROOT, SCOPES


def run_auth_flow(
    client_secrets: Path,
    *,
    port: int = 8080,
    open_browser: bool = True,
) -> Path:
    secrets = Path(client_secrets)
    if not secrets.is_file():
        raise SystemExit(
            f"No file at {secrets}. Copy your Google JSON here first, e.g.\n"
            "  cp ~/client_secret_*.json ~/youtube-uploader/client_secret.json"
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
    print(
        "A Google login page is required. If no browser opens, copy the URL "
        "from this terminal into the Linux browser (same Google account as "
        "@Contentlovers108)."
    )
    creds = flow.run_local_server(
        host="127.0.0.1",
        port=port,
        open_browser=open_browser,
        bind_addr="127.0.0.1",
    )
    dest = ROOT / "token.json"
    dest.write_text(creds.to_json(), encoding="utf-8")
    return dest
