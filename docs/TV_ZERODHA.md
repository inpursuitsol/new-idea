# TradingView indicator → Zerodha trade

TradingView cannot talk to Zerodha directly. This repo runs a small webhook: an **indicator alert** on TradingView POSTs JSON; the server maps that to a **Kite Connect** order.

```
TradingView chart (Pine indicator)
        │  alert on EMA cross / RSI threshold
        ▼
POST /webhook/tradingview   (this server, public HTTPS URL)
        │  secret check, symbol allow-list, qty cap
        ▼
Zerodha Kite Connect place_order
```

This is **not** investment advice. Orders can fill at a bad price, alerts can fire twice, and a leaked webhook URL can spend real money. Start with dry-run.

## What you need

1. **TradingView Essential or higher** (webhooks are a paid alert feature).
2. A **Kite Connect** app from [developers.kite.trade](https://developers.kite.trade/) (`api_key`, `api_secret`, redirect URL).
3. A **public HTTPS URL** for this server (Cloudflare Tunnel, ngrok, or a VPS). TradingView cannot hit `localhost`.
4. Python 3.11+ and `pip install -r requirements.txt -r requirements-trading.txt`.

Zerodha access tokens **die every trading day**. You log in again in the morning before alerts can place live orders.

## Configure

Copy `.env.example` and export the vars (or use a process manager).

| Variable | Purpose |
| --- | --- |
| `TV_WEBHOOK_SECRET` | Shared secret in the Pine alert JSON (or `X-TV-Secret` header). Required. |
| `TV_ZERODHA_DRY_RUN` | `true` (default) logs the order and does **not** call Kite. Set `false` only when you intend to trade. |
| `KITE_API_KEY` / `KITE_API_SECRET` | Kite Connect app credentials. |
| `KITE_ACCESS_TOKEN` | Optional. Otherwise the daily token is read from `.kite_access_token`. |
| `TV_ALLOWED_SYMBOLS` | Comma list, e.g. `INFY,RELIANCE,HDFCBANK`. Empty = any symbol (risky). |
| `TV_MAX_QUANTITY` | Hard cap (default 50). |
| `TV_DEFAULT_PRODUCT` | `MIS` (intraday), `CNC` (delivery), or `NRML`. |
| `TV_DEFAULT_EXCHANGE` | `NSE` unless the alert sends `exchange`. |

## Login to Kite (each trading day, live mode)

```bash
export PYTHONPATH=.
export KITE_API_KEY=...
export KITE_API_SECRET=...
python -m tv_zerodha.cli login-url
# Open the URL, log in, copy request_token from the redirect query string
python -m tv_zerodha.cli session REQUEST_TOKEN
```

That writes `.kite_access_token` (gitignored).

## Run the webhook

```bash
export TV_WEBHOOK_SECRET='a long random string'
export TV_ZERODHA_DRY_RUN=true
export PYTHONPATH=.
python -m tv_zerodha.cli serve
# listens on 0.0.0.0:8080  (TV_WEBHOOK_PORT to change)
```

Expose HTTPS to that port. Health check: `GET /health`.

## TradingView: attach the indicator and create the alert

1. Open a chart for an NSE cash name that exists on Kite (`INFY`, not `NSE:INFY` in the Kite field — the Pine scripts send `syminfo.ticker`).
2. Pine Editor → paste `tv_zerodha/pine/ema_crossover_alert.pine` (or `rsi_alert.pine`) → Add to chart.
3. In the indicator inputs, set **Webhook secret** to the same value as `TV_WEBHOOK_SECRET`.
4. Create Alert on that indicator:
   - Condition: the indicator’s `alert()` (any alert function call).
   - Notifications → **Webhook URL**: `https://YOUR-HOST/webhook/tradingview`
   - Message: leave default; the script already sends JSON via `alert()`.
5. Optional: also tick “Notify on app” so you see the same signal.

Example JSON if you write the alert message yourself instead of using the Pine `alert()` helper:

```json
{
  "secret": "same-as-TV_WEBHOOK_SECRET",
  "action": "{{strategy.order.action}}",
  "ticker": "{{ticker}}",
  "quantity": 1,
  "order_type": "MARKET",
  "product": "MIS",
  "indicator": "EMA_CROSS"
}
```

For a plain **indicator** (not a strategy), `{{strategy.order.action}}` is empty — use the Pine scripts, which send `"BUY"` / `"SELL"` explicitly.

`action` accepts `BUY` / `LONG` and `SELL` / `SHORT`.

## Preview without the server

```bash
echo '{"action":"BUY","ticker":"NSE:INFY","quantity":1,"indicator":"EMA_CROSS"}' \
  | python -m tv_zerodha.cli preview
```

## Go live

1. Keep `TV_ALLOWED_SYMBOLS` tight and `TV_MAX_QUANTITY` small.
2. Confirm dry-run webhook responses include `"dry_run": true` and a fake `DRYRUN-` order id.
3. `export TV_ZERODHA_DRY_RUN=false`, refresh the Kite session, restart `serve`.
4. Fire a **tiny** quantity on a liquid name during market hours and check the order on [kite.zerodha.com](https://kite.zerodha.com/).

## Limits

- Webhooks need a TradingView paid plan; free charts cannot POST to your server.
- `alert.freq_once_per_bar_close` still can double-fire if you duplicate alerts.
- Kite rejects unknown `tradingsymbol` values (use the Kite instrument dump, not Yahoo tickers).
- This path does not manage SL/target, position netting, or margin checks beyond Kite’s own errors.
