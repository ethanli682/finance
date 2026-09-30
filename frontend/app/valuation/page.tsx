import type { Metadata } from "next";
import Link from "next/link";

import { DcfCalculator } from "@/components/DcfCalculator";
import { SearchBox } from "@/components/SearchBox";
import { SiteHeader } from "@/components/SiteHeader";
import { ApiError, getValuationInputs } from "@/lib/api";
import type { ValuationInputs } from "@/lib/types";

function tickerParam(value: string | string[] | undefined): string | null {
  const ticker = (Array.isArray(value) ? value[0] : value)?.trim();
  return ticker ? ticker.toUpperCase() : null;
}

async function load(ticker: string | null): Promise<{ inputs: ValuationInputs | null; error: string | null }> {
  if (!ticker) return { inputs: null, error: null };
  try {
    return { inputs: await getValuationInputs(ticker), error: null };
  } catch (error) {
    if (error instanceof ApiError) return { inputs: null, error: error.message };
    throw error;
  }
}

export async function generateMetadata(props: PageProps<"/valuation">): Promise<Metadata> {
  const ticker = tickerParam((await props.searchParams).ticker);
  return { title: ticker ? `${ticker} valuation` : "Valuation" };
}

export default async function ValuationPage(props: PageProps<"/valuation">) {
  const ticker = tickerParam((await props.searchParams).ticker);
  const { inputs, error } = await load(ticker);

  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-5 pb-20 pt-8 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-x-10 gap-y-4">
          <div className="min-w-0">
            <h1 className="text-3xl font-bold leading-tight tracking-tight sm:text-4xl">
              {inputs ? inputs.name : "Valuation"}
            </h1>
            <p className="mt-2 max-w-2xl text-ink-muted">
              {inputs ? (
                <>
                  <Link
                    href={`/stock/${encodeURIComponent(inputs.ticker)}`}
                    className="font-bold text-carbon underline decoration-rule-strong underline-offset-4"
                  >
                    {inputs.ticker}
                  </Link>{" "}
                  · Discounted cash flow and reverse DCF, starting from reported figures. Change any input.
                </>
              ) : (
                "Discounted cash flow and reverse DCF calculators. Pick a company to start from its reported figures, or enter your own."
              )}
            </p>
          </div>
          <div className="w-full max-w-xs">
            <SearchBox
              variant="compact"
              destination="valuation"
              placeholder={inputs ? "Value another company" : "Start from a company"}
            />
          </div>
        </div>

        {error && <p className="mt-6 text-down">{error}</p>}

        <DcfCalculator key={inputs?.ticker ?? "blank"} inputs={inputs} />

        <p className="mt-12 max-w-3xl text-sm text-ink-muted">
          Free cash flow is cash from operations less capital expenditures, trailing twelve months where available.
          Debt is long-term debt only; add short-term borrowings and leases yourself if they matter. A DCF is only as
          good as its assumptions, and this is not investment advice.
        </p>
      </main>
    </>
  );
}
