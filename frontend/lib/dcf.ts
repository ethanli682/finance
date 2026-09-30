// Two-stage discounted cash flow: free cash flow grows at one rate for a set number of
// years, then at a perpetual rate (Gordon growth), all discounted at a single rate.

export type DcfAssumptions = {
  fcf: number; // starting annual free cash flow, dollars
  growth: number; // yearly FCF growth during the forecast
  years: number;
  terminalGrowth: number;
  discountRate: number;
  cash: number;
  debt: number;
  shares: number;
};

export type ForecastYear = {
  year: number;
  fcf: number;
  discountFactor: number;
  presentValue: number;
};

export type DcfResult = {
  forecast: ForecastYear[];
  pvForecast: number;
  terminalValue: number;
  pvTerminal: number;
  enterpriseValue: number;
  equityValue: number;
  perShare: number;
};

export type DcfProblem = "rates" | "shares" | "years";

export function checkAssumptions(a: Omit<DcfAssumptions, "growth">): DcfProblem | null {
  if (!(a.discountRate > a.terminalGrowth)) return "rates";
  if (!(a.shares > 0)) return "shares";
  if (!Number.isInteger(a.years) || a.years < 1 || a.years > 30) return "years";
  return null;
}

export function runDcf(a: DcfAssumptions): DcfResult {
  const forecast: ForecastYear[] = [];
  let fcf = a.fcf;
  let pvForecast = 0;
  for (let year = 1; year <= a.years; year++) {
    fcf *= 1 + a.growth;
    const discountFactor = 1 / (1 + a.discountRate) ** year;
    const presentValue = fcf * discountFactor;
    pvForecast += presentValue;
    forecast.push({ year, fcf, discountFactor, presentValue });
  }
  const terminalValue = (fcf * (1 + a.terminalGrowth)) / (a.discountRate - a.terminalGrowth);
  const pvTerminal = terminalValue * forecast[forecast.length - 1].discountFactor;
  const enterpriseValue = pvForecast + pvTerminal;
  const equityValue = enterpriseValue + a.cash - a.debt;
  return {
    forecast,
    pvForecast,
    terminalValue,
    pvTerminal,
    enterpriseValue,
    equityValue,
    perShare: equityValue / a.shares,
  };
}

export const GROWTH_BOUNDS = { low: -0.5, high: 1 } as const;

export type ImpliedGrowth =
  | { ok: true; growth: number }
  | { ok: false; reason: "negative-fcf" | "below-range" | "above-range" };

// Value per share rises steadily with growth when starting FCF is positive, so bisection
// finds the one growth rate that reproduces the price.
export function impliedGrowth(a: Omit<DcfAssumptions, "growth">, price: number): ImpliedGrowth {
  if (!(a.fcf > 0)) return { ok: false, reason: "negative-fcf" };
  const value = (growth: number) => runDcf({ ...a, growth }).perShare;
  let low: number = GROWTH_BOUNDS.low;
  let high: number = GROWTH_BOUNDS.high;
  if (value(low) > price) return { ok: false, reason: "below-range" };
  if (value(high) < price) return { ok: false, reason: "above-range" };
  for (let i = 0; i < 80 && high - low > 1e-9; i++) {
    const mid = (low + high) / 2;
    if (value(mid) < price) low = mid;
    else high = mid;
  }
  return { ok: true, growth: (low + high) / 2 };
}
