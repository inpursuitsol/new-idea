# Nifty × Stock Pair Trader — Edge Playbook

Simple pair-trading toolkit for Indian markets with **backtest-based defaults**.

## Files

| File | Purpose |
|------|---------|
| `tradingview/Nifty_Stock_Pair_Trader.pine` | **Main indicator + live trade coach dashboard** |
| `tradingview/Nifty_Stock_Pair_Strategy.pine` | Optional TV strategy shell |
| `scans/scan_nifty_pairs.py` | Daily stock scanner (same rules) |

## Edge playbook rules (built-in defaults)

**Enter LONG PAIR only when ALL are PASS:**
- Z ≤ **−2.0**
- |Correlation| ≥ **0.80**
- Half-life ≤ **8** bars

**Exit:**
- Take profit: Z ≥ **−0.5**
- Stop: Z ≤ **−4.0**
- Time exit: **15** bars

**Skip shorts** by default (LONG-only mode).

## How you know what to do while in a trade

You don’t calculate anything by hand. Use the indicator dashboard on the stock chart:

1. Open the stock (e.g. `NSE:M&M`)
2. Add **Nifty Pair Pro** (Pair Symbol = `NSE:NIFTY`)
3. Read the **LIVE TRADE COACH** table every day:

| Dashboard row | Meaning |
|---------------|---------|
| **TRADE STATUS** | Exact instruction: ENTER / HOLD / TAKE PROFIT / STOP OUT / TIME EXIT |
| **Z-Score (live)** | Current Z — compare to TP / Stop rows |
| **TP target Z** | When to book profit |
| **Stop Z** | When to cut the trade |
| **Bars Held / Max** | Time exit countdown (e.g. `7 / 15`) |
| **ENTRY CHECKS** | PASS/FAIL for Z, Corr, Half-Life before entry |
| **Hedge β** | Size Nifty ≈ β × stock notional |

Also set TradingView alerts: **Enter Long Pair**, **Take Profit**, **Stop Out**, **Time Exit**.

## Install indicator

1. Copy `tradingview/Nifty_Stock_Pair_Trader.pine`
2. TradingView → Pine Editor → Paste → Save → Add to chart
3. Keep defaults (Edge Playbook group)

## Daily scanner (Chromebook Linux / any PC)

```bash
cd ~/new-idea
python3 scans/scan_nifty_pairs.py
```

Shows actionable LONG pairs and saves `scans/nifty_pair_scan_latest.csv`.

Then open that stock on TradingView and manage the trade with the dashboard.

## Disclaimer

Research / education only. Past backtests ≠ future results. Prefer stock + Nifty futures/ETF hedge over short-dated options for this playbook.
