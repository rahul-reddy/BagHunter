import { useEffect, useState } from 'react';
import { download } from './downloads';

type Citation = {metric: string; concept: string; unit: string; value: number; accession: string; period_start: string | null; period_end: string; accepted_at: string; published_at: string; source_url: string};
type Row = {basis: string; period_start: string | null; period_end: string; values: Record<string, number | null>; citations: Citation[]; analysis_policy?: string; derivations?: Record<string, {method: string; status: string; reason: string | null; input_ids: (string | null)[][]}>};
type Result = {bundle_id: string; basis: string; total: number; offset: number; limit: number; source_fact_count: number; rows: Row[]; statements: {policy: string; asof: string; excluded_counts: Record<string, number>; limitations: string[]}};
const bases = {QUARTER: 'Reported quarters', ANNUAL: 'Annual statements', YTD_6M: 'Six-month cumulative', YTD_9M: 'Nine-month cumulative', INSTANT: 'Balance sheet and shares'};
const durationColumns = {revenue: 'Revenue USD', revenue_yoy: 'Revenue YoY', diluted_eps: 'Diluted EPS USD/share', diluted_weighted_shares: 'Weighted diluted shares', weighted_shares_yoy: 'Weighted shares YoY', operating_margin: 'Operating margin', net_margin: 'Net margin', operating_cashflow: 'Operating cashflow USD', ppe_payments: 'PPE payments USD', cfo_less_ppe: 'CFO less PPE USD'};
const instantColumns = {assets: 'Assets USD', liabilities: 'Liabilities USD', parent_equity: 'Parent equity USD', cash_equivalents: 'Cash and equivalents USD', current_long_term_debt: 'Current long-term debt USD', noncurrent_long_term_debt: 'Noncurrent long-term debt USD', common_shares: 'Common shares'};
const durationGroups: Record<string, {label: string; columns: Record<string, string>}> = {
  overview: {label: 'Overview', columns: durationColumns},
  growth: {label: 'Revenue growth and trailing quarters', columns: {revenue: 'Revenue USD', revenue_yoy: 'Revenue YoY', revenue_4q: 'Four direct quarters revenue USD', revenue_4q_yoy: 'Four-quarter revenue YoY', revenue_yoy_acceleration: 'YoY change vs previous quarter (pp)', revenue_yoy_change_2q: 'YoY change vs two quarters earlier (pp)'}},
  margins: {label: 'Margins and cash conversion', columns: {gross_profit: 'Reported gross profit USD', gross_margin: 'Reported gross margin', gross_margin_yoy_change: 'Gross margin YoY change (pp)', operating_margin: 'Operating margin', operating_margin_yoy_change: 'Operating margin YoY change (pp)', revenue_less_cost_margin: 'Revenue less cost-of-revenue margin proxy', revenue_less_goods_services_cost_margin: 'Revenue less goods/services cost margin proxy', cfo_less_ppe: 'CFO less PPE USD', cfo_less_ppe_to_income: 'CFO less PPE / net income proxy'}},
  compensation: {label: 'Share compensation and period-average shares', columns: {stock_compensation: 'Reported noncash share compensation USD', stock_compensation_to_revenue: 'Share compensation / revenue', diluted_weighted_shares: 'Weighted diluted shares', weighted_shares_yoy: 'Weighted shares YoY', revenue_per_weighted_share: 'Revenue / weighted diluted share USD'}},
};
const instantGroups = {overview: {label: 'Overview', columns: instantColumns}, liquidity: {label: 'Working capital and current ratio', columns: {current_assets: 'Current assets USD', current_liabilities: 'Current liabilities USD', working_capital: 'Working capital USD', working_capital_yoy_change: 'Working capital YoY change USD', current_ratio: 'Current ratio'}}};
function amount(key: string, value: number | null | undefined) {
  if (value === null || value === undefined) return 'Unavailable';
  if (key.endsWith('margin_yoy_change') || key === 'revenue_yoy_acceleration' || key === 'revenue_yoy_change_2q') return `${(value * 100).toFixed(1)} pp`;
  if (key === 'current_ratio' || key === 'cfo_less_ppe_to_income') return `${value.toFixed(2)}×`;
  if (key.endsWith('_yoy') || key.endsWith('_margin') || key === 'stock_compensation_to_revenue') return new Intl.NumberFormat('en-US', {style: 'percent', maximumFractionDigits: 1}).format(value);
  return new Intl.NumberFormat('en-US', {notation: ['diluted_eps', 'revenue_per_weighted_share'].includes(key) ? 'standard' : 'compact', maximumFractionDigits: 2}).format(value);
}

export function SecStatements({bundleId}: {bundleId: string}) {
  const [open, setOpen] = useState(false);
  return <details onToggle={event => setOpen(event.currentTarget.open)}><summary>Inspect quarterly statements, dilution and balance sheet</summary>{open && <StatementTable key={bundleId} bundleId={bundleId} />}</details>;
}

function StatementTable({bundleId}: {bundleId: string}) {
  const [basis, setBasis] = useState('QUARTER');
  const [group, setGroup] = useState('overview');
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState<{key: string; data: Result} | null>(null);
  const [failure, setFailure] = useState<{key: string; error: string} | null>(null);
  const key = JSON.stringify([bundleId, basis, offset, revision]);
  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({basis, offset: String(offset), limit: '12'});
    fetch(`/api/sec/bundles/${bundleId}/statements?${params}`, {signal: controller.signal}).then(async response => {
      if (!response.ok) throw new Error('SEC statement source verification or interpretation failed.');
      const data = await response.json() as Result;
      if (data.bundle_id !== bundleId || data.basis !== basis || data.offset !== offset) throw new Error('Statement response does not match the selected archive and period basis.');
      if (!controller.signal.aborted) setResult({key, data});
    }).catch((error: Error) => {if (!controller.signal.aborted) setFailure({key, error: error.message});});
    return () => controller.abort();
  }, [bundleId, basis, offset, key]);
  const data = result?.key === key ? result.data : null;
  const error = failure?.key === key ? failure.error : null;
  const groups: Record<string, {label: string; columns: Record<string, string>}> = basis === 'INSTANT' ? instantGroups : durationGroups;
  const columns = groups[group].columns;
  return <section aria-label="SEC financial statements"><h3>Financial statements and dilution</h3><p>Inspect directly reported quarters, annual results and cumulative cashflows. Missing quarters stay unavailable; six- and nine-month amounts are never relabeled as quarters.</p>
    <label>Statement period basis<select aria-label="Statement period basis" value={basis} onChange={e => {setBasis(e.target.value); setGroup('overview'); setOffset(0);}}>{Object.entries(bases).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    <label>Financial metric group<select aria-label="Financial metric group" value={group} onChange={e => setGroup(e.target.value)}>{Object.entries(groups).map(([value, item]) => <option key={value} value={value}>{item.label}</option>)}</select></label>
    <button className="secondary" onClick={() => setRevision(value => value + 1)}>Reload SEC statements</button>
    {error ? <p role="alert">{error}</p> : !data ? <p role="status">Verifying financial statement sources…</p> : <>
      <p>{data.source_fact_count.toLocaleString('en-US')} normalized statement facts · research clock {data.statements.asof}. Latest available revisions; no security valuation or historical identity assignment.</p>
      <p role="status">{data.total ? `Showing ${data.offset + 1}–${Math.min(data.offset + data.limit, data.total)} of ${data.total} statement periods` : 'No reported statements match this period basis.'}</p>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable financial statements"><table><caption className="sr-only">SEC financial statements by period basis</caption><thead><tr><th>Period start / end</th>{Object.entries(columns).map(([name, label]) => <th key={name}>{label}</th>)}<th>Dated evidence</th></tr></thead><tbody>{data.rows.map(row => <tr key={`${row.period_start}-${row.period_end}`}><td>{row.period_start ?? 'Instant'}<small>{row.period_end}</small></td>{Object.keys(columns).map(name => <td key={name}>{amount(name, row.values[name])}</td>)}<td><details><summary>Statement citations for {row.period_end}</summary><p>{row.analysis_policy ?? "Legacy statement analysis"}</p>{row.derivations && <ul>{Object.keys(columns).filter(name => row.derivations?.[name]).map(name => {const item = row.derivations![name]; return <li key={name}>{columns[name]}: {item.status}{item.reason ? ` · ${item.reason}` : ""}<small>{item.method} · inputs: {item.input_ids.map(id => id.join(" / ")).join("; ") || "none"}</small></li>;})}</ul>}{row.citations.map(c => <p key={`${c.metric}-${c.period_start}-${c.period_end}-${c.accession}`}><a href={c.source_url} target="_blank" rel="noreferrer">{c.concept} · {c.period_start ?? 'Instant'} / {c.period_end} · {c.accession}</a><small>{c.value.toLocaleString('en-US')} {c.unit} · accepted {c.accepted_at} · publication upper bound {c.published_at}</small></p>)}</details></td></tr>)}</tbody></table></div>
      <div className="pagination"><button className="secondary" disabled={!data.offset} onClick={() => setOffset(Math.max(0, offset - data.limit))}>Previous statement periods</button><button className="secondary" disabled={data.offset + data.limit >= data.total} onClick={() => setOffset(offset + data.limit)}>Next statement periods</button><button className="secondary" onClick={() => download(`SEC-statements-${bundleId.slice(0, 12)}-${basis}-${offset}.json`, JSON.stringify({...data, export_scope: 'CURRENT_STATEMENT_PAGE_ONLY'}, null, 2), 'application/json')}>Export current statement page</button></div>
      <details><summary>Statement definitions and exclusions</summary><p>{data.statements.policy}. YoY requires one comparable period 330–400 days earlier and positive prior amount. Weighted diluted shares are period averages; changes do not establish ownership dilution. All within-period ratios require the same accession. Cost-based margins stay separate from reported gross profit. Four-quarter totals require directly reported contiguous quarters; no Q4 is inferred. Revenue per weighted share is an entity period-average calculation with unknown class applicability. Working capital is current assets minus current liabilities; its YoY change is in USD, not a percentage. Current ratio and cash conversion require positive denominators. CFO less PPE requires both values from the same filing and exact period, with nonnegative PPE payments.</p><ul>{data.statements.limitations.map(text => <li key={text}>{text}</li>)}{Object.entries(data.statements.excluded_counts).map(([name, count]) => <li key={name}>{name}: {count}</li>)}</ul></details>
    </>}
  </section>;
}
