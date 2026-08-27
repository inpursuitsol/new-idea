from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tv_zerodha.config import Settings
from tv_zerodha.kite_client import BrokerError, exchange_request_token
from tv_zerodha.parse import AlertError, parse_alert
from tv_zerodha.webhook import create_app, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bridge TradingView alerts to Upstox or Zerodha."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("login-url", help="Print the Kite Connect login URL")
    session = sub.add_parser("session", help="Exchange a request_token for a daily access_token")
    session.add_argument("request_token")
    preview = sub.add_parser("preview", help="Parse a TradingView JSON alert without placing an order")
    preview.add_argument("json_file", nargs="?", help="Path to JSON, or stdin if omitted")
    sub.add_parser("serve", help="Run the webhook server")

    args = parser.parse_args(argv)
    settings = Settings.from_env()

    if args.cmd == "login-url":
        try:
            if settings.broker == "upstox":
                from tv_zerodha.upstox import login_url as broker_login_url
            else:
                from tv_zerodha.kite_client import login_url as broker_login_url
            print(broker_login_url(settings))
        except BrokerError as exc:
            print(exc, file=sys.stderr)
            return 2
        return 0

    if args.cmd == "session":
        try:
            if settings.broker == "upstox":
                from tv_zerodha.upstox import exchange_auth_code

                token = exchange_auth_code(settings, args.request_token)
            else:
                token = exchange_request_token(settings, args.request_token)
        except BrokerError as exc:
            print(exc, file=sys.stderr)
            return 2
        print(f"saved access_token to {settings.access_token_path}")
        print(f"token_prefix={token[:6]}…")
        return 0

    if args.cmd == "preview":
        raw = sys.stdin.read() if not args.json_file else Path(args.json_file).read_text(encoding="utf-8")
        try:
            intent = parse_alert(raw, settings)
        except AlertError as exc:
            print(exc, file=sys.stderr)
            return 2
        print(
            json.dumps(
                {
                    "action": intent.action,
                    "exchange": intent.exchange,
                    "tradingsymbol": intent.tradingsymbol,
                    "quantity": intent.quantity,
                    "product": intent.product,
                    "order_type": intent.order_type,
                    "price": intent.price,
                    "trigger_price": intent.trigger_price,
                    "indicator": intent.indicator,
                    "dry_run": settings.dry_run,
                },
                indent=2,
            )
        )
        return 0

    if args.cmd == "serve":
        # imported so tests can monkeypatch create_app
        _ = create_app
        run()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
