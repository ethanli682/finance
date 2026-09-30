import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { KeyFigures } from "@/components/KeyFigures";
import { PriceChart } from "@/components/PriceChart";
import { SiteHeader } from "@/components/SiteHeader";
import { Statements } from "@/components/Statements";
import { ApiError, getOverview, getPrices, getStatement } from "@/lib/api";
import { formatDate, formatPrice, formatSignedPercent, formatSignedPrice } from "@/lib/format";
import type { CompanyOverview, PriceBar, Statement } from "@/lib/types";

async function load(ticker: string) {
  try {
    const overview = await getOverview(ticker);
    // Overview has already triggered any data refresh, so these are quick reads.
    const [statement, prices] = await Promise.all([
      getStatement(overview.ticker, "income", "annual"),
      getPrices(overview.ticker, "1y").catch(() => [] as PriceBar[]),
    ]);
    return { overview, statement, prices, error: null };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    if (error instanceof ApiError) return { overview: null, statement: null, prices: [], error: error.message };
    throw error;
  }
}

export async function generateMetadata(props: PageProps<"/stock/[ticker]">): Promise<Metadata> {
  const { ticker } = await props.params;
  try {
    const overview = await getOverview(ticker);
    return { title: `${overview.name} (${overview.ticker})` };
  } catch {
    return { title: ticker.toUpperCase() };
  }
}

export default async function StockPage(props: PageProps<"/stock/[ticker]">) {
  const { ticker } = await props.params;
  const { overview, statement, prices, error } = await load(ticker);

  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-5 pb-20 pt-8 sm:px-8">
        {error || !overview || !statement ? (
          <Unavailable ticker={ticker.toUpperCase()} message={error ?? "This company's data couldn't be loaded."} />
        ) : (
          <Company overview={overview} statement={statement} prices={prices} />
        )}
      </main>
    </>
  );
}

function Company({
  overview,
  statement,
  prices,
}: {
  overview: CompanyOverview;
  statement: Statement;
  prices: PriceBar[];
}) {
  const { price } = overview;
  const up = (price?.change ?? 0) >= 0;

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-x-10 gap-y-4">
        <div className="min-w-0">
          <h1 className="text-3xl font-bold leading-tight tracking-tight sm:text-4xl">{overview.name}</h1>
          <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-ink-muted">
            <span className="font-bold text-ink">{overview.ticker}</span>
            {overview.exchange && <span>{overview.exchange}</span>}
            {overview.industry && <span>{sentenceCase(overview.industry)}</span>}
            {overview.other_tickers.length > 0 && (
              <span>
                Also trades as{" "}
                {overview.other_tickers.map((t, i) => (
                  <span key={t}>
                    {i > 0 && ", "}
                    <Link href={`/stock/${t}`} className="text-carbon underline decoration-rule-strong underline-offset-4">
                      {t}
                    </Link>
                  </span>
                ))}
              </span>
            )}
          </div>
        </div>

        {price && (
          <div className="tnum sm:text-right">
            <p className="text-3xl font-bold tracking-tight sm:text-4xl">
              {formatPrice(price.last)}
              <span className="ml-1.5 text-base font-semibold text-ink-muted">USD</span>
            </p>
            {price.change !== null && price.change_percent !== null && (
              <p className={`font-semibold ${up ? "text-up" : "text-down"}`}>
                {formatSignedPrice(price.change)} ({formatSignedPercent(price.change_percent)})
              </p>
            )}
            <p className="text-sm text-ink-muted">Close on {formatDate(price.as_of)}</p>
            {price.year_low !== null && price.year_high !== null && (
              <p className="text-sm text-ink-muted">
                52-week range {formatPrice(price.year_low)} to {formatPrice(price.year_high)}
              </p>
            )}
          </div>
        )}
      </div>

      <PriceChart ticker={overview.ticker} initialRange="1y" initialBars={prices} />

      {overview.has_financials && (
        <>
          <KeyFigures metrics={overview.metrics} />
          <p className="mt-4">
            <Link
              href={`/valuation?ticker=${encodeURIComponent(overview.ticker)}`}
              className="font-semibold text-carbon underline decoration-rule-strong underline-offset-4 hover:decoration-carbon"
            >
              Value {overview.ticker} with a DCF or reverse DCF
            </Link>
          </p>
        </>
      )}

      <Statements ticker={overview.ticker} initial={statement} />

      <p className="mt-6 text-sm text-ink-muted">
        Statements are compiled from {overview.name}&apos;s filings on{" "}
        <a
          href={`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${overview.cik}&type=10-K`}
          className="text-carbon underline decoration-rule-strong underline-offset-4"
          target="_blank"
          rel="noreferrer"
        >
          SEC EDGAR
        </a>
        {overview.fundamentals_updated_at && <>, last checked {formatDate(overview.fundamentals_updated_at)}</>}. Some
        line items are calculated from others when a company doesn&apos;t report them directly.
      </p>
    </>
  );
}

function Unavailable({ ticker, message }: { ticker: string; message: string }) {
  return (
    <div className="max-w-xl py-16">
      <h1 className="text-3xl font-bold tracking-tight">{ticker}</h1>
      <p className="mt-4">{message}</p>
      <Link
        href={`/stock/${encodeURIComponent(ticker)}`}
        className="mt-6 inline-block rounded-sm bg-ink px-4 py-2 font-semibold text-paper"
      >
        Try again
      </Link>
    </div>
  );
}

// SEC industry names arrive in capitals ("ELECTRONIC COMPUTERS").
function sentenceCase(value: string): string {
  if (value !== value.toUpperCase()) return value;
  const lower = value.toLowerCase();
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}
