from __future__ import annotations

import hmac
import html
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from tv_zerodha.config import Settings
from tv_zerodha.kite_client import Broker, BrokerError, build_broker
from tv_zerodha.parse import AlertError, parse_alert


def create_app(settings: Settings | None = None, broker: Broker | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    broker = broker or build_broker(settings)
    app = FastAPI(title="TradingView → broker", version="0.1.0")
    recent: list[dict[str, Any]] = []

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return _home_page(settings, recent)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "dry_run": settings.dry_run,
            "practice": settings.dry_run,
            "broker": settings.broker,
            "stock": settings.default_symbol,
            "logged_in": settings.logged_in(),
            "has_webhook_secret": bool(settings.webhook_secret),
        }

    @app.get("/login")
    def login() -> RedirectResponse:
        try:
            url = _login_url(settings)
        except BrokerError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(url)

    @app.get("/upstox/callback")
    def upstox_callback(code: str = "") -> HTMLResponse:
        from tv_zerodha.upstox import exchange_auth_code

        if not code:
            raise HTTPException(status_code=400, detail="Upstox did not send a login code")
        try:
            exchange_auth_code(settings, code)
        except BrokerError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return HTMLResponse(_ok_page("Logged in to Upstox for today. You can close this tab."))

    @app.get("/zerodha/callback")
    def zerodha_callback(request_token: str = "", status: str = "") -> HTMLResponse:
        from tv_zerodha.kite_client import exchange_request_token

        if status and status != "success":
            raise HTTPException(status_code=400, detail="Zerodha login was cancelled")
        if not request_token:
            raise HTTPException(status_code=400, detail="Zerodha did not send a request token")
        try:
            exchange_request_token(settings, request_token)
        except BrokerError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return HTMLResponse(_ok_page("Logged in to Zerodha for today. You can close this tab."))

    @app.api_route("/buy/{secret}", methods=["GET", "POST"])
    @app.api_route("/sell/{secret}", methods=["GET", "POST"])
    async def simple_alert(secret: str, request: Request) -> Any:
        action = "BUY" if "/buy/" in request.url.path else "SELL"
        _assert_path_secret(settings, secret)
        if request.method == "GET":
            return JSONResponse(
                {
                    "ok": True,
                    "hint": "TradingView should POST to this link. Opening it in a browser does not place an order.",
                    "action": action,
                    "stock": settings.default_symbol,
                    "practice": settings.dry_run,
                }
            )
        body = await request.body()
        return _place(settings, broker, recent, body, action_override=action)

    @app.post("/webhook/tradingview")
    async def tradingview_webhook(
        request: Request,
        x_tv_secret: str | None = Header(default=None, alias="X-TV-Secret"),
    ) -> JSONResponse:
        body = await request.body()
        try:
            payload = _decode_body(body)
        except AlertError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _assert_secret(settings, payload, x_tv_secret)
        return _place(settings, broker, recent, payload)

    return app


def _place(
    settings: Settings,
    broker: Broker,
    recent: list[dict[str, Any]],
    payload: Any,
    action_override: str | None = None,
) -> JSONResponse:
    try:
        intent = parse_alert(payload, settings, action_override=action_override)
        result = broker.place(intent)
    except AlertError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BrokerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    body = {
        "ok": True,
        "dry_run": result.get("dry_run"),
        "practice": result.get("dry_run"),
        "order_id": result.get("order_id"),
        "order": result.get("order"),
        "indicator": intent.indicator,
        "broker": result.get("broker") or settings.broker,
    }
    recent.insert(0, body)
    del recent[20:]
    return JSONResponse(body)


def _decode_body(body: bytes) -> Any:
    from tv_zerodha.parse import parse_json_object

    return parse_json_object(body)


def _assert_path_secret(settings: Settings, provided: str) -> None:
    expected = settings.webhook_secret
    if not expected:
        raise HTTPException(status_code=503, detail="Set secret in trade.yaml")
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="wrong secret in the link")


def _assert_secret(settings: Settings, payload: Any, header_secret: str | None) -> None:
    expected = settings.webhook_secret
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Set secret in trade.yaml",
        )
    provided = header_secret
    if not provided and isinstance(payload, dict):
        provided = str(payload.get("secret") or payload.get("passphrase") or "")
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="invalid webhook secret")


def _login_url(settings: Settings) -> str:
    if settings.broker == "upstox":
        from tv_zerodha.upstox import login_url as upstox_login_url

        return upstox_login_url(settings)
    from tv_zerodha.kite_client import login_url as kite_login_url

    return kite_login_url(settings)


def _home_page(settings: Settings, recent: list[dict[str, Any]]) -> str:
    mode = "Practice mode is ON — no real orders" if settings.dry_run else "LIVE — real orders can be sent"
    stock = settings.default_symbol or "(set stock in trade.yaml)"
    secret = settings.webhook_secret or "your-secret"
    base = settings.public_base_url or "https://YOUR-PUBLIC-HTTPS-LINK"
    buy = f"{base}/buy/{secret}"
    sell = f"{base}/sell/{secret}"
    rows = "".join(
        f"<li>{html.escape(str(item.get('order_id')))} {html.escape(str(item.get('indicator')))}</li>"
        for item in recent[:8]
    ) or "<li>None yet</li>"
    logged = "Yes, for today" if settings.logged_in() else "No — click Log in"
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>TradingView trades</title>
<style>
body {{ font-family: sans-serif; max-width: 40rem; margin: 2rem auto; line-height: 1.4; }}
code, input {{ font-size: 0.95rem; word-break: break-all; }}
.box {{ background: #f4f4f0; padding: 0.8rem 1rem; margin: 0.8rem 0; }}
.warn {{ color: #8a1c1c; }}
</style></head><body>
<h1>TradingView → {html.escape(settings.broker)}</h1>
<p><strong>{html.escape(mode)}</strong></p>
<p>Stock: <strong>{html.escape(stock)}</strong> &nbsp; Quantity: {settings.default_quantity}<br>
Logged in: {html.escape(logged)}</p>
<p><a href="/login">Log in to {html.escape(settings.broker)}</a> (do this every morning)</p>
<div class="box">
<p>In TradingView, paste these as the webhook URL. One alert for Buy, one for Sell.</p>
<p>Buy link<br><code>{html.escape(buy)}</code></p>
<p>Sell link<br><code>{html.escape(sell)}</code></p>
<p>If the links still say YOUR-PUBLIC-HTTPS-LINK, TradingView cannot reach this computer yet. See docs/START_HERE.md.</p>
</div>
<p>Recent alerts</p>
<ul>{rows}</ul>
<p><a href="/health">status</a></p>
</body></html>"""


def _ok_page(message: str) -> str:
    return f"<!doctype html><html><body><p>{html.escape(message)}</p><p><a href='/'>Back</a></p></body></html>"


def run() -> None:
    import uvicorn

    settings = Settings.from_env()
    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    run()
