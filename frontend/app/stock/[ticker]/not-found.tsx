import { SearchBox } from "@/components/SearchBox";
import { SiteHeader } from "@/components/SiteHeader";

export default function NotFound() {
  return (
    <>
      <SiteHeader search={false} />
      <main className="mx-auto max-w-6xl px-5 py-16 sm:px-8">
        <h1 className="text-3xl font-bold tracking-tight">No company has that ticker</h1>
        <p className="mt-4 max-w-xl text-ink-muted">
          Only companies that file with the SEC are listed. Search by name if you&apos;re not sure of the symbol.
        </p>
        <div className="mt-8 max-w-2xl">
          <SearchBox variant="hero" autoFocus />
        </div>
      </main>
    </>
  );
}
