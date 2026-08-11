#!/usr/bin/env python3
"""Scan NSE liquid stocks vs Nifty using the same pair logic as Nifty Pair Pro."""

from __future__ import annotations

import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# Defaults matching the Pine indicator
LOOKBACK = 60
Z_ENTRY = 2.0
Z_EXIT = 0.5
Z_STOP = 3.5
MIN_CORR = 0.70

NIFTY = "^NSEI"

# Nifty 50 + a few liquid extras (Yahoo Finance .NS tickers)
UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "BHARTIARTL.NS", "ICICIBANK.NS",
    "INFY.NS", "SBIN.NS", "LICI.NS", "ITC.NS", "HINDUNILVR.NS",
    "LT.NS", "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS",
    "AXISBANK.NS", "TITAN.NS", "ULTRACEMCO.NS", "BAJAJFINSV.NS", "NTPC.NS",
    "ONGC.NS", "M&M.NS", "ADANIENT.NS", "POWERGRID.NS", "WIPRO.NS",
    "ADANIPORTS.NS", "COALINDIA.NS", "TATAMOTORS.NS", "NESTLEIND.NS", "JSWSTEEL.NS",
    "ASIANPAINT.NS", "TATASTEEL.NS", "BAJAJ-AUTO.NS", "BEL.NS", "TECHM.NS",
    "HINDALCO.NS", "TRENT.NS", "INDUSINDBK.NS", "GRASIM.NS", "CIPLA.NS",
    "DRREDDY.NS", "SBILIFE.NS", "HDFCLIFE.NS", "EICHERMOT.NS", "KOTAKBANK.NS",
    "APOLLOHOSP.NS", "HEROMOTOCO.NS", "BPCL.NS", "BRITANNIA.NS", "TATACONSUM.NS",
]


def half_life(spread: np.ndarray) -> float:
    """Ornstein-Uhlenbeck / AR(1) half-life in bars."""
    x = spread[:-1]
    y = spread[1:]
    x = x - x.mean()
    y = y - y.mean()
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

    # OLS: stock = alpha + beta * nifty
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

    # Percentile of latest spread in window
    pct = float((spread_w <= spread_w.iloc[-1]).mean() * 100.0)

    corr_ok = abs(corr) >= MIN_CORR
    pair_quality = corr_ok and np.isfinite(hl) and 0 < hl < lookback * 1.5

    if z <= -Z_ENTRY and corr_ok:
        signal = "LONG PAIR"
        action = "Buy stock / Short Nifty"
    elif z >= Z_ENTRY and corr_ok:
        signal = "SHORT PAIR"
        action = "Short stock / Buy Nifty"
    elif corr_ok and abs(z) >= 1.5:
        signal = "WATCH"
        action = f"Approaching entry (|Z|={abs(z):.2f})"
    elif corr_ok:
        signal = "FLAT"
        action = "Wait for |Z| ≥ 2"
    else:
        signal = "WEAK"
        action = "Skip — correlation weak"

    return {
        "corr": corr,
        "beta": beta,
        "alpha": alpha,
        "z": z,
        "half_life": hl,
        "spread_pct": pct,
        "corr_ok": corr_ok,
        "pair_quality": pair_quality,
        "signal": signal,
        "action": action,
        "last_price": float(df["stock"].iloc[-1]),
        "bars": len(df),
    }


def main() -> None:
    print(f"Scanning {len(UNIVERSE)} NSE stocks vs Nifty ({NIFTY})")
    print(f"Lookback={LOOKBACK} bars | Entry |Z|>={Z_ENTRY} | Min |corr|>={MIN_CORR}")
    print(f"Data as of UTC {datetime.now(timezone.utc):%Y-%m-%d %H:%M}\n")

    tickers = [NIFTY] + UNIVERSE
    data = yf.download(
        tickers,
        period="1y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    if isinstance(data.columns, pd.MultiIndex):
        closes = data["Close"].copy()
    else:
        closes = data[["Close"]].copy()

    if NIFTY not in closes.columns:
        raise SystemExit("Could not download Nifty (^NSEI). Check network / Yahoo.")

    nifty = closes[NIFTY].dropna()
    rows = []

    for sym in UNIVERSE:
        if sym not in closes.columns:
            continue
        stock = closes[sym].dropna()
        res = analyze_pair(stock, nifty)
        if res is None:
            continue
        rows.append({"symbol": sym.replace(".NS", ""), **res})

    out = pd.DataFrame(rows)
    if out.empty:
        print("No results — data download may have failed.")
        return

    out = out.sort_values(["signal", "z"], key=lambda s: s.map({
        "LONG PAIR": 0, "SHORT PAIR": 1, "WATCH": 2, "FLAT": 3, "WEAK": 4
    }) if s.name == "signal" else s)

    # Priority: actionable + watchlist
    actionable = out[out["signal"].isin(["LONG PAIR", "SHORT PAIR"])].copy()
    watch = out[out["signal"] == "WATCH"].copy()
    good_flat = out[(out["signal"] == "FLAT") & (out["pair_quality"])].copy()

    def fmt(df: pd.DataFrame) -> str:
        if df.empty:
            return "  (none)\n"
        cols = ["symbol", "signal", "z", "corr", "beta", "half_life", "spread_pct", "action"]
        view = df[cols].copy()
        view["z"] = view["z"].map(lambda v: f"{v:+.2f}")
        view["corr"] = view["corr"].map(lambda v: f"{v:.3f}")
        view["beta"] = view["beta"].map(lambda v: f"{v:.4f}")
        view["half_life"] = view["half_life"].map(lambda v: "n/a" if not np.isfinite(v) else f"{v:.1f}d")
        view["spread_pct"] = view["spread_pct"].map(lambda v: f"{v:.0f}%")
        return view.to_string(index=False) + "\n"

    print("=" * 88)
    print("ACTIONABLE NOW (|Z| ≥ 2 AND correlation OK)")
    print("=" * 88)
    print(fmt(actionable))

    print("=" * 88)
    print("WATCHLIST (correlation OK, |Z| ≥ 1.5)")
    print("=" * 88)
    print(fmt(watch))

    print("=" * 88)
    print("BEST PAIR CANDIDATES (quality OK, currently flat — wait for stretch)")
    print("=" * 88)
    # Rank by highest |corr| then lowest half-life
    good_flat = good_flat.assign(
        abs_corr=lambda d: d["corr"].abs(),
        hl_sort=lambda d: d["half_life"].fillna(999),
    ).sort_values(["abs_corr", "hl_sort"], ascending=[False, True]).head(15)
    print(fmt(good_flat))

    # Save full CSV
    out_path = "/workspace/scans/nifty_pair_scan_latest.csv"
    out.to_csv(out_path, index=False)
    print(f"Full scan saved → {out_path}")
    print(f"Scanned {len(out)} / {len(UNIVERSE)} symbols successfully.")


if __name__ == "__main__":
    main()
