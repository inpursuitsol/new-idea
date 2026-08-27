from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from tv_zerodha.config import Settings

_ACTIONS = {
    "BUY": "BUY",
    "LONG": "BUY",
    "B": "BUY",
    "SELL": "SELL",
    "SHORT": "SELL",
    "S": "SELL",
}

_ORDER_TYPES = {"MARKET", "LIMIT", "SL", "SL-M"}
_PRODUCTS = {"MIS", "CNC", "NRML"}

_TICKER_RE = re.compile(
    r"^(?:(?P<exchange>NSE|BSE|NFO|BFO|MCX):)?(?P<symbol>[A-Z0-9&._-]+)$",
    re.IGNORECASE,
)


class AlertError(ValueError):
    """TradingView payload cannot be turned into a Kite order."""


@dataclass(frozen=True)
class TradeIntent:
    action: str
    tradingsymbol: str
    exchange: str
    quantity: int
    product: str
    order_type: str
    price: float | None
    trigger_price: float | None
    indicator: str
    raw: dict[str, Any]


def parse_json_object(payload: Any) -> dict[str, Any]:
    return _as_mapping(payload)


def parse_alert(payload: Any, settings: Settings) -> TradeIntent:
    data = parse_json_object(payload)
    action = _action(data)
    exchange, symbol = _symbol(data, settings.default_exchange)
    quantity = _quantity(data, settings)
    product = str(data.get("product") or settings.default_product).upper()
    order_type = str(data.get("order_type") or data.get("ordertype") or settings.default_order_type).upper()
    if product not in _PRODUCTS:
        raise AlertError(f"unsupported product {product!r}")
    if order_type not in _ORDER_TYPES:
        raise AlertError(f"unsupported order_type {order_type!r}")
    if settings.allowed_symbols and symbol not in settings.allowed_symbols:
        raise AlertError(f"symbol {symbol!r} is not in TV_ALLOWED_SYMBOLS")
    if exchange not in settings.allowed_exchanges:
        raise AlertError(f"exchange {exchange!r} is not allowed")

    price = _optional_float(data, "price")
    trigger_price = _optional_float(data, "trigger_price")
    if order_type == "LIMIT" and (price is None or price <= 0):
        raise AlertError("LIMIT orders need a positive price")
    if order_type in {"SL", "SL-M"} and (trigger_price is None or trigger_price <= 0):
        raise AlertError("SL / SL-M orders need a positive trigger_price")

    indicator = str(
        data.get("indicator") or data.get("strategy") or data.get("comment") or "tradingview"
    ).strip()

    return TradeIntent(
        action=action,
        tradingsymbol=symbol,
        exchange=exchange,
        quantity=quantity,
        product=product,
        order_type=order_type,
        price=price,
        trigger_price=trigger_price,
        indicator=indicator,
        raw=dict(data),
    )


def _as_mapping(payload: Any) -> dict[str, Any]:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            raise AlertError("empty alert body")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AlertError("alert body is not valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise AlertError("alert body must be a JSON object")
    return {str(k).lower(): v for k, v in payload.items()}


def _action(data: Mapping[str, Any]) -> str:
    raw = data.get("action") or data.get("side") or data.get("transaction_type")
    if raw is None:
        raise AlertError("missing action (BUY or SELL)")
    key = str(raw).strip().upper()
    if key not in _ACTIONS:
        raise AlertError(f"unsupported action {raw!r}")
    return _ACTIONS[key]


def _symbol(data: Mapping[str, Any], default_exchange: str) -> tuple[str, str]:
    ticker = data.get("tradingsymbol") or data.get("symbol") or data.get("ticker")
    if ticker is None:
        raise AlertError("missing symbol / ticker")
    text = str(ticker).strip().upper().replace(" ", "")
    match = _TICKER_RE.match(text)
    if not match:
        raise AlertError(f"cannot parse ticker {ticker!r}")
    exchange = (data.get("exchange") or match.group("exchange") or default_exchange)
    return str(exchange).upper(), match.group("symbol").upper()


def _quantity(data: Mapping[str, Any], settings: Settings) -> int:
    raw = data.get("quantity") or data.get("qty") or settings.default_quantity
    try:
        qty = int(float(raw))
    except (TypeError, ValueError) as exc:
        raise AlertError(f"invalid quantity {raw!r}") from exc
    if qty <= 0:
        raise AlertError("quantity must be positive")
    if qty > settings.max_quantity:
        raise AlertError(f"quantity {qty} exceeds TV_MAX_QUANTITY={settings.max_quantity}")
    return qty


def _optional_float(data: Mapping[str, Any], key: str) -> float | None:
    if key not in data or data[key] in (None, "", "{{close}}"):
        return None
    try:
        value = float(data[key])
    except (TypeError, ValueError) as exc:
        raise AlertError(f"invalid {key} {data[key]!r}") from exc
    return value
