import { formatMetric } from "@/lib/format";
import type { Metric } from "@/lib/types";

export function KeyFigures({ metrics }: { metrics: Metric[] }) {
  return (
    <section aria-labelledby="figures-heading" className="mt-12">
      <h2 id="figures-heading" className="text-xl font-bold tracking-tight">
        Key figures
      </h2>
      <dl className="mt-4 grid grid-cols-2 border-t border-rule-strong sm:grid-cols-3 lg:grid-cols-4">
        {metrics.map((m) => (
          <div key={m.key} className="border-b border-rule py-3 pr-4">
            <dt className="text-sm text-ink-muted">{m.label}</dt>
            <dd className="tnum mt-0.5 text-xl font-semibold">{formatMetric(m.value, m.format)}</dd>
            <dd className="text-xs text-ink-muted">{m.value === null ? "Not reported" : m.basis}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
