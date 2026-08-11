# Index & Stock Pair Trading Toolkit (TradingView)

## Primary system (fits ₹4L / 1 lot options): Nifty × BankNifty

| File | Purpose |
|------|---------|
| **`tradingview/Index_Pair_Coach_Nifty_BankNifty.pine`** | **NB Pair Coach** indicator (use this) |
| **`scans/scan_nifty_banknifty.py`** | Daily Nifty×BankNifty scanner |

### Install indicator
1. Copy `tradingview/Index_Pair_Coach_Nifty_BankNifty.pine`
2. TradingView → open **`NSE:BANKNIFTY`** chart
3. Pine Editor → paste → Save → Add to chart
4. Hedge symbol = **`NSE:NIFTY`**

Indicator name on chart: **Index Pair Coach — Nifty×BankNifty** (`NB Pair Coach`)

### Options rules (1 lot + 1 lot)
| Signal | Trade |
|--------|--------|
| **LONG BN PAIR** | Buy 1L **BankNifty CE** + Buy 1L **Nifty PE** |
| **SHORT BN PAIR** | Buy 1L **BankNifty PE** + Buy 1L **Nifty CE** |

Only when dashboard **NEW ENTRY TODAY? = YES**.

### Exit
- Take profit `|Z| ≤ 0.5`
- Stop `|Z| ≥ 3.5`
- Time **10** bars  
Close **both** legs together.

### Tuned defaults (edge playbook)
- Entry `|Z| ≥ 2`, `|corr| ≥ 0.70`
- Half-life filter **OFF** (time stop does more work)
- Both LONG BN and SHORT BN allowed

Rough backtest (index 1:1 style, before costs): ~**60%+ win rate**, ~**2–4% residual / year** — modest. Long options usually earn less than that due to theta.

### Daily scan (Chromebook)
```bash
cd ~/new-idea
git pull origin cursor/nifty-pair-trading-indicator-0959
source .venv/bin/activate
python scans/scan_nifty_banknifty.py
```

---

## Secondary system: Stock × Nifty (larger capital / lot matching issues)

| File | Purpose |
|------|---------|
| `tradingview/Nifty_Stock_Pair_Trader.pine` | Stock vs Nifty coach |
| `scans/scan_nifty_pairs.py` | Stock universe scanner |

Use when capital can properly size the Nifty hedge.

## Disclaimer
Education/research only. Options lose value to theta. Past signals ≠ future profits.
