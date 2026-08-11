#!/usr/bin/env python3
"""
Daily Nifty × BankNifty pair scanner (matches NB Pair Coach indicator).

LONG BN PAIR  (BankNifty cheap): Buy BN CE + Nifty PE
SHORT BN PAIR (BankNifty rich):  Buy BN PE + Nifty CE
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
MIN_CORR = 0.75
MAX_HALFLIFE = 10.0
MAX_HOLD = 15

NIFTY = "^NSEI"
BANKNIFTY = "^NSEBANK"


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


def analyze(bn: pd.Series, nf: pd.Series) -> dict | None:
    df = pd.concat([bn.rename("bn"), nf.rename("nf")], axis=1).dropna()
    if len(df) < LOOKBACK + 5:
        return None

    # Log residual OLS (matches indicator default)
    window = df.iloc[-LOOKBACK:]
    y = np.log(window["bn"].values.astype(float))
    x = np.log(window["nf"].values.astype(float))
    x_mean, y_mean = x.mean(), y.mean()
    var_x = np.dot(x - x_mean, x - x_mean)
    if var_x < 1e-12:
        return None
    beta = float(np.dot(x - x_mean, y - y_mean) / var_x)
    alpha = float(y_mean - beta * x_mean)

    spread_all = np.log(df["bn"]) - (alpha + beta * np.log(df["nf"]))
    spread_w = spread_all.iloc[-LOOKBACK:]
    mu, sigma = float(spread_w.mean()), float(spread_w.std(ddof=0))
    if sigma < 1e-12:
        return None
    z = float((spread_w.iloc[-1] - mu) / sigma)
    corr = float(window["bn"].corr(window["nf"]))
    hl = half_life(spread_w.values.astype(float))

    corr_ok = abs(corr) >= MIN_CORR
    hl_ok = np.isfinite(hl) and 0 < hl <= MAX_HALFLIFE
    filters_ok = corr_ok and hl_ok

    if z <= -Z_ENTRY and filters_ok:
        signal = "LONG BN PAIR"
        options = "Buy 1L BankNifty CE + Buy 1L Nifty PE"
    elif z >= Z_ENTRY and filters_ok:
        signal = "SHORT BN PAIR"
        options = "Buy 1L BankNifty PE + Buy 1L Nifty CE"
    elif filters_ok and z <= -1.5:
        signal = "WATCH LONG"
        options = "Approaching BN-cheap entry"
    elif filters_ok and z >= 1.5:
        signal = "WATCH SHORT"
        options = "Approaching BN-rich entry"
    elif filters_ok:
        signal = "FLAT"
        options = "Filters PASS — wait for |Z| ≥ 2"
    elif not corr_ok:
        signal = "CORR FAIL"
        options = "Skip — correlation weak"
    else:
        signal = "HL FAIL"
        options = "Skip — half-life too slow"

    # Return beta for info (BN returns ~ beta * Nifty returns)
    rets = df.pct_change().dropna().iloc[-LOOKBACK:]
    ret_beta = float(np.cov(rets["bn"], rets["nf"])[0, 1] / np.var(rets["nf"])) if len(rets) > 5 else np.nan

    return {
        "signal": signal,
        "z": z,
        "corr": corr,
        "half_life": hl,
        "log_beta": beta,
        "return_beta": ret_beta,
        "corr_ok": corr_ok,
        "hl_ok": hl_ok,
        "filters_ok": filters_ok,
        "options_1L_1L": options,
        "tp_z": Z_EXIT,
        "stop_z": Z_STOP,
        "max_hold": MAX_HOLD,
        "bn_last": float(df["bn"].iloc[-1]),
        "nf_last": float(df["nf"].iloc[-1]),
    }


def main() -> None:
    print("NB PAIR COACH SCANNER — Nifty × BankNifty")
    print(f"Enter |Z|>={Z_ENTRY}, |corr|>={MIN_CORR}, half-life≤{MAX_HALFLIFE}")
    print(f"Exit TP |Z|≤{Z_EXIT} | Stop |Z|≥{Z_STOP} | Time {MAX_HOLD} bars")
    print(f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\n")

    data = yf.download([NIFTY, BANKNIFTY], period="2y", interval="1d", auto_adjust=True, progress=False)
    closes = data["Close"]
    if NIFTY not in closes.columns or BANKNIFTY not in closes.columns:
        raise SystemExit("Could not download Nifty / BankNifty")

    res = analyze(closes[BANKNIFTY].dropna(), closes[NIFTY].dropna())
    if not res:
        raise SystemExit("Not enough data")

    print("=" * 72)
    print(f"SIGNAL          : {res['signal']}")
    print(f"OPTIONS (1L+1L) : {res['options_1L_1L']}")
    print(f"Z-Score         : {res['z']:+.3f}")
    print(f"Correlation     : {res['corr']:.3f}  ({'PASS' if res['corr_ok'] else 'FAIL'})")
    print(f"Half-Life       : {res['half_life']:.1f}d  ({'PASS' if res['hl_ok'] else 'FAIL'})")
    print(f"Return β (BN~NF): {res['return_beta']:.3f}")
    print(f"BankNifty last  : {res['bn_last']:.2f}")
    print(f"Nifty last      : {res['nf_last']:.2f}")
    print("=" * 72)
    print("TradingView: open NSE:BANKNIFTY → add 'Index Pair Coach — Nifty×BankNifty'")
    print("Only trade when NEW ENTRY TODAY? = YES")

    out = Path(__file__).resolve().parent / "nifty_banknifty_scan_latest.csv"
    pd.DataFrame([res]).to_csv(out, index=False)
    print(f"Saved → {out}")


if __name__ == "__main__":
    main()
