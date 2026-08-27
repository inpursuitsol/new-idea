from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tv_zerodha.config import Settings
from tv_zerodha.kite_client import DryRunBroker, KiteBroker, _order_kwargs
from tv_zerodha.parse import AlertError, parse_alert
from tv_zerodha.webhook import create_app


def settings(**kwargs) -> Settings:
    base = dict(
        webhook_secret="s3cret",
        dry_run=True,
        default_exchange="NSE",
        default_product="MIS",
        default_order_type="MARKET",
        default_quantity=1,
        max_quantity=10,
        allowed_symbols=(),
        allowed_exchanges=("NSE", "BSE", "NFO"),
        variety="regular",
    )
    base.update(kwargs)
    return Settings(**base)


def test_parse_tradingview_placeholders_and_nse_ticker():
    intent = parse_alert(
        {
            "secret": "s3cret",
            "action": "buy",
            "ticker": "NSE:RELIANCE",
            "quantity": "2",
            "indicator": "EMA_CROSS",
        },
        settings(),
    )
    assert intent.action == "BUY"
    assert intent.exchange == "NSE"
    assert intent.tradingsymbol == "RELIANCE"
    assert intent.quantity == 2
    assert intent.order_type == "MARKET"
    assert intent.product == "MIS"
    assert intent.indicator == "EMA_CROSS"


def test_parse_rejects_quantity_cap_and_unknown_symbol():
    with pytest.raises(AlertError, match="TV_MAX_QUANTITY"):
        parse_alert({"action": "SELL", "symbol": "INFY", "quantity": 99}, settings())
    with pytest.raises(AlertError, match="TV_ALLOWED_SYMBOLS"):
        parse_alert(
            {"action": "BUY", "symbol": "YESBANK", "quantity": 1},
            settings(allowed_symbols=("INFY", "RELIANCE")),
        )


def test_limit_order_requires_price():
    with pytest.raises(AlertError, match="LIMIT"):
        parse_alert(
            {"action": "BUY", "symbol": "INFY", "order_type": "LIMIT", "quantity": 1},
            settings(),
        )


def test_dry_run_broker_does_not_call_kite():
    broker = DryRunBroker()
    intent = parse_alert(
        '{"action":"SELL","ticker":"INFY","quantity":1,"indicator":"RSI"}',
        settings(),
    )
    result = broker.place(intent)
    assert result["dry_run"] is True
    assert result["order_id"].startswith("DRYRUN-")
    assert result["order"]["transaction_type"] == "SELL"
    assert result["order"]["tradingsymbol"] == "INFY"


class FakeKite:
    def __init__(self) -> None:
        self.kwargs = None

    def place_order(self, **kwargs):
        self.kwargs = kwargs
        return 123456


def test_live_broker_maps_intent_to_kite_place_order():
    kite = FakeKite()
    broker = KiteBroker(kite, variety="regular")
    intent = parse_alert(
        {
            "action": "BUY",
            "symbol": "TCS",
            "quantity": 3,
            "product": "CNC",
            "order_type": "LIMIT",
            "price": 3500.5,
            "indicator": "EMA_CROSS",
        },
        settings(),
    )
    result = broker.place(intent)
    assert result == {
        "order_id": "123456",
        "dry_run": False,
        "broker": "zerodha",
        "order": _order_kwargs(intent),
    }
    assert kite.kwargs["variety"] == "regular"
    assert kite.kwargs["tradingsymbol"] == "TCS"
    assert kite.kwargs["transaction_type"] == "BUY"
    assert kite.kwargs["product"] == "CNC"
    assert kite.kwargs["order_type"] == "LIMIT"
    assert kite.kwargs["price"] == 3500.5
    assert kite.kwargs["tag"] == "EMA-CROSS"


def test_webhook_places_order_when_secret_matches():
    broker = DryRunBroker()
    client = TestClient(create_app(settings(), broker))
    response = client.post(
        "/webhook/tradingview",
        json={
            "secret": "s3cret",
            "action": "BUY",
            "ticker": "HDFCBANK",
            "quantity": 1,
            "indicator": "RSI",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["dry_run"] is True
    assert body["order"]["tradingsymbol"] == "HDFCBANK"
    assert body["indicator"] == "RSI"
    assert len(broker.placed) == 1


def test_webhook_rejects_bad_secret_and_missing_secret_config():
    broker = DryRunBroker()
    client = TestClient(create_app(settings(), broker))
    bad = client.post(
        "/webhook/tradingview",
        json={"secret": "nope", "action": "BUY", "ticker": "INFY", "quantity": 1},
    )
    assert bad.status_code == 401
    unset = TestClient(create_app(settings(webhook_secret=""), broker))
    refused = unset.post(
        "/webhook/tradingview",
        json={"action": "BUY", "ticker": "INFY", "quantity": 1},
    )
    assert refused.status_code == 503
    assert broker.placed == []


def test_webhook_accepts_header_secret():
    broker = DryRunBroker()
    client = TestClient(create_app(settings(), broker))
    response = client.post(
        "/webhook/tradingview",
        headers={"X-TV-Secret": "s3cret", "content-type": "application/json"},
        content=json.dumps({"action": "SELL", "ticker": "NSE:INFY", "quantity": 1}),
    )
    assert response.status_code == 200
    assert response.json()["order"]["transaction_type"] == "SELL"


def test_health_and_cli_preview(tmp_path: Path, capsys, monkeypatch):
    from tv_zerodha.cli import main

    client = TestClient(create_app(settings(), DryRunBroker()))
    assert client.get("/health").json()["ok"] is True

    alert = tmp_path / "alert.json"
    alert.write_text('{"action":"BUY","ticker":"INFY","quantity":1}', encoding="utf-8")
    monkeypatch.setenv("TV_ZERODHA_DRY_RUN", "true")
    monkeypatch.setenv("TV_WEBHOOK_SECRET", "s3cret")
    assert main(["preview", str(alert)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["tradingsymbol"] == "INFY"
    assert out["action"] == "BUY"


def test_invite_only_buy_link_uses_stock_from_settings():
    broker = DryRunBroker()
    client = TestClient(create_app(settings(default_symbol="RELIANCE"), broker))
    peek = client.get("/buy/s3cret")
    assert peek.status_code == 200
    assert peek.json()["hint"]
    assert broker.placed == []
    fired = client.post("/buy/s3cret")
    assert fired.status_code == 200
    body = fired.json()
    assert body["practice"] is True
    assert body["order"]["tradingsymbol"] == "RELIANCE"
    assert body["order"]["transaction_type"] == "BUY"
    sell = client.post("/sell/s3cret")
    assert sell.json()["order"]["transaction_type"] == "SELL"
    assert client.post("/buy/wrong").status_code == 401


def test_plain_text_alert_finds_buy_word():
    intent = parse_alert("My invite script says BUY now", settings(default_symbol="INFY"))
    assert intent.action == "BUY"
    assert intent.tradingsymbol == "INFY"


def test_upstox_broker_uses_instrument_key_and_intraday_product():
    from tv_zerodha.parse import parse_alert as parse
    from tv_zerodha.upstox import UpstoxBroker, lookup_instrument_key

    posted: dict = {}

    def post_order(payload, token):
        posted["payload"] = payload
        posted["token"] = token
        return {"data": {"order_ids": ["UP1"]}}

    broker = UpstoxBroker("tok", instrument_key="NSE_EQ|INE002A01018", post_order=post_order)
    intent = parse({"action": "BUY", "symbol": "RELIANCE", "quantity": 1}, settings())
    result = broker.place(intent)
    assert result["order_id"] == "UP1"
    assert result["broker"] == "upstox"
    assert posted["payload"]["instrument_token"] == "NSE_EQ|INE002A01018"
    assert posted["payload"]["product"] == "I"
    assert posted["payload"]["transaction_type"] == "BUY"
    key = lookup_instrument_key(
        "NSE",
        "RELIANCE",
        rows=[{"trading_symbol": "RELIANCE", "segment": "NSE_EQ", "instrument_key": "NSE_EQ|INE002A01018"}],
    )
    assert key.startswith("NSE_EQ|")


def test_home_page_explains_practice_mode():
    client = TestClient(create_app(settings(default_symbol="TCS", public_base_url="https://example.ngrok.app"), DryRunBroker()))
    page = client.get("/")
    assert page.status_code == 200
    assert "Practice mode is ON" in page.text
    assert "/buy/s3cret" in page.text
    assert "TCS" in page.text
