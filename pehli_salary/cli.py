from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pehli_salary")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("plan", help="Print the content calendar")

    due = sub.add_parser("due", help="Show items scheduled for a day")
    due.add_argument("--date", dest="day", default=None, help="YYYY-MM-DD in IST")

    rend = sub.add_parser("render", help="Render one item by id")
    rend.add_argument("--id", required=True)

    rd = sub.add_parser("render-due", help="Render items due today (IST)")
    rd.add_argument("--date", dest="day", default=None)

    pub = sub.add_parser("publish-due", help="Render and upload due items")
    pub.add_argument("--date", dest="day", default=None)
    pub.add_argument("--dry-run", action="store_true")
    pub.add_argument("--privacy", default="private", choices=["private", "public", "unlisted"])

    auth = sub.add_parser("auth", help="Browser OAuth; writes token.json")
    auth.add_argument("--client-secrets", default="client_secret.json")
    auth.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Local callback port (use 8080 on ChromeOS Penguin)",
    )
    auth.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open a browser; paste the printed URL yourself",
    )

    args = parser.parse_args(argv)
    if args.cmd == "auth":
        from pehli_salary.auth import run_auth_flow

        dest = run_auth_flow(
            Path(args.client_secrets),
            port=args.port,
            open_browser=not args.no_browser,
        )
        print(f"Wrote {dest}. Put refresh_token in YOUTUBE_REFRESH_TOKEN.")
        return 0
    if args.cmd == "plan":
        return cmd_plan()
    if args.cmd == "due":
        return cmd_due(_parse_day(args.day))
    if args.cmd == "render":
        from pehli_salary.render import render_item

        item = _by_id(args.id)
        print(render_item(item))
        return 0
    if args.cmd == "render-due":
        return cmd_render_due(_parse_day(args.day))
    if args.cmd == "publish-due":
        return cmd_publish(_parse_day(args.day), dry_run=args.dry_run, privacy=args.privacy)
    return 1


def _parse_day(value: str | None) -> date:
    from pehli_salary.queue import today_ist

    return date.fromisoformat(value) if value else today_ist()


def _by_id(item_id: str):
    from pehli_salary.queue import load_queue

    for item in load_queue():
        if item.id == item_id:
            return item
    raise SystemExit(f"unknown id: {item_id}")


def cmd_plan() -> int:
    from pehli_salary.queue import load_queue

    for item in load_queue():
        when = item.publish_at().isoformat()
        print(f"{item.id:6} {item.kind:8} {when}  {item.title}")
    return 0


def cmd_due(day: date) -> int:
    from pehli_salary.queue import items_for_day

    due = items_for_day(day)
    if not due:
        print(f"No items on {day.isoformat()}")
        return 0
    for item in due:
        print(json.dumps({"id": item.id, "title": item.title, "kind": item.kind}, ensure_ascii=False))
    return 0


def cmd_render_due(day: date) -> int:
    from pehli_salary.queue import items_for_day
    from pehli_salary.render import render_item

    due = items_for_day(day)
    if not due:
        print(f"No items on {day.isoformat()}")
        return 0
    for item in due:
        print(render_item(item))
    return 0


def cmd_publish(day: date, *, dry_run: bool, privacy: str) -> int:
    from pehli_salary.copy import description_for, validate_title
    from pehli_salary.queue import items_for_day
    from pehli_salary.render import render_item
    from pehli_salary.youtube_client import MissingYouTubeCredentials, upload_video

    due = items_for_day(day)
    if not due:
        print(f"No items on {day.isoformat()}")
        return 0
    for item in due:
        video = render_item(item)
        payload = {
            "id": item.id,
            "title": validate_title(item.title),
            "description": description_for(item),
            "publish_at": item.publish_at().isoformat(),
            "video": str(video),
            "privacy": privacy,
        }
        if dry_run:
            print("DRY RUN")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            continue
        try:
            response = upload_video(item, video, privacy=privacy)
        except MissingYouTubeCredentials as exc:
            print(str(exc))
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 2
        print(json.dumps({"id": item.id, "youtube": response.get("id")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
