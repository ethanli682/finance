"use client";

import { AreaSeries, ColorType, createChart, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";

import { fetchJson } from "@/lib/client-api";
import { formatPrice, formatSignedPercent } from "@/lib/format";
import type { PriceBar, PriceRange } from "@/lib/types";

const RANGES: { value: PriceRange; label: string }[] = [
  { value: "1m", label: "1M" },
  { value: "3m", label: "3M" },
  { value: "6m", label: "6M" },
  { value: "1y", label: "1Y" },
  { value: "5y", label: "5Y" },
  { value: "max", label: "Max" },
];

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function withAlpha(hex: string, alpha: number): string {
  const n = parseInt(hex.replace("#", ""), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}

function toTime(date: string): UTCTimestamp {
  return (Date.parse(`${date}T00:00:00Z`) / 1000) as UTCTimestamp;
}

type Props = {
  ticker: string;
  initialRange: PriceRange;
  initialBars: PriceBar[];
};

export function PriceChart({ ticker, initialRange, initialBars }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const [range, setRange] = useState<PriceRange>(initialRange);
  const [bars, setBars] = useState<PriceBar[]>(initialBars);
  const [cache, setCache] = useState<Partial<Record<PriceRange, PriceBar[]>>>({ [initialRange]: initialBars });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [themeVersion, setThemeVersion] = useState(0);

  const first = bars[0]?.close;
  const last = bars[bars.length - 1]?.close;
  const rising = first === undefined || last === undefined || last >= first;

  // Create the chart once; re-theme when the color scheme changes.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart = createChart(el, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        fontFamily: '"Public Sans Variable", system-ui, sans-serif',
        fontSize: 12,
      },
      grid: { vertLines: { visible: false } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
      handleScroll: false,
      handleScale: false,
    });
    const series = chart.addSeries(AreaSeries, {
      lineWidth: 2,
      priceLineVisible: false,
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
    });
    chartRef.current = chart;
    seriesRef.current = series;

    const applyTheme = () => {
      const ink = cssVar("--color-ink-muted");
      chart.applyOptions({
        layout: { textColor: ink },
        grid: { horzLines: { color: cssVar("--color-rule") } },
        crosshair: {
          vertLine: { color: cssVar("--color-rule-strong"), labelBackgroundColor: cssVar("--color-ink") },
          horzLine: { color: cssVar("--color-rule-strong"), labelBackgroundColor: cssVar("--color-ink") },
        },
      });
    };
    applyTheme();
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onSchemeChange = () => {
      applyTheme();
      setThemeVersion((v) => v + 1); // re-color the series too
    };
    media.addEventListener("change", onSchemeChange);
    // Re-measure text once the web font has loaded.
    document.fonts?.ready.then(() => chart.applyOptions({}));

    return () => {
      media.removeEventListener("change", onSchemeChange);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Push data and trend color into the series.
  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;
    const color = cssVar(rising ? "--color-up" : "--color-down");
    series.applyOptions({
      lineColor: color,
      topColor: withAlpha(color, 0.18),
      bottomColor: withAlpha(color, 0.01),
    });
    series.setData(bars.map((b) => ({ time: toTime(b.date), value: b.close })));
    chartRef.current?.timeScale().fitContent();
  }, [bars, rising, themeVersion]);

  async function selectRange(next: PriceRange) {
    if (next === range) return;
    setRange(next);
    setError(null);
    const cached = cache[next];
    if (cached) {
      setBars(cached);
      return;
    }
    setLoading(true);
    try {
      const data = await fetchJson<PriceBar[]>(`/api/companies/${encodeURIComponent(ticker)}/prices?range=${next}`);
      setCache((c) => ({ ...c, [next]: data }));
      setBars(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const change = first && last ? last / first - 1 : null;
  const rangeLabel = RANGES.find((r) => r.value === range)?.label;

  return (
    <section aria-label="Price history" className="mt-8">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div className="flex gap-1" role="group" aria-label="Chart range">
          {RANGES.map((r) => (
            <button
              key={r.value}
              type="button"
              aria-pressed={r.value === range}
              onClick={() => selectRange(r.value)}
              className={`rounded-sm px-2.5 py-1 text-sm font-semibold ${
                r.value === range ? "bg-ink text-paper" : "text-ink-muted hover:bg-tint hover:text-ink"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
        {change !== null && (
          <p className="tnum text-sm text-ink-muted" aria-live="polite">
            {rangeLabel === "Max" ? "All time" : `Past ${rangeLabel}`}:{" "}
            <span className={`font-semibold ${rising ? "text-up" : "text-down"}`}>{formatSignedPercent(change)}</span>
            <span className="ml-3">
              {formatPrice(first!)} to {formatPrice(last!)}
            </span>
          </p>
        )}
      </div>

      <div className={`fade-busy relative mt-3 h-56 sm:h-72 ${loading ? "opacity-50" : ""}`} aria-busy={loading}>
        <div ref={containerRef} className="absolute inset-0" />
        {bars.length === 0 && !loading && (
          <p className="absolute inset-0 flex items-center justify-center text-sm text-ink-muted">
            No price history is available for {ticker}.
          </p>
        )}
      </div>
      {error && <p className="mt-2 text-sm text-down">{error}</p>}
    </section>
  );
}
