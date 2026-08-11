#!/usr/bin/env python3
"""
Daily NSE vs Nifty scanner — EDGE PLAYBOOK rules (matches TradingView indicator).

Enter LONG PAIR only when ALL pass:
  |Z| ≥ 2, |corr| ≥ 0.80, half-life ≤ 8 days

Exits (monitor on TradingView dashboard while in trade):
  TP |Z| ≤ 0.5 | Stop |Z| ≥ 4.0 | Time 15 bars
"""

from __future__ import annotations

import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

LOOKBACK = 60
Z_ENTRY = 2.0
Z_EXIT = 0.5
Z_STOP = 4.0
MIN_CORR = 0.80
MAX_HALFLIFE = 8.0
MAX_HOLD = 15
LONG_ONLY = True

NIFTY = "^NSEI"

UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "BHARTIARTL.NS", "ICICIBANK.NS",
    "INFY.NS", "SBIN.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS",
    "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "AXISBANK.NS",
    "TITAN.NS", "ULTRACEMCO.NS", "BAJAJFINSV.NS", "NTPC.NS", "ONGC.NS",
    "M&M.NS", "ADANIENT.NS", "POWERGRID.NS", "WIPRO.NS", "ADANIPORTS.NS",
    "COALINDIA.NS", "NESTLEIND.NS", "JSWSTEEL.NS", "ASIANPAINT.NS", "TATASTEEL.NS",
    "BAJAJ-AUTO.NS", "BEL.NS", "TECHM.NS", "HINDALCO.NS", "TRENT.NS",
    "INDUSINDBK.NS", "GRASIM.NS", "CIPLA.NS", "DRREDDY.NS", "SBILIFE.NS",
    "HDFCLIFE.NS", "EICHERMOT.NS", "KOTAKBANK.NS", "APOLLOHOSP.NS", "HEROMOTOCO.NS",
    "BPCL.NS", "BRITANNIA.NS", "TATACONSUM.NS",
]


def half_life(spread: np.ndarray) -> float:
    x = spread[:-1] - spread[:-1].mean()
    y = spread[1:] - spread[1:].mean()
    denom = np.dot(x, x)
    if denom < 1e-12:
        return np.nan
    phi = float(np.dot(x, y) / denom)
    if phi <= 0 or phi >= 1:
        return np.nan
    return float(-np.log(2.0) / np.log(phi))


def analyze_pair(stock: pd.Series, nifty: pd.Series, lookback: int = LOOKBACK) -> dict | None:
    df = pd.concat([stock.rename("stock"), nifty.rename("nifty")], axis=1).dropna()
    if len(df) < lookback + 5:
        return None

    window = df.iloc[-lookback:]
    y = window["stock"].values.astype(float)
    x = window["nifty"].values.astype(float)

    x_mean, y_mean = x.mean(), y.mean()
    var_x = np.dot(x - x_mean, x - x_mean)
    if var_x < 1e-12:
        return None
    beta = float(np.dot(x - x_mean, y - y_mean) / var_x)
    alpha = float(y_mean - beta * x_mean)

    spread_all = df["stock"] - (alpha + beta * df["nifty"])
    spread_w = spread_all.iloc[-lookback:]
    mu, sigma = float(spread_w.mean()), float(spread_w.std(ddof=0))
    if sigma < 1e-12:
        return None
    z = float((spread_w.iloc[-1] - mu) / sigma)
    corr = float(window["stock"].corr(window["nifty"]))
    hl = half_life(spread_w.values.astype(float))
    pct = float((spread_w <= spread_w.iloc[-1]).mean() * 100.0)

    corr_ok = abs(corr) >= MIN_CORR
    hl_ok = np.isfinite(hl) and 0 < hl <= MAX_HALFLIFE
    filters_ok = corr_ok and hl_ok
    z_long_ok = z <= -Z_ENTRY
    z_short_ok = z >= Z_ENTRY

    if z_long_ok and filters_ok:
        signal = "LONG PAIR"
        action = "Buy stock / Short Nifty"
    elif z_short_ok and filters_ok and not LONG_ONLY:
        signal = "SHORT PAIR"
        action = "Short stock / Buy Nifty"
    elif z_short_ok and filters_ok and LONG_ONLY:
        signal = "SKIP SHORT"
        action = "Short blocked (LONG-only playbook)"
    elif filters_ok and z <= -1.5:
        signal = "WATCH LONG"
        action = f"Approaching long entry (Z={z:+.2f})"
    elif filters_ok:
        signal = "FLAT"
        action = "Filters PASS — wait for Z ≤ -2"
    elif corr_ok and not hl_ok:
        signal = "HL FAIL"
        action = "Skip — half-life too slow"
    else:
        signal = "CORR FAIL"
        action = "Skip — correlation weak"

    return {
        "corr": corr,
        "beta": beta,
        "z": z,
        "half_life": hl,
        "spread_pct": pct,
        "corr_ok": corr_ok,
        "hl_ok": hl_ok,
        "filters_ok": filters_ok,
        "signal": signal,
        "action": action,
        "tp_z": -Z_EXIT if signal == "LONG PAIR" else Z_EXIT,
        "stop_z": -Z_STOP if signal == "LONG PAIR" else Z_STOP,
        "max_hold": MAX_HOLD,
        "last_price": float(df["stock"].iloc[-1]),
    }


def main() -> None:
    print("EDGE PLAYBOOK SCANNER — LONG PAIR only")
    print(f"Enter: Z≤-{Z_ENTRY}, |corr|≥{MIN_CORR}, half-life≤{MAX_HALFLIFE}d")
    print(f"Exit:  TP |Z|≤{Z_EXIT} | Stop |Z|≥{Z_STOP} | Time {MAX_HOLD} bars")
    print(f"Universe={len(UNIVERSE)} vs {NIFTY} | {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\n")

    tickers = [NIFTY] + UNIVERSE
    data = yf.download(tickers, period="1y", interval="1d", auto_adjust=True, progress=False, threads=True)
    closes = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]]
    if NIFTY not in closes.columns:
        raise SystemExit("Could not download Nifty (^NSEI).")

    nifty = closes[NIFTY].dropna()
    rows = []
    for sym in UNIVERSE:
        if sym not in closes.columns:
            continue
        res = analyze_pair(closes[sym].dropna(), nifty)
        if res:
            rows.append({"symbol": sym.replace(".NS", ""), **res})

    out = pd.DataFrame(rows)
    if out.empty:
        print("No results.")
        return

    order = {"LONG PAIR": 0, "WATCH LONG": 1, "FLAT": 2, "SKIP SHORT": 3, "HL FAIL": 4, "CORR FAIL": 5, "SHORT PAIR": 6}
    out["_o"] = out["signal"].map(lambda s: order.get(s, 9))
    out = out.sort_values(["_o", "z"])

    def fmt(df: pd.DataFrame) -> str:
        if df.empty:
            return "  (none)\n"
        cols = ["symbol", "signal", "z", "corr", "half_life", "beta", "action"]
        view = df[cols].copy()
        view["z"] = view["z"].map(lambda v: f"{v:+.2f}")
        view["corr"] = view["corr"].map(lambda v: f"{v:.3f}")
        view["beta"] = view["beta"].map(lambda v: f"{v:.4f}")
        view["half_life"] = view["half_life"].map(lambda v: "n/a" if not np.isfinite(v) else f"{v:.1f}d")
        return view.to_string(index=False) + "\n"

    long_now = out[out["signal"] == "LONG PAIR"]
    watch = out[out["signal"] == "WATCH LONG"]
    ready = out[(out["signal"] == "FLAT") & (out["filters_ok"])].copy()
    ready = ready.assign(hl_sort=lambda d: d["half_life"].fillna(999)).sort_values(["corr", "hl_sort"], ascending=[False, True]).head(12)

    print("=" * 88)
    print("ACTIONABLE LONG PAIR NOW (all filters PASS)")
    print("=" * 88)
    print(fmt(long_now))
    if not long_now.empty:
        print("While in these trades on TradingView, watch dashboard:")
        print(f"  TAKE PROFIT when Z ≥ -{Z_EXIT} | STOP when Z ≤ -{Z_STOP} | TIME EXIT at {MAX_HOLD} bars\n")

    print("=" * 88)
    print("WATCHLIST — approaching long entry")
    print("=" * 88)
    print(fmt(watch))

    print("=" * 88)
    print("FILTERS PASS — waiting for Z stretch (best candidates)")
    print("=" * 88)
    print(fmt(ready))

    # Save next to this script (works on Chromebook, PC, cloud, etc.)
    out_dir = Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "nifty_pair_scan_latest.csv"
    out.drop(columns=["_o"], errors="ignore").to_csv(out_path, index=False)
    print(f"Saved → {out_path}")
    print(f"Scanned {len(out)} symbols.")


if __name__ == "__main__":
    main()
