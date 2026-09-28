import { SiteHeader } from "@/components/SiteHeader";

export default function Loading() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-5 pt-8 sm:px-8" aria-busy="true">
        <div className="h-10 w-2/3 max-w-md rounded-sm bg-tint" />
        <div className="mt-3 h-5 w-1/3 max-w-xs rounded-sm bg-tint" />
        <div className="mt-10 h-56 rounded-sm bg-tint sm:h-72" />
        <p className="mt-6 max-w-lg text-ink-muted">
          Loading company data. The first visit to a company takes a few seconds while its filings are downloaded.
        </p>
      </main>
    </>
  );
}
