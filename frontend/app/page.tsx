import Link from "next/link";

import { SearchBox } from "@/components/SearchBox";
import { Wordmark } from "@/components/SiteHeader";

const EXAMPLES = [
  { ticker: "AAPL", name: "Apple" },
  { ticker: "MSFT", name: "Microsoft" },
  { ticker: "NVDA", name: "Nvidia" },
  { ticker: "JPM", name: "JPMorgan Chase" },
  { ticker: "KO", name: "Coca-Cola" },
];

export default function Home() {
  return (
    <div className="flex min-h-dvh flex-col">
      <div className="mx-auto w-full max-w-6xl px-5 pt-6 sm:px-8">
        <Wordmark />
      </div>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col justify-center px-5 pb-24 sm:px-8">
        <h1 className="mb-6 max-w-xl text-lg text-ink-muted">
          Look up any company that files with the SEC: its share price, income statement, balance sheet, and cash
          flows.
        </h1>
        <div className="max-w-3xl">
          <SearchBox variant="hero" autoFocus />
        </div>
        <p className="mt-6 text-ink-muted">
          Try{" "}
          {EXAMPLES.map((e, i) => (
            <span key={e.ticker}>
              <Link
                href={`/stock/${e.ticker}`}
                title={e.name}
                className="font-semibold text-carbon underline decoration-rule-strong underline-offset-4 hover:decoration-carbon"
              >
                {e.ticker}
              </Link>
              {i < EXAMPLES.length - 2 ? ", " : i === EXAMPLES.length - 2 ? ", or " : "."}
            </span>
          ))}
        </p>
      </main>

      <footer className="mx-auto w-full max-w-6xl px-5 pb-8 text-sm text-ink-muted sm:px-8">
        Financial statements come from company filings on SEC EDGAR. Prices are daily closes.
      </footer>
    </div>
  );
}
