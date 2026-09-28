import { formatDate, formatStatementValue, pickScale } from "@/lib/format";
import type { Statement } from "@/lib/types";

export function scaleNote(statement: Statement): string {
  const scale = pickScale(statement.rows);
  const hasPerShare = statement.rows.some((r) => r.unit === "USD/shares");
  const hasShares = statement.rows.some((r) => r.unit === "shares");
  return `In ${scale.word} of ${statement.currency}${
    hasPerShare ? ", except per-share figures" : ""
  }${hasShares ? ". Share counts in " + scale.word : ""}.`;
}

export function LedgerTable({ statement, caption }: { statement: Statement; caption: string }) {
  const scale = pickScale(statement.rows);
  const firstMemo = statement.rows.findIndex((r) => r.unit !== "USD");

  return (
    <table className="ledger">
      <caption className="sr-only">{caption}</caption>
      <thead>
        <tr>
          <th scope="col" className="desc">
            <span className="sr-only">Line item</span>
          </th>
          {statement.periods.map((p) => (
            <th key={p.end} scope="col" className="num">
              {p.label}
              <span className="period-end">{formatDate(p.end)}</span>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {statement.rows.map((row, index) => {
          const memo = row.unit !== "USD";
          const memoStart = index === firstMemo;
          const classes = [row.level !== "item" ? row.level : "", memo ? "memo" : "", memoStart ? "memo-start" : ""]
            .filter(Boolean)
            .join(" ");
          return (
            <tr key={row.key} className={classes || undefined}>
              <th scope="row" className={`desc font-normal ${row.indent ? "indent-1" : ""}`}>
                {row.label}
              </th>
              {row.values.map((value, i) => (
                <td key={statement.periods[i].end} className={`num ${value === null ? "missing" : ""}`}>
                  <span className="fig">{formatStatementValue(value, row.unit, scale)}</span>
                </td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
