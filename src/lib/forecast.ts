import { atr, macd, rsi, sma } from "./indicators";
import type { Bias, Bar, DayForecast, ForecastResponse, SignalDetail } from "./types";

function clamp(n: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, n));
}

function round(n: number, digits = 2): number {
  const p = 10 ** digits;
  return Math.round(n * p) / p;
}

function biasFromScore(score: number): Bias {
  if (score >= 0.18) return "UP";
  if (score <= -0.18) return "DOWN";
  return "FLAT";
}

function confidenceFromScore(score: number, agreement: number): number {
  const magnitude = Math.min(1, Math.abs(score) / 0.85);
  return Math.round(clamp(35 + magnitude * 45 + agreement * 20, 38, 92));
}

function outcomeFor(
  bias: Bias,
  actualChangePct: number | undefined,
): DayForecast["outcome"] {
  if (actualChangePct == null) return "PENDING";
  const abs = Math.abs(actualChangePct);
  if (bias === "FLAT") {
    if (abs <= 0.25) return "HIT";
    if (abs <= 0.55) return "PARTIAL";
    return "MISS";
  }
  const signed = bias === "UP" ? actualChangePct : -actualChangePct;
  if (signed > 0.12) return "HIT";
  if (signed >= -0.08) return "PARTIAL";
  return "MISS";
}

function buildSignals(bars: Bar[], idx: number): SignalDetail[] {
  const closes = bars.map((b) => b.close);
  const highs = bars.map((b) => b.high);
  const lows = bars.map((b) => b.low);

  const sma20 = sma(closes, 20);
  const sma50 = sma(closes, 50);
  const rsi14 = rsi(closes, 14);
  const { histogram } = macd(closes);
  const atr14 = atr(highs, lows, closes, 14);

  const close = closes[idx];
  const prev = closes[idx - 1];
  const s20 = sma20[idx];
  const s50 = sma50[idx];
  const r = rsi14[idx];
  const hist = histogram[idx];
  const a = atr14[idx];

  const signals: SignalDetail[] = [];

  if (s20 != null && s50 != null) {
    const spread = (s20 - s50) / close;
    const score = clamp(spread / 0.012, -1, 1);
    signals.push({
      id: "trend",
      label: "20/50 trend",
      value: s20 >= s50 ? "Uptrend structure" : "Downtrend structure",
      score,
    });
  }

  if (s20 != null) {
    const dist = (close - s20) / close;
    signals.push({
      id: "mean",
      label: "Price vs SMA20",
      value: `${dist >= 0 ? "+" : ""}${round(dist * 100, 2)}%`,
      score: clamp(dist / 0.015, -1, 1),
    });
  }

  if (r != null) {
    let score = 0;
    let value = `RSI ${round(r, 1)}`;
    if (r >= 55 && r <= 70) {
      score = 0.55;
      value += " · bullish momentum";
    } else if (r > 70) {
      score = -0.25;
      value += " · stretched high";
    } else if (r <= 45 && r >= 30) {
      score = -0.55;
      value += " · bearish momentum";
    } else if (r < 30) {
      score = 0.25;
      value += " · stretched low";
    } else {
      score = (r - 50) / 40;
      value += " · neutral";
    }
    signals.push({ id: "rsi", label: "RSI (14)", value, score: clamp(score, -1, 1) });
  }

  if (hist != null && a != null && a > 0) {
    const score = clamp(hist / (a * 0.35), -1, 1);
    signals.push({
      id: "macd",
      label: "MACD impulse",
      value: hist >= 0 ? "Positive histogram" : "Negative histogram",
      score,
    });
  }

  const roc5 = (close - closes[idx - 5]) / closes[idx - 5];
  signals.push({
    id: "roc",
    label: "5-day momentum",
    value: `${roc5 >= 0 ? "+" : ""}${round(roc5 * 100, 2)}%`,
    score: clamp(roc5 / 0.025, -1, 1),
  });

  const candle = (close - bars[idx].open) / bars[idx].open;
  const gap = (bars[idx].open - prev) / prev;
  const shortTerm = candle * 0.65 + gap * 0.35;
  signals.push({
    id: "flow",
    label: "Prior session flow",
    value: `${candle >= 0 ? "Green" : "Red"} day, gap ${gap >= 0 ? "+" : ""}${round(gap * 100, 2)}%`,
    score: clamp(shortTerm / 0.01, -1, 1),
  });

  return signals;
}

function forecastAt(bars: Bar[], signalIdx: number, targetDate: string): DayForecast {
  const signals = buildSignals(bars, signalIdx);
  const raw = signals.reduce((sum, s) => sum + s.score, 0) / signals.length;
  const score = clamp(raw, -1, 1);
  const bias = biasFromScore(score);

  const sameSide = signals.filter((s) => Math.sign(s.score) === Math.sign(score) || Math.abs(s.score) < 0.1);
  const agreement = sameSide.length / signals.length;
  const confidence = confidenceFromScore(score, agreement);

  const closes = bars.map((b) => b.close);
  const highs = bars.map((b) => b.high);
  const lows = bars.map((b) => b.low);
  const atr14 = atr(highs, lows, closes, 14);
  const vol = atr14[signalIdx] ?? closes[signalIdx] * 0.008;
  const asOfClose = closes[signalIdx];
  const expectedMovePct = round((vol / asOfClose) * 100 * (0.55 + confidence / 200), 2);

  return {
    date: targetDate,
    bias,
    confidence,
    score: round(score, 3),
    asOfClose: round(asOfClose, 2),
    expectedMovePct,
    support: round(asOfClose - vol, 2),
    resistance: round(asOfClose + vol, 2),
    signals,
  };
}

export function buildForecast(
  bars: Bar[],
  meta: {
    symbol: string;
    name: string;
    currency: string;
    timezone: string;
    lastPrice: number;
    previousClose: number;
    session: "PRE" | "OPEN" | "CLOSED";
  },
): ForecastResponse {
  const todayIst = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());

  const lastBar = bars[bars.length - 1];
  const historyStart = Math.max(55, bars.length - 45);
  const history: DayForecast[] = [];

  for (let i = historyStart; i < bars.length; i += 1) {
    // Forecast for day i uses information through day i-1
    const signalIdx = i - 1;
    if (signalIdx < 54) continue;
    const day = forecastAt(bars, signalIdx, bars[i].date);
    const actualChangePct = round(
      ((bars[i].close - bars[i].open) / bars[i].open) * 100,
      2,
    );
    day.actualClose = round(bars[i].close, 2);
    day.actualChangePct = actualChangePct;
    day.outcome = outcomeFor(day.bias, actualChangePct);
    history.push(day);
  }

  // Today's live call: if last bar is today, forecast from prior day; else from last close for next session
  let today: DayForecast;
  if (lastBar.date === todayIst) {
    today = forecastAt(bars, bars.length - 2, todayIst);
    const actualChangePct = round(((meta.lastPrice - lastBar.open) / lastBar.open) * 100, 2);
    today.actualClose = round(meta.lastPrice, 2);
    today.actualChangePct = actualChangePct;
    today.outcome = meta.session === "CLOSED" ? outcomeFor(today.bias, actualChangePct) : "PENDING";
  } else {
    today = forecastAt(bars, bars.length - 1, todayIst);
    today.outcome = "PENDING";
  }

  const evaluated = history.filter((h) => h.outcome && h.outcome !== "PENDING");
  const hits = evaluated.filter((h) => h.outcome === "HIT").length;
  const partials = evaluated.filter((h) => h.outcome === "PARTIAL").length;
  const misses = evaluated.filter((h) => h.outcome === "MISS").length;

  return {
    symbol: meta.symbol,
    name: meta.name,
    currency: meta.currency,
    timezone: meta.timezone,
    lastPrice: round(meta.lastPrice, 2),
    previousClose: round(meta.previousClose, 2),
    dayChangePct: round(((meta.lastPrice - meta.previousClose) / meta.previousClose) * 100, 2),
    session: meta.session,
    generatedAt: new Date().toISOString(),
    today,
    history: [...history].reverse(),
    accuracy: {
      evaluated: evaluated.length,
      hits,
      partials,
      misses,
      hitRate: evaluated.length
        ? round(((hits + partials * 0.5) / evaluated.length) * 100, 1)
        : 0,
    },
    disclaimer:
      "Educational market bias from technical indicators — not investment advice. Markets can gap and reverse without notice.",
  };
}
