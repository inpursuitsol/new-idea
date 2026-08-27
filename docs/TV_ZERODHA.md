# Technical notes (plain-language setup is in START_HERE.md)

Use [docs/START_HERE.md](START_HERE.md) unless you are changing the code.

- Default broker is **Upstox** (`trade.yaml`). Order APIs are free; brokerage still applies.
- Zerodha order APIs are also free; ₹500/month is only for live *data*, which this bridge does not use.
- Invite-only TradingView scripts: POST `/buy/{secret}` and `/sell/{secret}`. Stock and quantity come from `trade.yaml`.
- JSON webhook `/webhook/tradingview` still works if a script sends BUY/SELL JSON.
