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
_PRODUCTS = {"MIS", "CNC", "NRML", "I", "D", "M"}

_TICKER_RE = re.compile(
    r"^(?:(?P<exchange>NSE|BSE|NFO|BFO|MCX):)?(?P<symbol>[A-Z0-9&._-]+)$",
    re.IGNORECASE,
)
_LOOSE_ACTION = re.compile(r"\b(BUY|SELL|LONG|SHORT)\b", re.IGNORECASE)


class AlertError(ValueError):
    """Alert cannot be turned into a broker order."""


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


def parse_alert(
    payload: Any,
    settings: Settings,
    action_override: str | None = None,
) -> TradeIntent:
    data, leftover_text = _payload_dict(payload)
    action = _action(data, leftover_text, action_override)
    exchange, symbol = _symbol(data, settings)
    quantity = _quantity(data, settings)
    product = str(data.get("product") or settings.default_product).upper()
    if product == "I":
        product = "MIS"
    elif product == "D":
        product = "CNC"
    elif product == "M":
        product = "NRML"
    order_type = str(data.get("order_type") or data.get("ordertype") or settings.default_order_type).upper()
    if product not in {"MIS", "CNC", "NRML"}:
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


def _payload_dict(payload: Any) -> tuple[dict[str, Any], str]:
    if payload in (None, "", b"", {}, []):
        return {}, ""
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    if isinstance(payload, Mapping):
        return {str(k).lower(): v for k, v in payload.items()}, ""
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return {}, ""
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}, text
        if isinstance(parsed, Mapping):
            return {str(k).lower(): v for k, v in parsed.items()}, ""
        raise AlertError("alert body must be a JSON object")
    raise AlertError("alert body must be a JSON object")


def _as_mapping(payload: Any) -> dict[str, Any]:
    data, leftover = _payload_dict(payload)
    if leftover:
        raise AlertError("alert body is not valid JSON")
    if not data and payload not in (None, "", b"", {}, []):
        raise AlertError("empty alert body")
    if payload in (None, "", b"") or (isinstance(payload, str) and not payload.strip()):
        raise AlertError("empty alert body")
    return data


def _action(data: Mapping[str, Any], leftover_text: str, override: str | None) -> str:
    if override:
        key = str(override).strip().upper()
        if key not in _ACTIONS:
            raise AlertError(f"unsupported action {override!r}")
        return _ACTIONS[key]
    raw = data.get("action") or data.get("side") or data.get("transaction_type")
    if raw is not None:
        key = str(raw).strip().upper()
        if key not in _ACTIONS:
            raise AlertError(f"unsupported action {raw!r}")
        return _ACTIONS[key]
    match = _LOOSE_ACTION.search(leftover_text or "")
    if match:
        return _ACTIONS[match.group(1).upper()]
    raise AlertError("missing action (BUY or SELL)")


def _symbol(data: Mapping[str, Any], settings: Settings) -> tuple[str, str]:
    ticker = data.get("tradingsymbol") or data.get("symbol") or data.get("ticker") or settings.default_symbol
    if not ticker:
        raise AlertError("missing symbol — set stock in trade.yaml")
    text = str(ticker).strip().upper().replace(" ", "")
    match = _TICKER_RE.match(text)
    if not match:
        raise AlertError(f"cannot parse ticker {ticker!r}")
    exchange = data.get("exchange") or match.group("exchange") or settings.default_exchange
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
