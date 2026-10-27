import { useState } from 'react';
import type { DailyRisk } from './DailyRiskPanel';

type Target = {security_id: string; sector: string; requested_weight: number; planned_weight: number;
  asof_time: string; latest_included_publication: string; source_ids: string[];
  volatility: {value: number | null; window: number; observations: number; latest_available_at: string | null} | null};
type Plan = {decision: string; asof_time: string; mode: string; pool_count: number; accepted_count: number;
  targets: Target[]; entry_cash_fraction: number; requested_sector_weights: Record<string, number>;
  realized_sector_weights: Record<string, number>; exclusions: {security_id: string; reason: string}[]};
export type PortfolioComparison = {id: string; policy: {selector: string; allocation: string; volatility_window: number;
  capital: number; max_position: number; max_sector: number; participation: number; one_way_cost_bps: number};
  metrics: {total_return: number | null; max_drawdown: number | null}; daily_risk: DailyRisk;
  ending_equity: number; allocation_ledger: Plan[]; rows: {decision: string; entry: string; exit: string}[];
  executions: {security_id: string; decision: string; entry_notional: number; entry_cost: number; starting_capital: number}[]; exclusions: {decision: string; security_id: string; reason: string}[]};
const percent = (v: number | null | undefined) => v == null ? 'Missing' : `${(v*100).toFixed(2)}%`;
const label = (value: string) => ({cap_ranked:'Ranked position caps', equal_weight:'Equal weight', inverse_volatility:'Inverse volatility', sector_neutral:'Equal-sector targets', cash:'Cash'}[value] ?? value);

export function PortfolioComparisons({comparisons, runId}: {comparisons?: PortfolioComparison[]; runId: string}) {
  const [selectedId, setSelectedId] = useState('');
  const [decision, setDecision] = useState('');
  const selected = comparisons?.find(c => c.id === selectedId) ?? comparisons?.[0];
  const plan = selected?.allocation_ledger.find(p => p.decision === decision) ?? selected?.allocation_ledger[0];
  return <section className="panel portfolio-comparisons" aria-label="Allocation comparisons">
    <h2>Allocation comparison evidence</h2>
    {!comparisons?.length ? <p>Allocation comparison ledgers unavailable in this archive. Rebuild the fixture pipeline to create a new run.</p> : <>
      <p>FIXTURE · raw-price inputs · predeclared ranking and allocation variations. Every variation uses the configured capital, dates, price/liquidity floors, costs, participation, position and sector caps. Results describe artificial paths; no winning rule is selected.</p>
      <div className="table-scroll" tabIndex={0}><table><caption>Ranking and allocation comparisons</caption><thead><tr><th>Ranking</th><th>Allocation</th><th>Return</th><th>Daily drawdown</th><th>Daily volatility</th><th>Executions</th><th>Exclusions</th></tr></thead><tbody>{comparisons.map(c => <tr key={c.id}><td>{c.policy.selector}</td><td>{label(c.policy.allocation)}</td><td>{percent(c.metrics.total_return)}</td><td>{percent(c.daily_risk.max_drawdown)}</td><td>{percent(c.daily_risk.annualized_volatility)}</td><td>{c.executions.length}</td><td>{c.exclusions.length}</td></tr>)}</tbody></table></div>
      <div className="filters"><label>Inspect allocation comparison<select value={selected?.id ?? ''} onChange={e => {setSelectedId(e.target.value); setDecision('');}}>{comparisons.map(c => <option key={c.id} value={c.id}>{c.policy.selector} · {label(c.policy.allocation)}</option>)}</select></label><label>Allocation decision<select value={plan?.decision ?? ''} onChange={e => setDecision(e.target.value)}>{selected?.allocation_ledger.map(p => <option key={p.decision}>{p.decision}</option>)}</select></label></div>
      {selected && <p>Marked period {selected.daily_risk.period_start ?? 'Unavailable'} → {selected.daily_risk.period_end ?? 'Unavailable'}; {selected.daily_risk.observations} marks. Configured capital ${selected.policy.capital.toLocaleString('en-US')}; position / sector caps {percent(selected.policy.max_position)} / {percent(selected.policy.max_sector)}; participation {percent(selected.policy.participation)}; one-way costs {selected.policy.one_way_cost_bps} bps. Allocation: {label(selected.policy.allocation)}.</p>}
      {plan ? <><p role="status">Decision {plan.decision}: {plan.accepted_count} / {plan.pool_count} candidates have allocation inputs. Entry cash after costs: {percent(plan.entry_cash_fraction)}.</p><div className="table-scroll" tabIndex={0}><table><caption>Dated allocation targets</caption><thead><tr><th>Security / sector</th><th>Requested</th><th>After position / sector caps</th><th>Capital used (including fees)</th><th>Execution state</th><th>Annualized risk</th><th>Latest input publication</th></tr></thead><tbody>{plan.targets.map(t => {
        const trade = selected?.executions.find(e => e.decision === plan.decision && e.security_id === t.security_id);
        const reasons = selected?.exclusions.filter(e => e.decision === plan.decision && e.security_id === t.security_id).map(e => e.reason.replaceAll('_',' '));
        return <tr key={t.security_id}><td>{t.security_id}<small>{t.sector || 'Missing sector'}</small></td><td>{percent(t.requested_weight)}</td><td>{percent(t.planned_weight)}</td><td>{trade ? percent((trade.entry_notional + trade.entry_cost) / trade.starting_capital) : percent(0)}</td><td>{trade ? 'Executed' : plan.mode === 'cash' ? 'Cash allocation' : reasons?.join('; ') || 'Unfilled'}</td><td>{t.volatility ? `${percent(t.volatility.value)} · ${t.volatility.window} returns` : 'Not required'}</td><td>{t.latest_included_publication}</td></tr>;})}</tbody></table></div><div className="table-scroll" tabIndex={0}><table><caption>Requested and realized sector weights</caption><thead><tr><th>Sector</th><th>Requested target</th><th>Capital used (including fees)</th></tr></thead><tbody>{Object.keys(plan.requested_sector_weights).sort().map(sector => <tr key={sector}><td>{sector || 'Missing sector'}</td><td>{percent(plan.requested_sector_weights[sector])}</td><td>{percent(plan.realized_sector_weights[sector] ?? 0)}</td></tr>)}</tbody></table></div><p>Allocation exclusions: {plan.exclusions.length ? plan.exclusions.map(e => `${e.security_id}: ${e.reason.replaceAll('_',' ')}`).join('; ') : 'None'}.</p></> : <p>No allocation decisions in this run.</p>}
      <details><summary>Allocation definitions and limitations</summary><p>Equal weight divides capital among dated candidates. Inverse volatility normalizes reciprocal population volatility over {selected?.policy.volatility_window} simple close returns, annualized by √252; zero or missing volatility is excluded. Equal-sector targets divide capital equally among available sectors and equally among their members. Raw closes can contain corporate-action effects. Sector metadata is a proxy; dated benchmark sector weights are unavailable.</p><p>Position caps apply first, then nonlegacy targets in each sector scale down proportionally to the sector cap. Entry costs fit inside those envelopes. Missing entries, participation limits, costs and whole-share rounding leave cash without redistributing unfilled targets. Realized sector weights can differ from equal-sector targets. Ranked position caps preserve the legacy ranked fill order. Cash earns zero. All allocation inputs precede execution.</p></details>
    </>}
    <a href={`/api/runs/${runId}/reports/portfolio_comparators.json`}>Download allocation comparison ledgers</a>
  </section>;
}
