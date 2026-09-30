"use client";

import { useId, useState } from "react";

import { checkAssumptions, impliedGrowth, runDcf, type DcfAssumptions, type ForecastYear } from "@/lib/dcf";
import { formatCompactCurrency, formatDate, formatMetric, formatPrice, formatStatementValue } from "@/lib/format";
import type { ValuationInputs } from "@/lib/types";

type Mode = "dcf" | "reverse";

const MODES: { value: Mode; label: string }[] = [
  { value: "dcf", label: "DCF" },
  { value: "reverse", label: "Reverse DCF" },
];

const MINUS = "−";
const DASH = "—";

type Fields = {
  fcf: string;
  growth: string;
  years: string;
  terminalGrowth: string;
  discountRate: string;
  cash: string;
  debt: string;
  shares: string;
  price: string;
};

// Dollar amounts and share counts are entered in millions.
function millions(value: number | null | undefined): string {
  if (value === null || value === undefined) return "";
  const m = value / 1e6;
  return String(Number(m.toFixed(Math.abs(m) < 100 ? 2 : 0)));
}

function percent(value: number): string {
  return String(Number((value * 100).toFixed(1)));
}

function parse(text: string): number {
  return text.trim() === "" ? NaN : Number(text.replace(/[,\s$%]/g, ""));
}

function initialFields(inputs: ValuationInputs | null): Fields {
  // A starting growth guess: the historical FCF trend, kept within a sober range.
  const cagr = inputs?.fcf_cagr;
  const growth = cagr === null || cagr === undefined ? 0.05 : Math.min(Math.max(cagr, 0), 0.2);
  return {
    fcf: millions(inputs?.free_cash_flow),
    growth: percent(Math.round(growth * 200) / 200),
    years: "10",
    terminalGrowth: "2.5",
    discountRate: "9",
    cash: millions(inputs?.cash) || (inputs ? "0" : ""),
    debt: millions(inputs?.debt) || (inputs ? "0" : ""),
    shares: millions(inputs?.shares),
    price: inputs?.price ? inputs.price.toFixed(2) : "",
  };
}

function dollars(value: number): string {
  return `${value < 0 ? MINUS : ""}$${formatPrice(Math.abs(value))}`;
}

export function DcfCalculator({ inputs }: { inputs: ValuationInputs | null }) {
  const [mode, setMode] = useState<Mode>("dcf");
  const [fields, setFields] = useState<Fields>(() => initialFields(inputs));

  const set = (key: keyof Fields) => (value: string) => setFields((f) => ({ ...f, [key]: value }));

  const base: Omit<DcfAssumptions, "growth"> = {
    fcf: parse(fields.fcf) * 1e6,
    years: parse(fields.years),
    terminalGrowth: parse(fields.terminalGrowth) / 100,
    discountRate: parse(fields.discountRate) / 100,
    cash: (parse(fields.cash) || 0) * 1e6,
    debt: (parse(fields.debt) || 0) * 1e6,
    shares: parse(fields.shares) * 1e6,
  };
  const growth = parse(fields.growth) / 100;
  const price = parse(fields.price);

  return (
    <div className="mt-8 grid gap-x-12 gap-y-10 lg:grid-cols-[19rem_minmax(0,1fr)]">
      <form onSubmit={(e) => e.preventDefault()} className="self-start lg:sticky lg:top-20">
        <div role="group" aria-label="Calculator" className="flex rounded-sm border border-rule-strong p-0.5">
          {MODES.map((m) => (
            <button
              key={m.value}
              type="button"
              aria-pressed={m.value === mode}
              onClick={() => setMode(m.value)}
              className={`flex-1 rounded-[2px] px-3 py-1 text-sm font-semibold ${
                m.value === mode ? "bg-ink text-paper" : "text-ink-muted hover:text-ink"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <p className="mt-3 text-sm text-ink-muted">
          {mode === "dcf"
            ? "Project free cash flow, discount it back, and see what a share is worth."
            : "Start from the share price and solve for the growth the market is pricing in."}
        </p>

        <fieldset className="mt-6 space-y-4">
          <legend className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-muted">Cash flows</legend>
          <Field
            label="Free cash flow, starting year"
            value={fields.fcf}
            onChange={set("fcf")}
            prefix="$"
            suffix="M"
            note={inputs ? noteFor(inputs.free_cash_flow, inputs.free_cash_flow_basis) : undefined}
          />
          {mode === "dcf" && (
            <Field
              label="Annual growth, forecast years"
              value={fields.growth}
              onChange={set("growth")}
              suffix="%"
              note={historyNote(inputs)}
            />
          )}
          <Field label="Forecast years" value={fields.years} onChange={set("years")} suffix="yrs" />
          <Field
            label="Terminal growth, after the forecast"
            value={fields.terminalGrowth}
            onChange={set("terminalGrowth")}
            suffix="%"
          />
          <Field
            label="Discount rate"
            value={fields.discountRate}
            onChange={set("discountRate")}
            suffix="%"
            note="Your required return, often the WACC"
          />
        </fieldset>

        <fieldset className="mt-8 space-y-4">
          <legend className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-muted">Balance sheet</legend>
          <Field
            label="Cash and short-term investments"
            value={fields.cash}
            onChange={set("cash")}
            prefix="$"
            suffix="M"
            note={inputs ? noteFor(inputs.cash, inputs.cash_basis) : undefined}
          />
          <Field
            label="Debt"
            value={fields.debt}
            onChange={set("debt")}
            prefix="$"
            suffix="M"
            note={inputs ? (inputs.debt === null ? "Not reported" : `Long-term debt, ${inputs.debt_basis}`) : undefined}
          />
          <Field label="Shares outstanding" value={fields.shares} onChange={set("shares")} suffix="M" />
          <Field
            label="Share price"
            value={fields.price}
            onChange={set("price")}
            prefix="$"
            note={
              inputs?.price_as_of && parse(fields.price) === Number(inputs.price?.toFixed(2))
                ? `Close on ${formatDate(inputs.price_as_of)}`
                : undefined
            }
          />
        </fieldset>
      </form>

      <div className="min-w-0" aria-live="polite">
        {mode === "dcf" ? (
          <DcfResults base={base} growth={growth} price={price} />
        ) : (
          <ReverseResults base={base} price={price} inputs={inputs} />
        )}
      </div>
    </div>
  );
}

function noteFor(value: number | null, basis: string | null): string {
  return value === null ? "Not reported" : basis ? `Reported, ${basis}` : "Reported";
}

function historyNote(inputs: ValuationInputs | null): string | undefined {
  if (!inputs || inputs.fcf_cagr === null) return undefined;
  const h = inputs.fcf_history;
  return `${h[0].label}–${h[h.length - 1].label} trend: ${formatMetric(inputs.fcf_cagr, "percent")} a year`;
}

// ---------------------------------------------------------------------------
// Results
// ---------------------------------------------------------------------------

function Problem({ base, needsPrice, price }: { base: Omit<DcfAssumptions, "growth">; needsPrice?: boolean; price: number }) {
  let message: string | null = null;
  if (!Number.isFinite(base.fcf)) message = "Enter a starting free cash flow to run the model.";
  else if (needsPrice && !(price > 0)) message = "Enter a share price to solve for implied growth.";
  else {
    const problem = checkAssumptions(base);
    if (problem === "rates") message = "The discount rate has to be higher than terminal growth, or the terminal value is infinite.";
    if (problem === "shares") message = "Enter the number of shares outstanding.";
    if (problem === "years") message = "Forecast between 1 and 30 whole years.";
  }
  return message ? <p className="border-t border-rule-strong py-8 text-ink-muted">{message}</p> : null;
}

function isReady(base: Omit<DcfAssumptions, "growth">): boolean {
  return Number.isFinite(base.fcf) && checkAssumptions(base) === null;
}

function DcfResults({ base, growth, price }: { base: Omit<DcfAssumptions, "growth">; growth: number; price: number }) {
  if (!isReady(base)) return <Problem base={base} price={price} />;
  if (!Number.isFinite(growth)) {
    return <p className="border-t border-rule-strong py-8 text-ink-muted">Enter a forecast growth rate.</p>;
  }

  const result = runDcf({ ...base, growth });
  const upside = price > 0 ? result.perShare / price - 1 : null;
  const terminalShare = result.enterpriseValue > 0 ? result.pvTerminal / result.enterpriseValue : null;

  return (
    <>
      <div className="border-t border-rule-strong pt-4">
        <p className="text-sm text-ink-muted">Intrinsic value per share</p>
        <p className="tnum text-4xl font-bold tracking-tight sm:text-5xl">{dollars(result.perShare)}</p>
        {upside !== null && (
          <p className={`mt-1 font-semibold ${upside >= 0 ? "text-up" : "text-down"}`}>
            {formatMetric(Math.abs(upside), "percent")} {upside >= 0 ? "above" : "below"} the share price of{" "}
            {dollars(price)}
          </p>
        )}
      </div>

      <Bridge result={result} shares={base.shares} cash={base.cash} debt={base.debt} />
      {terminalShare !== null && terminalShare > 0.75 && (
        <p className="mt-3 text-sm text-ink-muted">
          The terminal value is {formatMetric(terminalShare, "percent")} of enterprise value, so this estimate
          depends mostly on the terminal growth and discount rates.
        </p>
      )}

      <Forecast forecast={result.forecast} />

      <Sensitivity
        title="Value per share by discount rate and terminal growth"
        base={base}
        cell={(a) => dollars(runDcf({ ...a, growth }).perShare)}
      />
    </>
  );
}

function ReverseResults({
  base,
  price,
  inputs,
}: {
  base: Omit<DcfAssumptions, "growth">;
  price: number;
  inputs: ValuationInputs | null;
}) {
  if (!isReady(base) || !(price > 0)) return <Problem base={base} price={price} needsPrice />;

  const solved = impliedGrowth(base, price);
  if (!solved.ok) {
    const message = {
      "negative-fcf":
        "A reverse DCF needs positive starting free cash flow: with negative cash flow, faster growth makes the company worth less, so no single growth rate matches the price.",
      "below-range": `Even shrinking free cash flow by 50% a year gives a value above ${dollars(price)}. The price implies less than the business already earns, or the discount rate is too low.`,
      "above-range": `Even doubling free cash flow every year doesn't reach ${dollars(price)}. Try a longer forecast, a lower discount rate, or check the inputs.`,
    }[solved.reason];
    return <p className="border-t border-rule-strong py-8">{message}</p>;
  }

  const result = runDcf({ ...base, growth: solved.growth });
  const years = base.years;

  return (
    <>
      <div className="border-t border-rule-strong pt-4">
        <p className="text-sm text-ink-muted">Implied free cash flow growth</p>
        <p className="tnum text-4xl font-bold tracking-tight sm:text-5xl">
          {formatMetric(solved.growth, "percent")}
          <span className="ml-2 text-lg font-semibold text-ink-muted">a year</span>
        </p>
        <p className="mt-2 max-w-2xl">
          At {dollars(price)} a share, the market is pricing in free cash flow growth of{" "}
          {formatMetric(solved.growth, "percent")} a year for {years} {years === 1 ? "year" : "years"}, then{" "}
          {formatMetric(base.terminalGrowth, "percent")} a year forever, discounted at{" "}
          {formatMetric(base.discountRate, "percent")}. That takes free cash flow from{" "}
          {formatCompactCurrency(base.fcf)} to {formatCompactCurrency(result.forecast[years - 1].fcf)}.
        </p>
        {inputs?.fcf_cagr !== null && inputs?.fcf_cagr !== undefined && (
          <p className="mt-2 text-ink-muted">
            For comparison, free cash flow grew {formatMetric(inputs.fcf_cagr, "percent")} a year from{" "}
            {inputs.fcf_history[0].label} to {inputs.fcf_history[inputs.fcf_history.length - 1].label}.
          </p>
        )}
      </div>

      <Bridge result={result} shares={base.shares} cash={base.cash} debt={base.debt} />
      <Forecast forecast={result.forecast} />

      <Sensitivity
        title="Implied growth by discount rate and terminal growth"
        base={base}
        cell={(a) => {
          const g = impliedGrowth(a, price);
          return g.ok ? formatMetric(g.growth, "percent") : DASH;
        }}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Tables
// ---------------------------------------------------------------------------

function scaleFor(values: number[]) {
  const largest = Math.max(...values.map(Math.abs));
  return largest >= 1e8 ? { divisor: 1e6, word: "millions" as const } : { divisor: 1e3, word: "thousands" as const };
}

function Bridge({
  result,
  shares,
  cash,
  debt,
}: {
  result: ReturnType<typeof runDcf>;
  shares: number;
  cash: number;
  debt: number;
}) {
  const scale = scaleFor([result.enterpriseValue, result.equityValue, cash, debt]);
  const money = (v: number) => formatStatementValue(v, "USD", scale);
  const rows: { label: string; value: string; level?: "subtotal" | "total"; indent?: boolean }[] = [
    { label: "Present value of forecast cash flows", value: money(result.pvForecast), indent: true },
    { label: "Present value of terminal value", value: money(result.pvTerminal), indent: true },
    { label: "Enterprise value", value: money(result.enterpriseValue), level: "subtotal" },
    { label: "Plus cash and short-term investments", value: money(cash), indent: true },
    { label: "Less debt", value: money(-debt), indent: true },
    { label: "Equity value", value: money(result.equityValue), level: "subtotal" },
    { label: `Shares outstanding (${scale.word})`, value: money(shares), indent: true },
    { label: "Value per share", value: formatStatementValue(result.perShare, "USD/shares", scale), level: "total" },
  ];

  return (
    <section aria-labelledby="bridge-heading" className="mt-10">
      <h2 id="bridge-heading" className="text-xl font-bold tracking-tight">
        From cash flows to a share price
      </h2>
      <p className="mt-1 text-sm text-ink-muted">In {scale.word} of USD, except per-share figures.</p>
      <div className="mt-2 overflow-x-auto">
        <table className="ledger">
          <caption className="sr-only">Valuation bridge</caption>
          <tbody>
            {rows.map((r) => (
              <tr key={r.label} className={r.level}>
                <th scope="row" className={`desc font-normal ${r.indent ? "indent-1" : ""}`}>
                  {r.label}
                </th>
                <td className="num">
                  <span className="fig">{r.value}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Forecast({ forecast }: { forecast: ForecastYear[] }) {
  const scale = scaleFor(forecast.map((y) => y.fcf));
  const rows: { label: string; cells: string[]; level?: "subtotal" }[] = [
    { label: "Free cash flow", cells: forecast.map((y) => formatStatementValue(y.fcf, "USD", scale)) },
    { label: "Discount factor", cells: forecast.map((y) => y.discountFactor.toFixed(3)) },
    {
      label: "Present value",
      cells: forecast.map((y) => formatStatementValue(y.presentValue, "USD", scale)),
      level: "subtotal",
    },
  ];

  return (
    <section aria-labelledby="forecast-heading" className="mt-12">
      <h2 id="forecast-heading" className="text-xl font-bold tracking-tight">
        Forecast
      </h2>
      <p className="mt-1 text-sm text-ink-muted">In {scale.word} of USD.</p>
      <div className="mt-2 overflow-x-auto">
        <table className="ledger">
          <caption className="sr-only">Projected free cash flow by year</caption>
          <thead>
            <tr>
              <th scope="col" className="desc">
                <span className="sr-only">Line item</span>
              </th>
              {forecast.map((y) => (
                <th key={y.year} scope="col" className="num">
                  Year {y.year}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.label} className={r.level}>
                <th scope="row" className="desc font-normal">
                  {r.label}
                </th>
                {r.cells.map((c, i) => (
                  <td key={i} className="num">
                    <span className="fig">{c}</span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

const RATE_STEPS = [-0.02, -0.01, 0, 0.01, 0.02];
const TERMINAL_STEPS = [-0.01, -0.005, 0, 0.005, 0.01];

function Sensitivity({
  title,
  base,
  cell,
}: {
  title: string;
  base: Omit<DcfAssumptions, "growth">;
  cell: (a: Omit<DcfAssumptions, "growth">) => string;
}) {
  const terminals = TERMINAL_STEPS.map((s) => base.terminalGrowth + s);
  return (
    <section aria-labelledby="sensitivity-heading" className="mt-12">
      <h2 id="sensitivity-heading" className="text-xl font-bold tracking-tight">
        Sensitivity
      </h2>
      <p className="mt-1 text-sm text-ink-muted">{title}. Your inputs are in the center.</p>
      <div className="mt-2 overflow-x-auto">
        <table className="ledger">
          <caption className="sr-only">{title}</caption>
          <thead>
            <tr>
              <th scope="col" className="desc">
                Discount rate <span className="font-normal text-ink-muted">/ terminal growth</span>
              </th>
              {terminals.map((t, i) => (
                <th key={i} scope="col" className="num">
                  {formatMetric(t, "percent")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {RATE_STEPS.map((rs) => {
              const rate = base.discountRate + rs;
              return (
                <tr key={rs}>
                  <th scope="row" className="desc font-semibold">
                    {formatMetric(rate, "percent")}
                  </th>
                  {terminals.map((t, i) => {
                    const a = { ...base, discountRate: rate, terminalGrowth: t };
                    const center = rs === 0 && TERMINAL_STEPS[i] === 0;
                    return (
                      <td key={i} className={`num ${center ? "bg-tint font-bold" : ""}`}>
                        {rate > t ? cell(a) : DASH}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Inputs
// ---------------------------------------------------------------------------

function Field({
  label,
  value,
  onChange,
  prefix,
  suffix,
  note,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  prefix?: string;
  suffix?: string;
  note?: string;
}) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-semibold">
        {label}
      </label>
      <div className="mt-1 flex items-baseline rounded-sm border border-rule-strong bg-sheet px-3 focus-within:border-carbon">
        {prefix && <span className="pr-1 text-ink-muted">{prefix}</span>}
        <input
          id={id}
          type="text"
          inputMode="decimal"
          autoComplete="off"
          spellCheck={false}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-describedby={note ? `${id}-note` : undefined}
          className="tnum min-w-0 flex-1 bg-transparent py-1.5 text-ink focus:outline-none focus-visible:outline-none"
        />
        {suffix && <span className="pl-2 text-sm text-ink-muted">{suffix}</span>}
      </div>
      {note && (
        <p id={`${id}-note`} className="mt-1 text-xs text-ink-muted">
          {note}
        </p>
      )}
    </div>
  );
}
