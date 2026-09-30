// Server-side data access. Browser code goes through the /api proxy route instead.
import "server-only";
import { cache } from "react";

import type {
  CompanyOverview,
  PeriodKind,
  PriceBar,
  PriceRange,
  Statement,
  StatementKind,
  ValuationInputs,
} from "./types";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function get<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  } catch {
    throw new ApiError(502, "The data service isn't reachable. Check that the backend is running.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.detail ?? `Request failed with status ${response.status}.`);
  }
  return response.json() as Promise<T>;
}

// `cache` dedupes the call between generateMetadata and the page within one request.
export const getOverview = cache((ticker: string) =>
  get<CompanyOverview>(`/api/companies/${encodeURIComponent(ticker)}`),
);

export function getStatement(ticker: string, statement: StatementKind, period: PeriodKind) {
  return get<Statement>(
    `/api/companies/${encodeURIComponent(ticker)}/financials?statement=${statement}&period=${period}`,
  );
}

export function getPrices(ticker: string, range: PriceRange) {
  return get<PriceBar[]>(`/api/companies/${encodeURIComponent(ticker)}/prices?range=${range}`);
}

export function getValuationInputs(ticker: string) {
  return get<ValuationInputs>(`/api/companies/${encodeURIComponent(ticker)}/valuation-inputs`);
}
