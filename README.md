# Compound Pair System (money engine)

## What to run daily
```bash
cd ~/new-idea
source .venv/bin/activate
python scans/compound_pair_system.py
```

Full playbook: [`docs/COMPOUND_PAIR_SYSTEM.md`](docs/COMPOUND_PAIR_SYSTEM.md)

## What it is
- **10 active pairs** (Nifty–BankNifty, Nifty–FinNifty, banks, energy, IT, auto, pharma)
- **Options debit spreads** (not naked CE+PE)
- **Compounding**: profits raise package size
- Max **3** pairs open at once

## Research snapshot (₹4L start, ~5y proxy)
- Win rate ~**64%**
- Equity ~₹4.0L → ~₹5.2L  
- CAGR ~**6%**, max DD ~**4%**
- More trades / better stacking than single NB pair alone

Honest: this builds capital steadily; it is not a get-rich-quick options lottery.

## TradingView
- Index pair: `tradingview/Index_Pair_Coach_Nifty_BankNifty.pine` (**NB Pair Coach**, debit-spread text)
- Stock pairs: follow Python scanner recipes

## Older tools
- Stock×Nifty single-name scanner still in `scans/scan_nifty_pairs.py`
