"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";

import { fetchJson } from "@/lib/client-api";
import type { SearchResult } from "@/lib/types";

type Props = {
  variant: "hero" | "compact";
  autoFocus?: boolean;
};

const DEBOUNCE_MS = 140;

export function SearchBox({ variant, autoFocus }: Props) {
  const router = useRouter();
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [failed, setFailed] = useState(false);
  const [resolved, setResolved] = useState(""); // query the current results answer

  // Debounced lookup; stale responses are aborted.
  useEffect(() => {
    const q = query.trim();
    if (!q) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const data = await fetchJson<SearchResult[]>(`/api/search?q=${encodeURIComponent(q)}`, controller.signal);
        setResults(data);
        setResolved(q);
        setActive(data.length ? 0 : -1);
        setFailed(false);
      } catch (error) {
        if ((error as Error).name !== "AbortError") setFailed(true);
      }
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  // "/" focuses the header search from anywhere on the page.
  useEffect(() => {
    if (variant !== "compact") return;
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (event.key === "/" && !["INPUT", "TEXTAREA"].includes(target.tagName) && !target.isContentEditable) {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [variant]);

  function go(ticker: string) {
    setOpen(false);
    setQuery("");
    inputRef.current?.blur();
    router.push(`/stock/${encodeURIComponent(ticker)}`);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" && results.length) {
      event.preventDefault();
      setOpen(true);
      setActive((i) => (i + 1) % results.length);
    } else if (event.key === "ArrowUp" && results.length) {
      event.preventDefault();
      setActive((i) => (i - 1 + results.length) % results.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      const choice = results[active] ?? results[0];
      if (choice) go(choice.ticker);
      else if (query.trim()) go(query.trim().toUpperCase());
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  const trimmed = query.trim();
  const settled = resolved === trimmed || failed;
  const showList = open && trimmed.length > 0 && (results.length > 0 || settled);
  const hero = variant === "hero";

  return (
    <div className={`relative ${hero ? "w-full" : "w-full max-w-xs"}`}>
      <label htmlFor={`${listId}-input`} className="sr-only">
        Search by ticker or company name
      </label>
      <input
        ref={inputRef}
        id={`${listId}-input`}
        type="text"
        role="combobox"
        aria-expanded={showList}
        aria-controls={`${listId}-list`}
        aria-autocomplete="list"
        aria-activedescendant={showList && active >= 0 ? `${listId}-opt-${active}` : undefined}
        autoComplete="off"
        autoCapitalize="characters"
        spellCheck={false}
        autoFocus={autoFocus}
        value={query}
        placeholder={hero ? "Ticker or company" : "Search companies"}
        onChange={(e) => {
          setQuery(e.target.value);
          if (!e.target.value.trim()) setResults([]);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={onKeyDown}
        className={
          hero
            ? "w-full border-0 border-b-2 border-ink bg-transparent pb-2 text-4xl font-semibold tracking-tight text-ink placeholder:text-rule-strong focus:outline-none focus-visible:outline-none focus:border-carbon sm:text-6xl"
            : "peer w-full rounded-sm border border-rule-strong bg-sheet py-1.5 pl-3 pr-8 text-sm text-ink placeholder:text-ink-muted focus:border-carbon focus:outline-none"
        }
      />
      {!hero && !query && (
        <kbd
          aria-hidden
          className="pointer-events-none absolute right-2 top-1/2 hidden -translate-y-1/2 rounded-sm border border-rule px-1.5 text-xs text-ink-muted peer-focus:hidden sm:block"
        >
          /
        </kbd>
      )}

      {showList && (
        <ul
          id={`${listId}-list`}
          role="listbox"
          aria-label="Matching companies"
          className={`absolute left-0 right-0 z-20 mt-1 overflow-hidden rounded-sm border border-rule-strong bg-sheet shadow-[0_6px_18px_-8px_rgb(23_56_45/0.35)] ${
            hero ? "text-lg" : "text-sm"
          }`}
        >
          {results.map((r, i) => (
            <li
              key={r.ticker}
              id={`${listId}-opt-${i}`}
              role="option"
              aria-selected={i === active}
              // mousedown fires before the input's blur closes the list
              onMouseDown={(e) => {
                e.preventDefault();
                go(r.ticker);
              }}
              onMouseEnter={() => setActive(i)}
              className={`flex cursor-pointer items-baseline gap-4 border-b border-rule px-3 py-2 last:border-b-0 ${
                i === active ? "bg-tint" : ""
              }`}
            >
              <span className={`shrink-0 font-bold text-carbon ${hero ? "w-24" : "w-16"}`}>{r.ticker}</span>
              <span className="min-w-0 flex-1 truncate">{r.name}</span>
              {r.exchange && <span className="shrink-0 text-xs text-ink-muted">{r.exchange}</span>}
            </li>
          ))}
          {results.length === 0 && (
            <li className="px-3 py-2 text-ink-muted" role="presentation">
              {failed
                ? "Search isn't responding. Check that the backend is running."
                : `No companies match \u201c${trimmed}\u201d.`}
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
