"use client";

import { useRef, useState } from "react";

import { fetchJson } from "@/lib/client-api";
import type { PeriodKind, Statement, StatementKind } from "@/lib/types";

import { LedgerTable, scaleNote } from "./LedgerTable";

const STATEMENTS: { value: StatementKind; label: string }[] = [
  { value: "income", label: "Income statement" },
  { value: "balance", label: "Balance sheet" },
  { value: "cashflow", label: "Cash flow" },
];

const PERIODS: { value: PeriodKind; label: string }[] = [
  { value: "annual", label: "Annual" },
  { value: "quarterly", label: "Quarterly" },
];

type Props = {
  ticker: string;
  initial: Statement;
};

export function Statements({ ticker, initial }: Props) {
  const [statement, setStatement] = useState<StatementKind>(initial.statement);
  const [period, setPeriod] = useState<PeriodKind>(initial.period);
  const [cache, setCache] = useState<Record<string, Statement>>({
    [`${initial.statement}:${initial.period}`]: initial,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const key = `${statement}:${period}`;
  // While a new table loads, keep showing the last one (dimmed) so the page doesn't jump.
  const [shown, setShown] = useState<Statement>(initial);
  const current = cache[key] ?? shown;

  async function load(nextStatement: StatementKind, nextPeriod: PeriodKind) {
    setStatement(nextStatement);
    setPeriod(nextPeriod);
    setError(null);
    const nextKey = `${nextStatement}:${nextPeriod}`;
    if (cache[nextKey]) {
      setShown(cache[nextKey]);
      return;
    }
    const id = ++requestId.current;
    setLoading(true);
    try {
      const data = await fetchJson<Statement>(
        `/api/companies/${encodeURIComponent(ticker)}/financials?statement=${nextStatement}&period=${nextPeriod}`,
      );
      setCache((c) => ({ ...c, [nextKey]: data }));
      if (id === requestId.current) setShown(data);
    } catch (e) {
      if (id === requestId.current) setError((e as Error).message);
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }

  function onTabKey(event: React.KeyboardEvent, index: number) {
    const offset = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!offset) return;
    event.preventDefault();
    const next = (index + offset + STATEMENTS.length) % STATEMENTS.length;
    tabRefs.current[next]?.focus();
    load(STATEMENTS[next].value, period);
  }

  const activeLabel = STATEMENTS.find((s) => s.value === statement)!.label;
  const panelId = `statement-panel-${ticker}`;
  const stale = current.statement !== statement || current.period !== period;

  return (
    <section aria-labelledby="statements-heading" className="mt-14">
      <h2 id="statements-heading" className="text-xl font-bold tracking-tight">
        Financial statements
      </h2>

      <div className="mt-4 flex flex-wrap items-end justify-between gap-x-6 gap-y-3 border-b border-rule-strong">
        <div role="tablist" aria-label="Statement" className="-mb-px flex gap-1 overflow-x-auto">
          {STATEMENTS.map((s, i) => {
            const selected = s.value === statement;
            return (
              <button
                key={s.value}
                ref={(el) => {
                  tabRefs.current[i] = el;
                }}
                type="button"
                role="tab"
                id={`tab-${s.value}`}
                aria-selected={selected}
                aria-controls={panelId}
                tabIndex={selected ? 0 : -1}
                onClick={() => load(s.value, period)}
                onKeyDown={(e) => onTabKey(e, i)}
                className={`whitespace-nowrap border-b-[3px] px-3 pb-2 pt-1 font-semibold ${
                  selected ? "border-ink text-ink" : "border-transparent text-ink-muted hover:text-ink"
                }`}
              >
                {s.label}
              </button>
            );
          })}
        </div>

        <div role="group" aria-label="Reporting period" className="mb-2 flex rounded-sm border border-rule-strong p-0.5">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              type="button"
              aria-pressed={p.value === period}
              onClick={() => load(statement, p.value)}
              className={`rounded-[2px] px-3 py-0.5 text-sm font-semibold ${
                p.value === period ? "bg-ink text-paper" : "text-ink-muted hover:text-ink"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div
        id={panelId}
        role="tabpanel"
        aria-labelledby={`tab-${statement}`}
        aria-busy={loading}
        className={`fade-busy ${loading || stale ? "opacity-50" : ""}`}
      >
        {error ? (
          <p className="py-8 text-down">{error}</p>
        ) : current.rows.length === 0 ? (
          <p className="py-8 text-ink-muted">
            {ticker} hasn&apos;t filed {period === "quarterly" ? "quarterly " : ""}financial data in a format this
            site can read. Funds, trusts, and foreign companies filing on Form 20-F often don&apos;t.
          </p>
        ) : (
          <>
            <p className="mt-3 text-sm text-ink-muted">{scaleNote(current)}</p>
            <div className="mt-2 overflow-x-auto">
              <LedgerTable statement={current} caption={`${activeLabel}, ${period}, ${ticker}`} />
            </div>
          </>
        )}
      </div>
    </section>
  );
}
