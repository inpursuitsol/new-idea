#!/usr/bin/env python3
"""
COMPOUND PAIR SYSTEM — bigger-edge multi-pair engine
====================================================
Goal: stack several high-quality mean-reversion pairs, size by capital,
reinvest profits (compound), express with options DEBIT SPREADS.

Pairs include:
  • Index: Nifty×BankNifty, Nifty×FinNifty
  • Stock–stock: banks, IT, energy, auto, pharma

Daily:
  python scans/compound_pair_system.py

Outputs:
  scans/compound_signals_latest.csv
  scans/compound_backtest_equity.csv
  prints today's actionable trades + suggested debit-spread recipes + lot sizing
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Tuned pair rules (walk-forward screened on NB; applied book-wide) ─────────
LOOKBACK = 60
Z_ENTRY = 2.0
Z_EXIT = 0.5
Z_STOP = 3.5
MIN_CORR = 0.70
MAX_HOLD = 10

# ── Capital / compounding (deploy real capital, reinvest profits) ─────────────
START_CAPITAL = 400_000          # ₹4L
ALLOC_PCT_PER_TRADE = 0.25       # deploy ~25% equity economics per open pair
CAPTURE = 0.75                   # debit-spread capture vs full residual (haircut)
MAX_CONCURRENT = 3               # max open pairs at once
# Legacy name used in size helper
RISK_PCT_PER_TRADE = ALLOC_PCT_PER_TRADE

OUT_DIR = Path(__file__).resolve().parent

# Full candidate list; live + backtest use ACTIVE_PAIRS (edge-filtered)
ALL_PAIRS: list[tuple[str, str, str, str]] = [
    ("Nifty_BankNifty", "^NSEBANK", "^NSEI", "index"),
    ("Nifty_FinNifty", "NIFTY_FIN_SERVICE.NS", "^NSEI", "index"),
    ("HDFC_ICICI", "HDFCBANK.NS", "ICICIBANK.NS", "stock"),
    ("ICICI_SBI", "ICICIBANK.NS", "SBIN.NS", "stock"),
    ("HDFC_KOTAK", "HDFCBANK.NS", "KOTAKBANK.NS", "stock"),
    ("SBI_AXIS", "SBIN.NS", "AXISBANK.NS", "stock"),
    ("TCS_INFY", "TCS.NS", "INFY.NS", "stock"),
    ("INFY_HCL", "INFY.NS", "HCLTECH.NS", "stock"),
    ("TCS_WIPRO", "TCS.NS", "WIPRO.NS", "stock"),
    ("RELIANCE_ONGC", "RELIANCE.NS", "ONGC.NS", "stock"),
    ("RELIANCE_BPCL", "RELIANCE.NS", "BPCL.NS", "stock"),
    ("MARUTI_MM", "MARUTI.NS", "M&M.NS", "stock"),
    ("SUN_CIPLA", "SUNPHARMA.NS", "CIPLA.NS", "stock"),
    ("SUN_DRREDDY", "SUNPHARMA.NS", "DRREDDY.NS", "stock"),
]

# Keep only historically stronger pairs (avg>0, PF>1.3, win≥50%, n≥12)
ACTIVE_PAIRS = [
    "Nifty_BankNifty",
    "Nifty_FinNifty",
    "RELIANCE_BPCL",
    "RELIANCE_ONGC",
    "SBI_AXIS",
    "HDFC_KOTAK",
    "ICICI_SBI",
    "MARUTI_MM",
    "TCS_INFY",
    "SUN_CIPLA",
]

PAIRS = [p for p in ALL_PAIRS if p[0] in ACTIVE_PAIRS]


@dataclass
class Trade:
    pair: str
    kind: str
    side: str  # LONG_Y or SHORT_Y
    entry: pd.Timestamp
    exit: pd.Timestamp
    hold: int
    reason: str
    z: float
    corr: float
    ret_1to1: float
    ret_beta: float


def _ols_log_z(y: np.ndarray, x: np.ndarray) -> tuple[float, float, float, float, float]:
    y = np.log(y)
    x = np.log(x)
    xm, ym = x.mean(), y.mean()
    vx = np.dot(x - xm, x - xm)
    if vx < 1e-12:
        return np.nan, np.nan, np.nan, np.nan, np.nan
    beta = float(np.dot(x - xm, y - ym) / vx)
    alpha = float(ym - beta * xm)
    spread = y - (alpha + beta * x)
    sig = float(spread.std(ddof=0))
    if sig < 1e-12:
        return np.nan, np.nan, np.nan, np.nan, np.nan
    z = float((spread[-1] - spread.mean()) / sig)
    return z, beta, alpha, float(spread.mean()), sig


def analyze_window(y: pd.Series, x: pd.Series) -> dict | None:
    df = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    if len(df) < LOOKBACK + 5:
        return None
    w = df.iloc[-LOOKBACK:]
    z, beta, alpha, _, _ = _ols_log_z(w["y"].values.astype(float), w["x"].values.astype(float))
    if not np.isfinite(z):
        return None
    corr = float(w["y"].corr(w["x"]))
    rets = w.pct_change().dropna()
    rb = float(np.cov(rets["y"], rets["x"])[0, 1] / np.var(rets["x"])) if len(rets) > 10 else np.nan
    corr_ok = abs(corr) >= MIN_CORR
    if z <= -Z_ENTRY and corr_ok:
        signal, side = "LONG_Y", "LONG_Y"
    elif z >= Z_ENTRY and corr_ok:
        signal, side = "SHORT_Y", "SHORT_Y"
    elif corr_ok and abs(z) >= 1.5:
        signal, side = "WATCH", None
    elif corr_ok:
        signal, side = "FLAT", None
    else:
        signal, side = "CORR_FAIL", None
    return {
        "z": z,
        "corr": corr,
        "log_beta": beta,
        "ret_beta": rb,
        "corr_ok": corr_ok,
        "signal": signal,
        "side": side,
        "y_last": float(df["y"].iloc[-1]),
        "x_last": float(df["x"].iloc[-1]),
    }


def debit_spread_recipe(pair: str, side: str, kind: str) -> str:
    """Human recipe for options debit spreads (1 package)."""
    y_name, x_name = pair.split("_", 1) if "_" in pair else (pair, "HEDGE")
    # prettier labels
    labels = {
        "Nifty_BankNifty": ("BankNifty", "Nifty"),
        "Nifty_FinNifty": ("FinNifty", "Nifty"),
        "HDFC_ICICI": ("HDFC Bank", "ICICI Bank"),
        "ICICI_SBI": ("ICICI Bank", "SBI"),
        "HDFC_KOTAK": ("HDFC Bank", "Kotak"),
        "SBI_AXIS": ("SBI", "Axis"),
        "TCS_INFY": ("TCS", "Infosys"),
        "INFY_HCL": ("Infosys", "HCL Tech"),
        "TCS_WIPRO": ("TCS", "Wipro"),
        "RELIANCE_ONGC": ("Reliance", "ONGC"),
        "RELIANCE_BPCL": ("Reliance", "BPCL"),
        "MARUTI_MM": ("Maruti", "M&M"),
        "SUN_CIPLA": ("Sun Pharma", "Cipla"),
        "SUN_DRREDDY": ("Sun Pharma", "Dr Reddy"),
    }
    y_lbl, x_lbl = labels.get(pair, (y_name, x_name))
    if side == "LONG_Y":
        return (
            f"DEBIT SPREADS: {y_lbl} bull CALL spread (buy ATM CE / sell OTM CE) + "
            f"{x_lbl} bear PUT spread (buy ATM PE / sell OTM PE). Expiry 2–4 weeks."
        )
    return (
        f"DEBIT SPREADS: {y_lbl} bear PUT spread (buy ATM PE / sell OTM PE) + "
        f"{x_lbl} bull CALL spread (buy ATM CE / sell OTM CE). Expiry 2–4 weeks."
    )


def backtest_pair(y: pd.Series, x: pd.Series, pair: str, kind: str) -> list[Trade]:
    df = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    trades: list[Trade] = []
    i = LOOKBACK
    while i < len(df) - 1:
        w = df.iloc[i - LOOKBACK + 1 : i + 1]
        z, beta, alpha, mu, sig = _ols_log_z(w["y"].values.astype(float), w["x"].values.astype(float))
        if not np.isfinite(z):
            i += 1
            continue
        corr = float(np.corrcoef(w["y"].values, w["x"].values)[0, 1])
        if abs(corr) < MIN_CORR or abs(z) < Z_ENTRY:
            i += 1
            continue
        side = "LONG_Y" if z <= -Z_ENTRY else "SHORT_Y"
        rets = w.pct_change().dropna()
        if len(rets) < 20:
            i += 1
            continue
        rb = float(np.cov(rets["y"], rets["x"])[0, 1] / np.var(rets["x"]))
        ey, ex = float(df["y"].iloc[i]), float(df["x"].iloc[i])
        entry_i = i
        exit_i = reason = None
        for j in range(i + 1, min(i + MAX_HOLD, len(df) - 1) + 1):
            w2 = df.iloc[j - LOOKBACK + 1 : j + 1]
            zj, _, _, _, _ = _ols_log_z(w2["y"].values.astype(float), w2["x"].values.astype(float))
            if not np.isfinite(zj):
                continue
            hold = j - entry_i
            if side == "LONG_Y" and zj >= -Z_EXIT:
                exit_i, reason = j, "tp"
                break
            if side == "SHORT_Y" and zj <= Z_EXIT:
                exit_i, reason = j, "tp"
                break
            if side == "LONG_Y" and zj <= -Z_STOP:
                exit_i, reason = j, "stop"
                break
            if side == "SHORT_Y" and zj >= Z_STOP:
                exit_i, reason = j, "stop"
                break
            if hold >= MAX_HOLD:
                exit_i, reason = j, "time"
                break
        if exit_i is None:
            i += 1
            continue
        ry = float(df["y"].iloc[exit_i] / ey - 1)
        rx = float(df["x"].iloc[exit_i] / ex - 1)
        if side == "LONG_Y":
            o2o, pret = ry - rx, ry - rb * rx
        else:
            o2o, pret = -ry + rx, -ry + rb * rx
        trades.append(
            Trade(pair, kind, side, df.index[entry_i], df.index[exit_i], exit_i - entry_i, reason, z, corr, o2o, pret)
        )
        i = exit_i + 1
    return trades


def compound_backtest(all_trades: list[Trade], start_capital: float = START_CAPITAL) -> pd.DataFrame:
    """
    Portfolio backtest with compounding:
    - Up to MAX_CONCURRENT pairs
    - Each trade allocates ALLOC_PCT_PER_TRADE of current equity
    - Apply residual return * CAPTURE (debit-spread proxy)
    - PnL added back to equity (reinvest / compound)
    """
    if not all_trades:
        return pd.DataFrame()
    T = sorted(all_trades, key=lambda t: (t.entry, t.pair))
    equity = start_capital
    open_pos: list[dict] = []
    rows = []
    peak = equity

    for tr in T:
        still_open = []
        for p in open_pos:
            if p["exit"] <= tr.entry:
                equity += p["pnl"]
                peak = max(peak, equity)
                rows.append(
                    {
                        "date": p["exit"],
                        "event": "close",
                        "pair": p["pair"],
                        "side": p["side"],
                        "ret": p["ret"],
                        "pnl": p["pnl"],
                        "equity": equity,
                        "dd": equity / peak - 1,
                    }
                )
            else:
                still_open.append(p)
        open_pos = still_open

        if len(open_pos) >= MAX_CONCURRENT:
            continue
        if any(p["pair"] == tr.pair for p in open_pos):
            continue

        alloc = equity * ALLOC_PCT_PER_TRADE
        ret = float(np.clip(tr.ret_1to1 * CAPTURE, -1.0, 1.0))
        pnl = alloc * ret
        open_pos.append(
            {
                "pair": tr.pair,
                "side": tr.side,
                "exit": tr.exit,
                "ret": ret,
                "pnl": pnl,
                "entry": tr.entry,
            }
        )
        rows.append(
            {
                "date": tr.entry,
                "event": "open",
                "pair": tr.pair,
                "side": tr.side,
                "ret": ret,
                "pnl": 0.0,
                "equity": equity,
                "dd": equity / peak - 1,
            }
        )

    for p in sorted(open_pos, key=lambda x: x["exit"]):
        equity += p["pnl"]
        peak = max(peak, equity)
        rows.append(
            {
                "date": p["exit"],
                "event": "close",
                "pair": p["pair"],
                "side": p["side"],
                "ret": p["ret"],
                "pnl": p["pnl"],
                "equity": equity,
                "dd": equity / peak - 1,
            }
        )

    return pd.DataFrame(rows)


def size_packages(equity: float, y_price: float = 0.0) -> dict:
    """Compounding size ladder from equity."""
    risk_budget = equity * ALLOC_PCT_PER_TRADE
    # rough combined debit-spread max-loss budget per package
    est_max_loss_per_package = 50_000  # combined max loss ballpark for both debit spreads
    packages = max(1, int(risk_budget // est_max_loss_per_package))
    packages = min(packages, 4)  # hard cap until equity is large
    if equity >= 1_200_000:
        packages = min(max(packages, 3), 6)
    # tier label for reinvestment
    if equity < 500_000:
        tier = "T1 starter (1 package focus)"
    elif equity < 800_000:
        tier = "T2 grow (2 packages)"
    elif equity < 1_200_000:
        tier = "T3 scale (3 packages)"
    else:
        tier = "T4 compound hard (4+ packages / more pairs)"
    return {
        "equity": equity,
        "risk_budget": risk_budget,
        "suggested_packages": packages,
        "tier": tier,
        "note": (
            f"{tier} | deploy ~{ALLOC_PCT_PER_TRADE*100:.0f}% equity (₹{risk_budget:,.0f}) "
            f"→ about {packages} debit-spread package(s). Reinvest profits → raise packages."
        ),
    }


def main(run_backtest: bool = True) -> None:
    print("=" * 78)
    print("COMPOUND PAIR SYSTEM — multi-pair + debit spreads + reinvest")
    print(f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")
    print(f"Start capital ₹{START_CAPITAL:,.0f} | alloc/trade {ALLOC_PCT_PER_TRADE*100:.0f}% | max {MAX_CONCURRENT} pairs | capture {CAPTURE:.0%}")
    print(f"Active pairs ({len(PAIRS)}): " + ", ".join(p[0] for p in PAIRS))
    print(f"Rules: Z≥{Z_ENTRY}, corr≥{MIN_CORR}, TP {Z_EXIT}, stop {Z_STOP}, hold {MAX_HOLD}")
    print("=" * 78)

    tickers = sorted({a for _, a, b, _ in PAIRS for a in (a, b)})
    data = yf.download(tickers, period="5y", interval="1d", auto_adjust=True, progress=False)["Close"]

    # ── Live scan ─────────────────────────────────────────────────────────────
    rows = []
    for name, ysym, xsym, kind in PAIRS:
        if ysym not in data.columns or xsym not in data.columns:
            continue
        res = analyze_window(data[ysym].dropna(), data[xsym].dropna())
        if not res:
            continue
        recipe = debit_spread_recipe(name, res["side"], kind) if res["side"] else "—"
        rows.append({"pair": name, "kind": kind, "ysym": ysym, "xsym": xsym, **res, "recipe": recipe})

    scan = pd.DataFrame(rows)
    if scan.empty:
        print("No scan results")
        return

    actionable = scan[scan["signal"].isin(["LONG_Y", "SHORT_Y"])].copy()
    watch = scan[scan["signal"] == "WATCH"].copy()

    # Rank actionable by |z| * corr quality
    if not actionable.empty:
        actionable["score"] = actionable["z"].abs() * actionable["corr"].abs()
        actionable = actionable.sort_values("score", ascending=False)

    print("\nACTIONABLE TODAY (take up to max concurrent):")
    if actionable.empty:
        print("  (none)")
    else:
        for _, r in actionable.iterrows():
            print(f"  {r['pair']:16s} {r['signal']:8s} Z={r['z']:+.2f} corr={r['corr']:.2f}")
            print(f"    → {r['recipe']}")
            sz = size_packages(START_CAPITAL, r["y_last"])
            print(f"    → {sz['note']}")

    print("\nWATCHLIST (|Z|≥1.5):")
    if watch.empty:
        print("  (none)")
    else:
        for _, r in watch.sort_values("z", key=lambda s: s.abs(), ascending=False).head(8).iterrows():
            print(f"  {r['pair']:16s} Z={r['z']:+.2f} corr={r['corr']:.2f}")

    # Compounding ladder always shown
    print("\nCOMPOUNDING LADDER (put profits back → raise size):")
    for eq in [400_000, 500_000, 800_000, 1_200_000, 2_000_000]:
        print(" ", size_packages(eq)["note"])
    scan_path = OUT_DIR / "compound_signals_latest.csv"
    scan.to_csv(scan_path, index=False)
    print(f"\nSaved signals → {scan_path}")

    if not run_backtest:
        return

    # ── Portfolio backtest ────────────────────────────────────────────────────
    print("\nRunning multi-pair compounded backtest (5y)...")
    all_tr: list[Trade] = []
    pair_stats = []
    for name, ysym, xsym, kind in PAIRS:
        if ysym not in data.columns or xsym not in data.columns:
            continue
        tr = backtest_pair(data[ysym].dropna(), data[xsym].dropna(), name, kind)
        all_tr.extend(tr)
        if tr:
            rets = np.array([t.ret_1to1 for t in tr])
            pair_stats.append(
                {
                    "pair": name,
                    "kind": kind,
                    "n": len(tr),
                    "win": float((rets > 0).mean()),
                    "avg": float(rets.mean()),
                    "pf": float(rets[rets > 0].sum() / max(-rets[rets <= 0].sum(), 1e-12)),
                }
            )

    eq = compound_backtest(all_tr, START_CAPITAL)
    eq_path = OUT_DIR / "compound_backtest_equity.csv"
    eq.to_csv(eq_path, index=False)
    ps = pd.DataFrame(pair_stats).sort_values("avg", ascending=False)
    ps.to_csv(OUT_DIR / "compound_pair_stats.csv", index=False)

    if eq.empty:
        print("No portfolio trades")
        return

    closes = eq[eq["event"] == "close"]
    start = START_CAPITAL
    end = float(closes["equity"].iloc[-1])
    years = (closes["date"].iloc[-1] - closes["date"].iloc[0]).days / 365.25
    cagr = (end / start) ** (1 / max(years, 0.1)) - 1 if end > 0 else -1
    max_dd = float(closes["dd"].min()) if len(closes) else 0
    rets = closes["ret"].values
    wins = rets[rets > 0].sum()
    losses = -rets[rets <= 0].sum()
    pf = wins / losses if losses > 1e-12 else 99

    print("\n" + "=" * 78)
    print("COMPOUND PORTFOLIO RESULT (proxy: 70% of 1:1 residual on risk capital)")
    print("=" * 78)
    print(f"Closed trades     : {len(closes)}")
    print(f"Win rate          : {100 * (rets > 0).mean():.1f}%")
    print(f"Avg ret on risk   : {100 * rets.mean():.2f}%")
    print(f"Profit factor     : {pf:.2f}")
    print(f"Start → End equity: ₹{start:,.0f} → ₹{end:,.0f}")
    print(f"Total return      : {100 * (end / start - 1):.1f}% over {years:.1f}y")
    print(f"CAGR (compounded) : {100 * cagr:.1f}%")
    print(f"Max DD (equity)   : {100 * max_dd:.1f}%")
    print(f"Avg concurrent cap: {MAX_CONCURRENT} pairs | alloc/trade {ALLOC_PCT_PER_TRADE*100:.0f}% | capture {CAPTURE:.0%}")
    print("\nCOMPOUND RULE: every month update your equity → use size_packages(equity) → raise debit-spread packages.")

    # yearly equity path
    closes = closes.copy()
    closes["year"] = pd.to_datetime(closes["date"]).dt.year
    # approximate year PnL from equity differences at year ends
    print("\nTop pairs by avg residual:")
    print(ps.head(10).to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"\nSaved equity curve → {eq_path}")
    print(
        "\nNOTE: RESEARCH PROXY for debit-spread economics (75% capture haircut)."
        "\nLive options PnL varies with IV, strikes, and expiry. Compound by raising packages as equity grows."
    )
    print("Playbook: docs/COMPOUND_PAIR_SYSTEM.md")


if __name__ == "__main__":
    main(run_backtest=True)
