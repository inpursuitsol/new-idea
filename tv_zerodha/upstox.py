from __future__ import annotations

import gzip
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from tv_zerodha.config import Settings
from tv_zerodha.kite_client import BrokerError
from tv_zerodha.parse import TradeIntent

_TOKEN_URL = "https://api.upstox.com/v2/login/authorization/token"
_LOGIN_DIALOG = "https://api.upstox.com/v2/login/authorization/dialog"
_PLACE_ORDER_URL = "https://api-hft.upstox.com/v3/order/place"
_INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"

_SEGMENT = {
    "NSE": "NSE_EQ",
    "BSE": "BSE_EQ",
    "NFO": "NSE_FO",
    "BFO": "BSE_FO",
    "MCX": "MCX_FO",
}

_PRODUCT = {"MIS": "I", "CNC": "D", "NRML": "M"}


def login_url(settings: Settings) -> str:
    if not settings.upstox_api_key:
        raise BrokerError("Put upstox_api_key in trade.yaml")
    query = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": settings.upstox_api_key,
            "redirect_uri": settings.upstox_redirect_uri,
        }
    )
    return f"{_LOGIN_DIALOG}?{query}"


def exchange_auth_code(settings: Settings, code: str) -> str:
    if not settings.upstox_api_key or not settings.upstox_api_secret:
        raise BrokerError("Put upstox_api_key and upstox_api_secret in trade.yaml")
    body = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": settings.upstox_api_key,
            "client_secret": settings.upstox_api_secret,
            "redirect_uri": settings.upstox_redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode()
    req = urllib.request.Request(
        _TOKEN_URL,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise BrokerError(f"Upstox login failed: {detail}") from exc
    token = str((data.get("data") or data).get("access_token") or data.get("access_token") or "")
    if not token:
        raise BrokerError("Upstox login did not return an access_token")
    settings.save_access_token(token)
    return token


class UpstoxBroker:
    def __init__(
        self,
        access_token: str,
        instrument_key: str = "",
        lookup: Callable[[str, str], str] | None = None,
        post_order: Callable[[dict[str, Any], str], dict[str, Any]] | None = None,
    ) -> None:
        self._token = access_token
        self._instrument_key = instrument_key
        self._lookup = lookup or lookup_instrument_key
        self._post_order = post_order or _place_order_http

    def place(self, intent: TradeIntent) -> dict[str, Any]:
        key = self._instrument_key or self._lookup(intent.exchange, intent.tradingsymbol)
        payload = {
            "quantity": intent.quantity,
            "product": _PRODUCT.get(intent.product, "I"),
            "validity": "DAY",
            "price": 0 if intent.order_type == "MARKET" else (intent.price or 0),
            "tag": "tv-alert",
            "instrument_token": key,
            "order_type": intent.order_type if intent.order_type in {"MARKET", "LIMIT"} else "MARKET",
            "transaction_type": intent.action,
            "disclosed_quantity": 0,
            "trigger_price": intent.trigger_price or 0,
            "is_amo": False,
            "slice": False,
        }
        data = self._post_order(payload, self._token)
        order_id = _extract_order_id(data)
        return {"order_id": order_id, "dry_run": False, "order": payload, "broker": "upstox"}


def lookup_instrument_key(exchange: str, symbol: str, rows: list[dict[str, Any]] | None = None) -> str:
    symbol = symbol.upper()
    segment = _SEGMENT.get(exchange.upper(), "NSE_EQ")
    rows = rows if rows is not None else _load_nse_instruments()
    matches = []
    for row in rows:
        trading = str(row.get("trading_symbol") or row.get("tradingsymbol") or "").upper()
        key = str(row.get("instrument_key") or "")
        seg = str(row.get("segment") or row.get("exchange") or "")
        if trading != symbol or not key:
            continue
        if seg and seg != segment and not key.startswith(segment):
            continue
        matches.append(key)
    if not matches:
        raise BrokerError(f"Upstox does not know {exchange}:{symbol}. Use the broker symbol, e.g. RELIANCE.")
    return matches[0]


def _load_nse_instruments() -> list[dict[str, Any]]:
    req = urllib.request.Request(_INSTRUMENTS_URL, headers={"User-Agent": "tv-trade-bridge"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except urllib.error.URLError as exc:
        raise BrokerError("Could not download Upstox instrument list") from exc
    try:
        text = gzip.decompress(raw).decode()
    except OSError:
        text = raw.decode()
    data = json.loads(text)
    if not isinstance(data, list):
        raise BrokerError("Unexpected Upstox instrument list")
    return data


def _place_order_http(payload: dict[str, Any], token: str) -> dict[str, Any]:
    req = urllib.request.Request(
        _PLACE_ORDER_URL,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise BrokerError(f"Upstox order failed: {detail}") from exc


def _extract_order_id(data: dict[str, Any]) -> str:
    inner = data.get("data") if isinstance(data.get("data"), dict) else data
    if isinstance(inner, dict):
        if inner.get("order_id"):
            return str(inner["order_id"])
        ids = inner.get("order_ids")
        if isinstance(ids, list) and ids:
            return str(ids[0])
    return str(data)
