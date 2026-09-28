// Browser-side fetches go same-origin through app/api/[...path]/route.ts.

export async function fetchJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed with status ${response.status}.`);
  }
  return response.json() as Promise<T>;
}
