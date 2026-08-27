from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from tv_zerodha.config import Settings
from tv_zerodha.parse import TradeIntent


class Broker(Protocol):
    def place(self, intent: TradeIntent) -> dict[str, Any]: ...


class BrokerError(RuntimeError):
    pass


@dataclass
class DryRunBroker:
    """Records the order that would have been sent to Kite. Default in tests and first run."""

    placed: list[dict[str, Any]]

    def __init__(self) -> None:
        self.placed = []

    def place(self, intent: TradeIntent) -> dict[str, Any]:
        payload = _order_kwargs(intent)
        order_id = f"DRYRUN-{len(self.placed) + 1}"
        result = {"order_id": order_id, "dry_run": True, "order": payload}
        self.placed.append(result)
        return result


class KiteBroker:
    def __init__(self, kite: Any, variety: str = "regular") -> None:
        self._kite = kite
        self._variety = variety

    def place(self, intent: TradeIntent) -> dict[str, Any]:
        kwargs = _order_kwargs(intent)
        try:
            order_id = self._kite.place_order(variety=self._variety, **kwargs)
        except Exception as exc:  # kiteconnect raises its own types
            raise BrokerError(str(exc)) from exc
        return {"order_id": str(order_id), "dry_run": False, "order": kwargs}


def build_broker(settings: Settings) -> Broker:
    if settings.dry_run:
        return DryRunBroker()
    try:
        from kiteconnect import KiteConnect
    except ImportError as exc:
        raise BrokerError("install kiteconnect (pip install -r requirements-trading.txt)") from exc
    if not settings.kite_api_key:
        raise BrokerError("KITE_API_KEY is required when TV_ZERODHA_DRY_RUN=false")
    token = settings.load_access_token()
    if not token:
        raise BrokerError("no Kite access token; run: python -m tv_zerodha.cli session <request_token>")
    kite = KiteConnect(api_key=settings.kite_api_key)
    kite.set_access_token(token)
    return KiteBroker(kite, variety=settings.variety)


def login_url(settings: Settings) -> str:
    from kiteconnect import KiteConnect

    if not settings.kite_api_key:
        raise BrokerError("KITE_API_KEY is required")
    return KiteConnect(api_key=settings.kite_api_key).login_url()


def exchange_request_token(settings: Settings, request_token: str) -> str:
    from kiteconnect import KiteConnect

    if not settings.kite_api_key or not settings.kite_api_secret:
        raise BrokerError("KITE_API_KEY and KITE_API_SECRET are required")
    kite = KiteConnect(api_key=settings.kite_api_key)
    data = kite.generate_session(request_token, api_secret=settings.kite_api_secret)
    token = str(data["access_token"])
    settings.save_access_token(token)
    return token


def _order_kwargs(intent: TradeIntent) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "exchange": intent.exchange,
        "tradingsymbol": intent.tradingsymbol,
        "transaction_type": intent.action,
        "quantity": intent.quantity,
        "product": intent.product,
        "order_type": intent.order_type,
    }
    if intent.price is not None:
        kwargs["price"] = intent.price
    if intent.trigger_price is not None:
        kwargs["trigger_price"] = intent.trigger_price
    kwargs["tag"] = _kite_tag(intent.indicator)
    return kwargs


def _kite_tag(indicator: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in indicator)[:20]
    return cleaned or "tv-alert"
