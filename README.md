# Nifty × Stock Pair Trader (TradingView)

Simple-to-use pair trading toolkit for Indian markets. Chart the **stock**, hedge against **Nifty** (or a sector index).

## Files

| File | Purpose |
|------|---------|
| `tradingview/Nifty_Stock_Pair_Trader.pine` | **Main indicator** — signals + dashboard |
| `tradingview/Nifty_Stock_Pair_Strategy.pine` | Optional backtest of Z-score timing on the stock leg |

## Install (60 seconds)

1. Open [TradingView Pine Editor](https://www.tradingview.com/pine-script-editor/)
2. Paste `Nifty_Stock_Pair_Trader.pine` → **Save** → **Add to chart**
3. Open a stock chart, e.g. `NSE:RELIANCE`, `NSE:TCS`, `NSE:INFY`, `NSE:HDFCBANK`
4. In indicator settings set **Pair Symbol** to `NSE:NIFTY`  
   (or `NSE:NIFTYBANK` / a sector index for sector pairs)

## How to read it (only this matters)

| Signal | Meaning | What to do |
|--------|---------|------------|
| **LONG PAIR** | Stock cheap vs Nifty | **Buy stock / Short Nifty** |
| **SHORT PAIR** | Stock rich vs Nifty | **Short stock / Buy Nifty** |
| **EXIT** | Spread mean-reverted (or stop) | Close both legs |
| Dashboard **WEAK** | Correlation too low | Skip — pair not co-moving |

Default thresholds (prop-desk style):

- Enter when **|Z| ≥ 2.0**
- Exit when **|Z| ≤ 0.5**
- Stop if **|Z| ≥ 3.5**
- Require **|Correlation| ≥ 0.70**

## What’s under the hood

Desk-style statistical arb, not a random oscillator mash-up:

1. **Engle–Granger residual** — rolling OLS hedge ratio β so spread ≈ Stock − α − β·Nifty  
2. **Kalman-filter β** (optional) — adaptive hedge when regimes shift  
3. **Z-score** — standardized spread for mean-reversion entries  
4. **Correlation filter** — block trades when the pair is not co-moving  
5. **Ornstein–Uhlenbeck half-life** — rough holding-period guide (bars)  
6. **Spread percentile + Bollinger** — extra context on residual extremes  
7. **Log residual / ratio modes** — scale-aware alternatives to raw price residual  

## Suggested defaults (India)

| Timeframe | Lookback | Notes |
|-----------|----------|--------|
| 15m / 30m | 60–120 | Intraday stock vs Nifty futures / index |
| 1H | 60–100 | Swing intraday |
| Daily | 60–120 | Positional pairs |

Start with **Spread Model = Residual (OLS)** and **Hedge Ratio = Rolling OLS**.  
Switch to **Kalman Filter** if β drifts a lot through earnings / regime changes.

## Position sizing (real pair)

Hedge shares / lots with β from the dashboard:

```text
Nifty notional ≈ β × Stock notional
```

Example: ₹5,00,000 stock long, β = 1.2 → short ≈ ₹6,00,000 Nifty (futures / ETF / index units).

## Alerts

Create alerts from the indicator:

- Long Pair  
- Short Pair  
- Exit Pair  
- Z Entry Level  

Prefer **Once Per Bar Close** (matches the “Alerts Need Bar Close” setting).

## Backtest note

The strategy script marks long/short on the **stock chart only**. TradingView cannot natively mark-to-market a two-leg Nifty hedge in one strategy. Use it to validate **signal timing**; compute true pair PnL in a spreadsheet if you need both legs.

## Disclaimer

For education and research. Pair trading carries divergence, borrow, and execution risk. Not investment advice.
