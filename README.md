# NiftyHead

Everyday direction for **Nifty 50** — a live daily bias (UP / DOWN / FLAT) built from technical signals on Yahoo Finance data.

## What you get

- Today's directional call with conviction, support/resistance, and expected swing
- Signal breakdown (trend, SMA distance, RSI, MACD, momentum, prior session flow)
- Recent everyday history scored HIT / PARTIAL / MISS against open-to-close

This is an educational market bias tool, not investment advice.

## Run locally

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Forecast API: `GET /api/forecast`.

## Stack

- Next.js App Router
- Live `^NSEI` daily bars from Yahoo Finance
- Rule-based technical forecast engine
