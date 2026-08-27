from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from tv_zerodha.config import Settings
from tv_zerodha.kite_client import Broker, BrokerError, build_broker
from tv_zerodha.parse import AlertError, parse_alert


def create_app(settings: Settings | None = None, broker: Broker | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    broker = broker or build_broker(settings)
    app = FastAPI(title="TradingView → Zerodha", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "dry_run": settings.dry_run,
            "has_webhook_secret": bool(settings.webhook_secret),
        }

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
        try:
            intent = parse_alert(payload, settings)
            result = broker.place(intent)
        except AlertError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except BrokerError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return JSONResponse(
            {
                "ok": True,
                "dry_run": result.get("dry_run"),
                "order_id": result.get("order_id"),
                "order": result.get("order"),
                "indicator": intent.indicator,
            }
        )

    return app


def _decode_body(body: bytes) -> Any:
    from tv_zerodha.parse import parse_json_object

    return parse_json_object(body)


def _assert_secret(settings: Settings, payload: Any, header_secret: str | None) -> None:
    expected = settings.webhook_secret
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="TV_WEBHOOK_SECRET is not set; refusing alerts",
        )
    provided = header_secret
    if not provided and isinstance(payload, dict):
        provided = str(payload.get("secret") or payload.get("passphrase") or "")
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="invalid webhook secret")


def run() -> None:
    import uvicorn

    settings = Settings.from_env()
    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    if os.environ.get("TV_WEBHOOK_SECRET") is None:
        raise SystemExit("Set TV_WEBHOOK_SECRET before serving")
    run()
