import type { MetricFormat, StatementRow } from "./types";

const MINUS = "\u2212";
const DASH = "\u2014";

export function formatCompactCurrency(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? MINUS : "";
  const units: [number, string][] = [
    [1e12, "T"],
    [1e9, "B"],
    [1e6, "M"],
    [1e3, "K"],
  ];
  for (const [size, suffix] of units) {
    if (abs >= size) {
      const scaled = abs / size;
      return `${sign}$${scaled.toFixed(scaled >= 100 ? 0 : scaled >= 10 ? 1 : 2)}${suffix}`;
    }
  }
  return `${sign}$${abs.toFixed(0)}`;
}

export function formatMetric(value: number | null, format: MetricFormat): string {
  if (value === null || !Number.isFinite(value)) return DASH;
  switch (format) {
    case "currency":
      return formatCompactCurrency(value);
    case "percent":
      return `${value < 0 ? MINUS : ""}${Math.abs(value * 100).toFixed(1)}%`;
    case "ratio":
      return value.toFixed(2);
    case "multiple":
      return `${value.toFixed(1)}\u00d7`;
  }
}

export function formatPrice(value: number): string {
  return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatSignedPrice(value: number): string {
  return `${value >= 0 ? "+" : MINUS}${formatPrice(Math.abs(value))}`;
}

export function formatSignedPercent(value: number): string {
  return `${value >= 0 ? "+" : MINUS}${Math.abs(value * 100).toFixed(2)}%`;
}

export function formatDate(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

// ---------------------------------------------------------------------------
// Statement tables: one scale per table, accounting-style negatives.
// ---------------------------------------------------------------------------

export type StatementScale = { divisor: number; word: "thousands" | "millions" };

export function pickScale(rows: StatementRow[]): StatementScale {
  let largest = 0;
  for (const row of rows) {
    if (row.unit !== "USD") continue;
    for (const v of row.values) if (v !== null) largest = Math.max(largest, Math.abs(v));
  }
  return largest >= 1e8 ? { divisor: 1e6, word: "millions" } : { divisor: 1e3, word: "thousands" };
}

export function formatStatementValue(value: number | null, unit: string, scale: StatementScale): string {
  if (value === null) return DASH;
  const perShare = unit === "USD/shares";
  const scaled = perShare ? value : value / scale.divisor;
  const digits = perShare ? 2 : Math.abs(scaled) < 10 && scaled !== 0 ? 1 : 0;
  const text = Math.abs(scaled).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return scaled < 0 ? `(${text})` : text;
}
