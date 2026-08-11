# Compound Pair System — bigger edge playbook

## What this is
A **multi-pair** mean-reversion book that:
1. Scans **10 active pairs** (indexes + stock–stock)
2. Trades with **options debit spreads** (not naked CE+PE)
3. **Reinvests profits** by raising package count as equity grows

This is larger than single Nifty–BankNifty because you get **more independent trades**.

## Daily command (Chromebook)
```bash
cd ~/new-idea
source .venv/bin/activate
git pull origin cursor/nifty-pair-trading-indicator-0959
python scans/compound_pair_system.py
```

Read **ACTIONABLE TODAY**. Take at most **3** pairs at once.

## Active pairs
- Nifty_BankNifty, Nifty_FinNifty  
- RELIANCE_BPCL, RELIANCE_ONGC  
- SBI_AXIS, HDFC_KOTAK, ICICI_SBI  
- MARUTI_MM, TCS_INFY, SUN_CIPLA  

## Entry / exit (same for every pair)
- Enter when `|Z| ≥ 2` and `|corr| ≥ 0.70`
- TP `|Z| ≤ 0.5` | Stop `|Z| ≥ 3.5` | Time **10** bars  
- Close **both** debit spreads together

## Debit spread recipe
**LONG_Y** (primary cheap):  
- Primary: bull **call** spread (buy ATM CE / sell higher OTM CE)  
- Hedge: bear **put** spread (buy ATM PE / sell lower OTM PE)

**SHORT_Y** (primary rich):  
- Primary: bear **put** spread  
- Hedge: bull **call** spread  

Expiry: **2–4 weeks**.

## Compounding (put money back)
Start ₹4L. Each month update equity and raise size:

| Equity | Tier | Packages (approx) |
|--------|------|-------------------|
| ₹4L | T1 | 1 |
| ₹5L | T1–T2 | 1–2 |
| ₹8L | T2–T3 | 2–3 |
| ₹12L+ | T3–T4 | 3–4+ |

Deploy ~**25%** of equity per open pair (max 3 pairs).

## Research backtest (proxy, not a promise)
Filtered multi-pair book, compounded from ₹4L:
- Win rate ~**60–65%**
- CAGR ~**6%** range (low drawdown research proxy)
- More trades than single NB pair

Live debit-spread results vary with IV/strikes.  
This will **not** usually print lakhs/month at ₹4L — it builds by **stacking pairs + compounding size**.

## TradingView
For Nifty–BankNifty leg, use **NB Pair Coach** on `BANKNIFTY` (now shows debit-spread text).  
For stock pairs, run the Python scanner daily (signals CSV).

## Discipline
1. Only trade scanner **ACTIONABLE** names  
2. Max 3 concurrent  
3. Journal every trade  
4. After profits, **increase packages** on next signals (compound)
