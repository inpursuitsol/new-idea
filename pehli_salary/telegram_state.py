from __future__ import annotations

import json
from pathlib import Path

from pehli_salary.config import TELEGRAM_STATE_PATH


def load_state(path: Path = TELEGRAM_STATE_PATH) -> dict[str, list[str]]:
    if not path.exists():
        return {"tips": [], "feeds": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "tips": list(data.get("tips") or []),
        "feeds": list(data.get("feeds") or []),
    }


def save_state(state: dict[str, list[str]], path: Path = TELEGRAM_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def mark_tip(item_id: str, path: Path = TELEGRAM_STATE_PATH) -> None:
    state = load_state(path)
    if item_id not in state["tips"]:
        state["tips"].append(item_id)
        save_state(state, path)


def mark_feed(entry_id: str, path: Path = TELEGRAM_STATE_PATH) -> None:
    state = load_state(path)
    if entry_id not in state["feeds"]:
        state["feeds"].append(entry_id)
        save_state(state, path)


def seen_tip(item_id: str, path: Path = TELEGRAM_STATE_PATH) -> bool:
    return item_id in load_state(path)["tips"]


def seen_feed(entry_id: str, path: Path = TELEGRAM_STATE_PATH) -> bool:
    return entry_id in load_state(path)["feeds"]
