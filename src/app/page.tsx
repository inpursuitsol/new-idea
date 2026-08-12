"use client";

import { useEffect, useState } from "react";
import styles from "./page.module.css";
import type { Bias, ForecastResponse } from "@/lib/types";

function formatNumber(n: number): string {
  return new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 2,
  }).format(n);
}

function formatDate(date: string): string {
  const d = new Date(`${date}T00:00:00+05:30`);
  return new Intl.DateTimeFormat("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(d);
}

function biasCopy(bias: Bias): string {
  if (bias === "UP") return "Bias points higher for the session.";
  if (bias === "DOWN") return "Bias points lower for the session.";
  return "Bias stays range-bound — wait for a cleaner push.";
}

function biasVars(bias: Bias): React.CSSProperties {
  if (bias === "UP") {
    return {
      ["--bias" as string]: "var(--up)",
      ["--bias-soft" as string]: "var(--up-soft)",
    };
  }
  if (bias === "DOWN") {
    return {
      ["--bias" as string]: "var(--down)",
      ["--bias-soft" as string]: "var(--down-soft)",
    };
  }
  return {
    ["--bias" as string]: "var(--flat)",
    ["--bias-soft" as string]: "var(--flat-soft)",
  };
}

export default function Home() {
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await fetch("/api/forecast", { cache: "no-store" });
        const json = await res.json();
        if (!res.ok) throw new Error(json.error || "Could not load forecast");
        if (!cancelled) setData(json as ForecastResponse);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load forecast");
        }
      }
    }

    load();
    const id = window.setInterval(load, 5 * 60 * 1000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  if (error) {
    return (
      <main className={styles.error}>
        <div>
          <div className={styles.loadingTitle}>NiftyHead</div>
          <p>{error}</p>
        </div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className={styles.loading}>
        <div>
          <div className={styles.loadingTitle}>Reading Nifty…</div>
          <div className={styles.shimmerLine} />
        </div>
      </main>
    );
  }

  const { today } = data;

  return (
    <main className={styles.page}>
      <header className={styles.topbar}>
        <div className={styles.brand}>
          Nifty<span>Head</span>
        </div>
        <div className={styles.meta}>
          <span className={styles.dot} aria-hidden />
          <span>
            {data.name} · {data.session === "OPEN" ? "Market open" : data.session === "PRE" ? "Pre-open" : "Closed"} · IST
          </span>
        </div>
      </header>

      <section className={styles.hero} aria-label="Today's Nifty direction">
        <div className={styles.heroCopy}>
          <h1>NiftyHead</h1>
          <p>
            Everyday direction for Nifty 50. Today&apos;s call:{" "}
            <strong>{today.bias}</strong> with {today.confidence}% conviction.{" "}
            {biasCopy(today.bias)}
          </p>
          <div className={styles.ctaRow}>
            <a className={styles.cta} href="#history">
              See everyday calls
            </a>
            <a className={styles.ghost} href="#signals">
              Why this bias
            </a>
          </div>
        </div>

        <div className={styles.biasPlane} style={biasVars(today.bias)}>
          <div className={styles.biasWord}>{today.bias}</div>
          <div className={styles.biasMeta}>
            <span>{formatDate(today.date)}</span>
            <span>
              Spot {formatNumber(data.lastPrice)} ({data.dayChangePct >= 0 ? "+" : ""}
              {data.dayChangePct}%)
            </span>
          </div>
        </div>
      </section>

      <section className={styles.section} aria-label="Session levels">
        <div className={styles.sectionHead}>
          <div>
            <h2>Today&apos;s map</h2>
            <p>
              Levels and expected swing sized from recent volatility. Built before the
              move, then scored against the day&apos;s open-to-close.
            </p>
          </div>
        </div>
        <div className={styles.stats}>
          <div className={styles.stat}>
            <strong>{today.confidence}%</strong>
            <span>Conviction</span>
          </div>
          <div className={styles.stat}>
            <strong>{formatNumber(today.support)}</strong>
            <span>Support</span>
          </div>
          <div className={styles.stat}>
            <strong>{formatNumber(today.resistance)}</strong>
            <span>Resistance</span>
          </div>
          <div className={styles.stat}>
            <strong>±{today.expectedMovePct}%</strong>
            <span>Expected swing</span>
          </div>
        </div>
      </section>

      <section className={styles.section} id="signals" aria-label="Signal breakdown">
        <div className={styles.sectionHead}>
          <div>
            <h2>Why Nifty heads {today.bias.toLowerCase()}</h2>
            <p>
              Six technical reads from the prior close — trend, mean distance, RSI, MACD,
              short momentum, and session flow.
            </p>
          </div>
          <div>
            Hit rate {data.accuracy.hitRate}% over {data.accuracy.evaluated} sessions
          </div>
        </div>
        <div className={styles.signals}>
          {today.signals.map((signal) => (
            <div key={signal.id} className={styles.signal}>
              <div className={styles.label}>{signal.label}</div>
              <div className={styles.value}>{signal.value}</div>
              <div className={styles.score}>
                Score {signal.score >= 0 ? "+" : ""}
                {signal.score.toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.section} id="history" aria-label="Everyday forecast history">
        <div className={styles.sectionHead}>
          <div>
            <h2>Everyday where it headed</h2>
            <p>
              Each morning bias versus that day&apos;s open-to-close. HIT means direction
              matched; PARTIAL means a soft/near miss.
            </p>
          </div>
        </div>

        <div className={styles.history}>
          <div className={`${styles.row} ${styles.rowHead}`}>
            <span>Day</span>
            <span>Call</span>
            <span>Actual</span>
            <span>Close</span>
            <span>Result</span>
          </div>
          {data.history.map((day, index) => (
            <div
              key={day.date}
              className={styles.row}
              style={{ animationDelay: `${Math.min(index, 12) * 0.04}s` }}
            >
              <span>{formatDate(day.date)}</span>
              <span>
                <span
                  className={`${styles.pill} ${
                    day.bias === "UP"
                      ? styles.UP
                      : day.bias === "DOWN"
                        ? styles.DOWN
                        : styles.FLAT
                  }`}
                >
                  {day.bias}
                </span>
              </span>
              <span>
                {day.actualChangePct == null
                  ? "—"
                  : `${day.actualChangePct >= 0 ? "+" : ""}${day.actualChangePct}%`}
              </span>
              <span>{day.actualClose ? formatNumber(day.actualClose) : "—"}</span>
              <span
                className={`${styles.outcome} ${
                  day.outcome === "HIT"
                    ? styles.HIT
                    : day.outcome === "PARTIAL"
                      ? styles.PARTIAL
                      : day.outcome === "MISS"
                        ? styles.MISS
                        : styles.PENDING
                }`}
              >
                {day.outcome}
              </span>
            </div>
          ))}
        </div>
      </section>

      <p className={styles.disclaimer}>{data.disclaimer}</p>
    </main>
  );
}
