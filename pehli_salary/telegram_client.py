from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from pehli_salary.config import TELEGRAM_CHANNEL_ID


class MissingTelegramCredentials(RuntimeError):
    pass


class TelegramAPIError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise MissingTelegramCredentials(
            "Set TELEGRAM_BOT_TOKEN (from @BotFather). "
            f"Channel defaults to {TELEGRAM_CHANNEL_ID}."
        )
    return token


def _chat_id() -> str:
    return os.environ.get("TELEGRAM_CHANNEL_ID", TELEGRAM_CHANNEL_ID).strip()


def send_message(text: str, *, dry_run: bool = False) -> dict:
    chat_id = _chat_id()
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": "false",
    }
    if dry_run:
        print("DRY RUN")
        print(json.dumps({"chat_id": chat_id, "text": text}, ensure_ascii=False, indent=2))
        return {"dry_run": True}
    url = f"https://api.telegram.org/bot{_token()}/sendMessage"
    body = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise TelegramAPIError(f"Telegram HTTP {exc.code}: {detail}") from exc
    if not data.get("ok"):
        raise TelegramAPIError(json.dumps(data, ensure_ascii=False))
    return data
