export function sma(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = Array(values.length).fill(null);
  if (period <= 0 || values.length < period) return out;

  let sum = 0;
  for (let i = 0; i < values.length; i += 1) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

export function ema(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = Array(values.length).fill(null);
  if (period <= 0 || values.length < period) return out;

  const k = 2 / (period + 1);
  let prev = 0;
  for (let i = 0; i < period; i += 1) prev += values[i];
  prev /= period;
  out[period - 1] = prev;

  for (let i = period; i < values.length; i += 1) {
    prev = values[i] * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

export function rsi(values: number[], period = 14): (number | null)[] {
  const out: (number | null)[] = Array(values.length).fill(null);
  if (values.length <= period) return out;

  let gains = 0;
  let losses = 0;
  for (let i = 1; i <= period; i += 1) {
    const diff = values[i] - values[i - 1];
    if (diff >= 0) gains += diff;
    else losses -= diff;
  }

  let avgGain = gains / period;
  let avgLoss = losses / period;
  out[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);

  for (let i = period + 1; i < values.length; i += 1) {
    const diff = values[i] - values[i - 1];
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? -diff : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }
  return out;
}

export function macd(
  values: number[],
  fast = 12,
  slow = 26,
  signalPeriod = 9,
): {
  macdLine: (number | null)[];
  signalLine: (number | null)[];
  histogram: (number | null)[];
} {
  const fastEma = ema(values, fast);
  const slowEma = ema(values, slow);
  const macdLine: (number | null)[] = values.map((_, i) => {
    if (fastEma[i] == null || slowEma[i] == null) return null;
    return (fastEma[i] as number) - (slowEma[i] as number);
  });

  const macdValues = macdLine.map((v) => v ?? 0);
  const firstValid = macdLine.findIndex((v) => v != null);
  const signalLine: (number | null)[] = Array(values.length).fill(null);
  const histogram: (number | null)[] = Array(values.length).fill(null);

  if (firstValid >= 0) {
    const sliced = macdValues.slice(firstValid);
    const signalSliced = ema(sliced, signalPeriod);
    for (let i = 0; i < signalSliced.length; i += 1) {
      const idx = firstValid + i;
      signalLine[idx] = signalSliced[i];
      if (macdLine[idx] != null && signalSliced[i] != null) {
        histogram[idx] = (macdLine[idx] as number) - (signalSliced[i] as number);
      }
    }
  }

  return { macdLine, signalLine, histogram };
}

export function atr(
  highs: number[],
  lows: number[],
  closes: number[],
  period = 14,
): (number | null)[] {
  const out: (number | null)[] = Array(closes.length).fill(null);
  if (closes.length <= period) return out;

  const trs: number[] = closes.map((close, i) => {
    if (i === 0) return highs[i] - lows[i];
    const prevClose = closes[i - 1];
    return Math.max(
      highs[i] - lows[i],
      Math.abs(highs[i] - prevClose),
      Math.abs(lows[i] - prevClose),
    );
  });

  let sum = 0;
  for (let i = 1; i <= period; i += 1) sum += trs[i];
  out[period] = sum / period;

  for (let i = period + 1; i < closes.length; i += 1) {
    out[i] = ((out[i - 1] as number) * (period - 1) + trs[i]) / period;
  }
  return out;
}
