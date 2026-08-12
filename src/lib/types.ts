export type Bias = "UP" | "DOWN" | "FLAT";

export type Bar = {
  date: string; // YYYY-MM-DD in IST calendar
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type SignalDetail = {
  id: string;
  label: string;
  value: string;
  score: number; // -1 .. +1
};

export type DayForecast = {
  date: string;
  bias: Bias;
  confidence: number; // 0..100
  score: number;
  asOfClose: number;
  expectedMovePct: number;
  support: number;
  resistance: number;
  signals: SignalDetail[];
  actualClose?: number;
  actualChangePct?: number;
  outcome?: "HIT" | "MISS" | "PARTIAL" | "PENDING";
};

export type ForecastResponse = {
  symbol: string;
  name: string;
  currency: string;
  timezone: string;
  lastPrice: number;
  previousClose: number;
  dayChangePct: number;
  session: "PRE" | "OPEN" | "CLOSED";
  generatedAt: string;
  today: DayForecast;
  history: DayForecast[];
  accuracy: {
    evaluated: number;
    hits: number;
    partials: number;
    misses: number;
    hitRate: number;
  };
  disclaimer: string;
};
