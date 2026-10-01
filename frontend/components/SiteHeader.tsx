import Link from "next/link";

import { SearchBox } from "./SearchBox";

export function Wordmark() {
  return (
    <Link href="/" className="text-lg font-extrabold tracking-tight text-ink">
      <span className="double-rule">Axon</span>
    </Link>
  );
}

export function SiteHeader({ search = true }: { search?: boolean }) {
  return (
    <header className="sticky top-0 z-30 border-b border-rule bg-paper/95 backdrop-blur supports-[backdrop-filter]:bg-paper/80">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-5 py-3 sm:px-8">
        <div className="flex items-center gap-6">
          <Wordmark />
          <nav aria-label="Tools">
            <Link href="/valuation" className="text-sm font-semibold text-ink-muted hover:text-ink">
              Valuation
            </Link>
          </nav>
        </div>
        {search && <SearchBox variant="compact" />}
      </div>
    </header>
  );
}
