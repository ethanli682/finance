"use client";

import { useEffect } from "react";

export default function Error({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto max-w-6xl px-5 py-16 sm:px-8">
      <h1 className="text-3xl font-bold tracking-tight">This page didn&apos;t load</h1>
      <p className="mt-4 max-w-xl">
        Something failed while building the page. Check that the backend is running, then try again.
      </p>
      <button type="button" onClick={() => retry()} className="mt-6 rounded-sm bg-ink px-4 py-2 font-semibold text-paper">
        Try again
      </button>
    </main>
  );
}
