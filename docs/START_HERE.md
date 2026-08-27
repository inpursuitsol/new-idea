# Trade when your invite-only TradingView script signals

You do **not** paste the script, and you do **not** write code.

The invite-only indicator stays on the chart. You add two alerts (Buy and Sell). Each alert pings this computer, and this computer places the order at **Upstox**.

This is not investment advice. Start with `practice: true` so no real order is sent.

## How hard is this, honestly?

| What you want | How hard | How reliable |
| --- | --- | --- |
| Phone buzzes, you tap Buy in the Upstox app | Easy | Best. You are still the one clicking. |
| Chart signal places the order by itself | Medium. One evening to set up, then a 1-minute login each morning | Good on market days if this computer stays on and you logged in that morning. Misses happen (Wi‑Fi, token expired, TradingView delay). |
| Zero computer, fully automatic | Not something this repo can do for you | Use a paid Indian “TradingView to broker” product if you want that |

Invite-only scripts **can** drive trades only if TradingView lets you pick a Buy and a Sell condition on that script. If the alert menu shows no Buy/Sell (only “Any alert() function call” with nothing behind it, or only a generic plot), ask the script author how they expect alerts to be set.

## Zerodha vs Upstox (money)

You asked: if Zerodha charges for APIs, use Upstox.

- **Upstox:** creating an API app is **free**. You still pay normal brokerage on the trade. This repo defaults to Upstox.
- **Zerodha:** placing orders through their API is **free**. They charge about **₹500/month** only if you also want live market *data* through the API. This bridge does not need that data (TradingView is already the chart), so Zerodha would not charge you extra for this use. Switch `broker: zerodha` in `trade.yaml` if you prefer to keep the same account.

Upstox Pro’s TradingView **charts** let you click Buy on the chart. That is not the same as auto-trading an invite-only script on tradingview.com.

## What you need

1. The invite-only script already on a TradingView chart.
2. A TradingView plan that allows **webhook** alerts (paid).
3. An Upstox account.
4. This computer left on during market hours.

## Setup (once)

1. Open `trade.yaml` and set:
   - `stock` — the same name as the chart (example: `RELIANCE`). Every alert will trade **this** stock.
   - `quantity` — how many shares (keep it tiny at first).
   - `secret` — any private word, like a password.
   - `upstox_api_key` / `upstox_api_secret` — from [upstox.com/developer/apps](https://upstox.com/developer/apps). While creating the app, set redirect URL to exactly `http://127.0.0.1:8080/upstox/callback`.
2. In a terminal, from this folder:

```bash
python3 -m pip install -r requirements.txt
python3 -m tv_zerodha.cli serve
```

3. Open [http://127.0.0.1:8080](http://127.0.0.1:8080) in your browser. You should see **Practice mode is ON**.
4. Click **Log in to Upstox** and finish login. Do this every morning before market (the login lasts one trading day).
5. TradingView cannot see `127.0.0.1`. In a **second** terminal, paste this (it gives you an https link):

```bash
npx --yes cloudflared tunnel --url http://127.0.0.1:8080
```

Copy the `https://....trycloudflare.com` address. Put that same address into `trade.yaml` as:

```yaml
public_url: https://xxxx.trycloudflare.com
```

Restart `serve`, refresh [http://127.0.0.1:8080](http://127.0.0.1:8080). The Buy and Sell links should now start with that https address. Keep **both** terminals open while you trade.

## Two alerts on your invite-only script

On the chart: **Alert** (clock icon).

**Alert 1 — Buy**

- Condition: your invite-only script → the Buy / long / bullish condition (whatever it is called).
- Options: Once per bar close (safest).
- Notifications: turn **Webhook URL** on. Paste the **Buy link**.
- Message: leave default. You do not need JSON.

**Alert 2 — Sell**

- Same, but the Sell / short / exit condition, and the **Sell link**.

Save both. Leave this computer running.

## When you are ready for a real order

1. Watch a practice alert hit the web page first (`Practice mode` will say an order was simulated).
2. In `trade.yaml` set `practice: false`.
3. Restart `serve`, log in to Upstox again, and keep quantity at 1 for the first live test during market hours.
4. Check the order in the Upstox app.

## If nothing happens

- Practice mode is still on — that is fine; you should still see a simulated order on the web page.
- You did not log in this morning.
- The invite-only script has no Buy/Sell condition in the alert dropdown.
- TradingView webhook needs a public https URL, not `127.0.0.1`.
- `stock` in `trade.yaml` does not match an Upstox symbol (`RELIANCE` not `NSE:RELIANCE`).
