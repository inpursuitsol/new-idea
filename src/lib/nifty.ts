import type { Bar } from "./types";

type YahooChartResponse = {
  chart?: {
    result?: Array<{
      meta?: {
        currency?: string;
        symbol?: string;
        regularMarketPrice?: number;
        chartPreviousClose?: number;
        previousClose?: number;
        regularMarketTime?: number;
        timezone?: string;
        exchangeTimezoneName?: string;
        shortName?: string;
        longName?: string;
        currentTradingPeriod?: {
          regular?: { start: number; end: number };
        };
      };
      timestamp?: number[];
      indicators?: {
        quote?: Array<{
          open?: Array<number | null>;
          high?: Array<number | null>;
          low?: Array<number | null>;
          close?: Array<number | null>;
          volume?: Array<number | null>;
        }>;
      };
    }>;
    error?: { description?: string };
  };
};

function toIstDate(unixSeconds: number): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(unixSeconds * 1000));
}

export async function fetchNiftyBars(range = "1y"): Promise<{
  bars: Bar[];
  meta: {
    symbol: string;
    name: string;
    currency: string;
    timezone: string;
    lastPrice: number;
    previousClose: number;
    session: "PRE" | "OPEN" | "CLOSED";
  };
}> {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?range=${range}&interval=1d&includePrePost=false&events=div%2Csplit`;
  const res = await fetch(url, {
    headers: {
      "User-Agent":
        "Mozilla/5.0 (compatible; NiftyHead/1.0; +https://github.com/inpursuitsol/new-idea)",
      Accept: "application/json",
    },
    next: { revalidate: 300 },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch Nifty data (${res.status})`);
  }

  const json = (await res.json()) as YahooChartResponse;
  const result = json.chart?.result?.[0];
  if (!result?.timestamp?.length || !result.indicators?.quote?.[0]) {
    throw new Error(json.chart?.error?.description || "No Nifty chart data returned");
  }

  const quote = result.indicators.quote[0];
  const bars: Bar[] = [];

  for (let i = 0; i < result.timestamp.length; i += 1) {
    const open = quote.open?.[i];
    const high = quote.high?.[i];
    const low = quote.low?.[i];
    const close = quote.close?.[i];
    if (open == null || high == null || low == null || close == null) continue;

    bars.push({
      date: toIstDate(result.timestamp[i]),
      open,
      high,
      low,
      close,
      volume: quote.volume?.[i] ?? 0,
    });
  }

  if (bars.length < 60) {
    throw new Error("Not enough Nifty history to build a daily forecast");
  }

  const nowSec = Math.floor(Date.now() / 1000);
  const regular = result.meta?.currentTradingPeriod?.regular;
  let session: "PRE" | "OPEN" | "CLOSED" = "CLOSED";
  if (regular) {
    if (nowSec < regular.start) session = "PRE";
    else if (nowSec >= regular.start && nowSec <= regular.end) session = "OPEN";
    else session = "CLOSED";
  }

  const lastPrice = result.meta?.regularMarketPrice ?? bars[bars.length - 1].close;
  const previousClose =
    result.meta?.previousClose ??
    result.meta?.chartPreviousClose ??
    bars[bars.length - 2]?.close ??
    bars[bars.length - 1].close;

  return {
    bars,
    meta: {
      symbol: result.meta?.symbol ?? "^NSEI",
      name: result.meta?.longName || result.meta?.shortName || "NIFTY 50",
      currency: result.meta?.currency ?? "INR",
      timezone: result.meta?.exchangeTimezoneName || "Asia/Kolkata",
      lastPrice,
      previousClose,
      session,
    },
  };
}
