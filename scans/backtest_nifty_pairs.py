#!/usr/bin/env python3
"""
Backtest Nifty Pair Pro logic across NSE stocks.
Pair PnL (market-neutral residual):
  LONG PAIR  : +r_stock - beta * r_nifty
  SHORT PAIR : -r_stock + beta * r_nifty
Entry |Z|>=2, exit |Z|<=0.5, stop |Z|>=3.5, min |corr|>=0.70, lookback=60.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

LOOKBACK = 60
Z_ENTRY = 2.0
Z_EXIT = 0.5
Z_STOP = 3.5
MIN_CORR = 0.70
MAX_HOLD = 20  # safety exit (bars)
NIFTY = "^NSEI"
PERIOD = "5y"
INTERVAL = "1d"

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


@dataclass
class Trade:
    symbol: str
    side: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_z: float
    exit_z: float
    beta: float
    corr: float
    hold_bars: int
    pair_ret: float  # residual return over hold
    exit_reason: str


def rolling_ols_params(stock: np.ndarray, nifty: np.ndarray):
    """Return alpha, beta, corr, z for each bar using trailing LOOKBACK window.
    Values are NaN until enough history.
    """
    n = len(stock)
    alpha = np.full(n, np.nan)
    beta = np.full(n, np.nan)
    corr = np.full(n, np.nan)
    z = np.full(n, np.nan)

    for i in range(LOOKBACK - 1, n):
        y = stock[i - LOOKBACK + 1 : i + 1]
        x = nifty[i - LOOKBACK + 1 : i + 1]
        x_mean = x.mean()
        y_mean = y.mean()
        var_x = np.dot(x - x_mean, x - x_mean)
        if var_x < 1e-12:
            continue
        b = float(np.dot(x - x_mean, y - y_mean) / var_x)
        a = float(y_mean - b * x_mean)
        spread = y - (a + b * x)
        sig = spread.std(ddof=0)
        if sig < 1e-12:
            continue
        c = float(np.corrcoef(y, x)[0, 1])
        alpha[i] = a
        beta[i] = b
        corr[i] = c
        z[i] = (spread[-1] - spread.mean()) / sig
    return alpha, beta, corr, z


def backtest_symbol(sym: str, stock: pd.Series, nifty: pd.Series) -> list[Trade]:
    df = pd.concat([stock.rename("s"), nifty.rename("n")], axis=1).dropna()
    if len(df) < LOOKBACK + 30:
        return []

    s = df["s"].values.astype(float)
    n = df["n"].values.astype(float)
    dates = df.index
    alpha, beta, corr, z = rolling_ols_params(s, n)

    trades: list[Trade] = []
    pos = 0  # 1 long pair, -1 short pair
    entry_i = None
    entry_z = None
    entry_beta = None
    entry_corr = None
    entry_s = None
    entry_n = None

    # Signal on bar i close; PnL from i close -> exit close (same as TV process_orders_on_close)
    for i in range(LOOKBACK, len(df)):
        if np.isnan(z[i]) or np.isnan(beta[i]) or np.isnan(corr[i]):
            continue

        if pos == 0:
            if abs(corr[i]) < MIN_CORR:
                continue
            if z[i] <= -Z_ENTRY:
                pos = 1
                entry_i, entry_z, entry_beta, entry_corr = i, z[i], beta[i], corr[i]
                entry_s, entry_n = s[i], n[i]
            elif z[i] >= Z_ENTRY:
                pos = -1
                entry_i, entry_z, entry_beta, entry_corr = i, z[i], beta[i], corr[i]
                entry_s, entry_n = s[i], n[i]
            continue

        hold = i - entry_i
        reason = None
        if pos == 1:
            if z[i] >= -Z_EXIT:
                reason = "mean_revert"
            elif z[i] <= -Z_STOP:
                reason = "stop"
            elif hold >= MAX_HOLD:
                reason = "time"
        else:
            if z[i] <= Z_EXIT:
                reason = "mean_revert"
            elif z[i] >= Z_STOP:
                reason = "stop"
            elif hold >= MAX_HOLD:
                reason = "time"

        if reason is None:
            continue

        # Pair residual return using entry beta (hedge held fixed)
        r_s = s[i] / entry_s - 1.0
        r_n = n[i] / entry_n - 1.0
        if pos == 1:
            pair_ret = r_s - entry_beta * r_n
        else:
            pair_ret = -r_s + entry_beta * r_n

        trades.append(
            Trade(
                symbol=sym.replace(".NS", ""),
                side="LONG_PAIR" if pos == 1 else "SHORT_PAIR",
                entry_date=dates[entry_i],
                exit_date=dates[i],
                entry_z=float(entry_z),
                exit_z=float(z[i]),
                beta=float(entry_beta),
                corr=float(entry_corr),
                hold_bars=int(hold),
                pair_ret=float(pair_ret),
                exit_reason=reason,
            )
        )
        pos = 0
        entry_i = None

    return trades


def summarize(trades: list[Trade]) -> dict:
    if not trades:
        return {}
    rets = np.array([t.pair_ret for t in trades], dtype=float)
    wins = rets[rets > 0]
    losses = rets[rets <= 0]
    # "Accuracy" = win rate on closed pair trades
    win_rate = float((rets > 0).mean())
    # Directional accuracy of mean-reversion thesis: exited via mean_revert and profitable
    mr = [t for t in trades if t.exit_reason == "mean_revert"]
    mr_wr = float(np.mean([t.pair_ret > 0 for t in mr])) if mr else np.nan
    avg = float(rets.mean())
    med = float(np.median(rets))
    std = float(rets.std(ddof=1)) if len(rets) > 1 else np.nan
    # Profit factor
    gross_win = float(wins.sum()) if len(wins) else 0.0
    gross_loss = float(-losses.sum()) if len(losses) else 0.0
    pf = gross_win / gross_loss if gross_loss > 1e-12 else np.inf
    # Expectancy
    expectancy = avg
    # Simple equity compounding equal-weight per trade
    equity = np.cumprod(1.0 + rets)
    total_comp = float(equity[-1] - 1.0)
    max_dd = float(((equity / np.maximum.accumulate(equity)) - 1.0).min())
    avg_hold = float(np.mean([t.hold_bars for t in trades]))

    by_reason = {}
    for r in sorted({t.exit_reason for t in trades}):
        sub = [t.pair_ret for t in trades if t.exit_reason == r]
        by_reason[r] = {
            "n": len(sub),
            "win_rate": float(np.mean(np.array(sub) > 0)),
            "avg_ret": float(np.mean(sub)),
        }

    return {
        "n_trades": len(trades),
        "win_rate": win_rate,
        "mean_revert_win_rate": mr_wr,
        "avg_pair_ret": avg,
        "median_pair_ret": med,
        "std_pair_ret": std,
        "profit_factor": pf,
        "expectancy": expectancy,
        "compounded_all_trades": total_comp,
        "max_dd_trade_eq": max_dd,
        "avg_hold_bars": avg_hold,
        "by_reason": by_reason,
        "long_n": sum(1 for t in trades if t.side == "LONG_PAIR"),
        "short_n": sum(1 for t in trades if t.side == "SHORT_PAIR"),
        "long_wr": float(np.mean([t.pair_ret > 0 for t in trades if t.side == "LONG_PAIR"])) if any(t.side == "LONG_PAIR" for t in trades) else np.nan,
        "short_wr": float(np.mean([t.pair_ret > 0 for t in trades if t.side == "SHORT_PAIR"])) if any(t.side == "SHORT_PAIR" for t in trades) else np.nan,
    }


def main():
    print(f"Backtesting pair logic | lookback={LOOKBACK} entry={Z_ENTRY} exit={Z_EXIT} stop={Z_STOP} min_corr={MIN_CORR}")
    print(f"Universe={len(UNIVERSE)} stocks vs {NIFTY} | period={PERIOD} {INTERVAL}\n")

    tickers = [NIFTY] + UNIVERSE
    data = yf.download(tickers, period=PERIOD, interval=INTERVAL, auto_adjust=True, progress=False, threads=True)
    closes = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]]

    if NIFTY not in closes.columns:
        raise SystemExit("Nifty download failed")

    nifty = closes[NIFTY].dropna()
    all_trades: list[Trade] = []
    per_symbol = []

    for sym in UNIVERSE:
        if sym not in closes.columns:
            continue
        stock = closes[sym].dropna()
        tr = backtest_symbol(sym, stock, nifty)
        all_trades.extend(tr)
        if tr:
            rets = np.array([t.pair_ret for t in tr])
            per_symbol.append({
                "symbol": sym.replace(".NS", ""),
                "trades": len(tr),
                "win_rate": float((rets > 0).mean()),
                "avg_ret": float(rets.mean()),
                "total_ret_sum": float(rets.sum()),
            })

    summary = summarize(all_trades)
    trades_df = pd.DataFrame([t.__dict__ for t in all_trades])
    sym_df = pd.DataFrame(per_symbol).sort_values("total_ret_sum", ascending=False) if per_symbol else pd.DataFrame()

    out_dir = "/workspace/scans"
    trades_df.to_csv(f"{out_dir}/pair_backtest_trades.csv", index=False)
    sym_df.to_csv(f"{out_dir}/pair_backtest_by_symbol.csv", index=False)

    # Yearly breakdown
    if not trades_df.empty:
        trades_df["year"] = pd.to_datetime(trades_df["entry_date"]).dt.year
        yearly = trades_df.groupby("year").agg(
            trades=("pair_ret", "count"),
            win_rate=("pair_ret", lambda x: float((x > 0).mean())),
            avg_ret=("pair_ret", "mean"),
            sum_ret=("pair_ret", "sum"),
        )
    else:
        yearly = pd.DataFrame()

    print("=" * 72)
    print("OVERALL RESULTS (stock−β·Nifty residual PnL, costs NOT included)")
    print("=" * 72)
    if not summary:
        print("No trades generated.")
        return

    def pct(x):
        return f"{100 * x:.1f}%" if x is not None and np.isfinite(x) else "n/a"

    print(f"Closed trades          : {summary['n_trades']}  (LONG {summary['long_n']} / SHORT {summary['short_n']})")
    print(f"Win rate (accuracy)    : {pct(summary['win_rate'])}")
    print(f"Win rate if mean-revert exit: {pct(summary['mean_revert_win_rate'])}")
    print(f"LONG win rate          : {pct(summary['long_wr'])}")
    print(f"SHORT win rate         : {pct(summary['short_wr'])}")
    print(f"Avg pair return/trade  : {pct(summary['avg_pair_ret'])}")
    print(f"Median pair return     : {pct(summary['median_pair_ret'])}")
    print(f"Profit factor          : {summary['profit_factor']:.2f}")
    print(f"Avg holding period     : {summary['avg_hold_bars']:.1f} trading days")
    print(f"Max DD (trade equity)  : {pct(summary['max_dd_trade_eq'])}")
    print(f"Sum of trade returns*  : {pct(float(trades_df['pair_ret'].sum()))}")
    print("  *sum is not account CAGR; equal-risk sequential compound shown below")
    print(f"Compounded (seq trades): {pct(summary['compounded_all_trades'])}")
    print()
    print("Exit reason breakdown:")
    for reason, info in summary["by_reason"].items():
        print(f"  {reason:12s} n={info['n']:4d}  win={pct(info['win_rate'])}  avg={pct(info['avg_ret'])}")

    print()
    print("=" * 72)
    print("YEARLY")
    print("=" * 72)
    if not yearly.empty:
        print(yearly.to_string(float_format=lambda v: f"{v:.4f}" if isinstance(v, float) else str(v)))

    print()
    print("=" * 72)
    print("TOP 10 SYMBOLS BY SUM OF PAIR RETURNS")
    print("=" * 72)
    if not sym_df.empty:
        top = sym_df.head(10).copy()
        top["win_rate"] = top["win_rate"].map(lambda v: f"{100*v:.0f}%")
        top["avg_ret"] = top["avg_ret"].map(lambda v: f"{100*v:.2f}%")
        top["total_ret_sum"] = top["total_ret_sum"].map(lambda v: f"{100*v:.1f}%")
        print(top.to_string(index=False))

    print()
    print("=" * 72)
    print("BOTTOM 10 SYMBOLS")
    print("=" * 72)
    if not sym_df.empty:
        bot = sym_df.tail(10).copy()
        bot["win_rate"] = bot["win_rate"].map(lambda v: f"{100*v:.0f}%")
        bot["avg_ret"] = bot["avg_ret"].map(lambda v: f"{100*v:.2f}%")
        bot["total_ret_sum"] = bot["total_ret_sum"].map(lambda v: f"{100*v:.1f}%")
        print(bot.to_string(index=False))

    print()
    print(f"Saved: {out_dir}/pair_backtest_trades.csv")
    print(f"Saved: {out_dir}/pair_backtest_by_symbol.csv")
    print()
    print("Notes:")
    print("- Accuracy here = % of closed pair trades with positive residual PnL.")
    print("- Does NOT include brokerage, slippage, STT, or borrow costs.")
    print("- Options (buying PE) will usually underperform this residual backtest due to theta/IV.")
    print("- Past win rate ≠ future guarantee.")


if __name__ == "__main__":
    main()
