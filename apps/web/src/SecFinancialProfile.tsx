import { useState } from 'react';
import { download } from './downloads';

type Citation = {metric: string; period_end: string; value: number; unit: string; accession: string; source_url: string; accepted_at: string; published_at: string};
type Period = {period_end: string; revenue: number | null; revenue_growth: number | null; growth_acceleration: number | null; operating_margin: number | null; net_margin: number | null; cashflow_margin: number | null; citations: Citation[]};
export type FinancialProfile = {policy: string; asof: string; security_id: string; periods: number; status: string; latest: Period | null; series: Period[]; limitations: string[]};
const usd = (value: number | null) => value === null ? 'Unavailable' : new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 2}).format(value);
const percent = (value: number | null) => value === null ? 'Unavailable' : `${(value * 100).toFixed(1)}%`;

export function SecFinancialProfile({profile, cik, bundleId}: {profile: FinancialProfile; cik: string; bundleId: string}) {
  const [all, setAll] = useState(false);
  const rows = (all ? profile.series : profile.series.slice(-8)).slice().reverse();
  return <section aria-label="SEC entity financial profile"><h3>Annual financial profile</h3><p>Latest available revisions at {profile.asof}. USD entity financials; no share-class assignment or security ranking. The fact filter below does not change this profile.</p>
    <p>{profile.periods} annual revenue periods · {profile.status}</p>
    {profile.latest && <p>Latest period {profile.latest.period_end}: revenue {usd(profile.latest.revenue)} · revenue growth {percent(profile.latest.revenue_growth)} · operating margin {percent(profile.latest.operating_margin)}</p>}
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable SEC financial profile"><table><caption className="sr-only">SEC annual financial profile</caption><thead><tr><th>Period end</th><th>Revenue USD</th><th>Revenue growth</th><th>Growth acceleration</th><th>Operating margin</th><th>Net margin</th><th>Operating cashflow margin</th><th>Evidence</th></tr></thead><tbody>{rows.map(row => <tr key={row.period_end}><td>{row.period_end}</td><td>{usd(row.revenue)}</td><td>{percent(row.revenue_growth)}</td><td>{row.growth_acceleration === null ? 'Unavailable' : `${(row.growth_acceleration * 100).toFixed(1)} pp`}</td><td>{percent(row.operating_margin)}</td><td>{percent(row.net_margin)}</td><td>{percent(row.cashflow_margin)}</td><td><details><summary>Filing citations for {row.period_end}</summary>{row.citations.map(c => <p key={`${c.metric}-${c.period_end}-${c.accession}`}><a href={c.source_url} target="_blank" rel="noreferrer">{c.metric} · {c.period_end} · {c.accession}</a><small>{c.value.toLocaleString('en-US')} {c.unit} · accepted {c.accepted_at} · publication upper bound {c.published_at}</small></p>)}</details></td></tr>)}</tbody></table></div>
    {profile.series.length > 8 && <button className="secondary" onClick={() => setAll(value => !value)}>{all ? 'Show latest eight financial periods' : 'Show all financial periods'}</button>}
    <button className="secondary" onClick={() => download(`SEC-${cik}-financial-profile.json`, JSON.stringify({bundle_id: bundleId, export_scope: 'FULL_ENTITY_FINANCIAL_PROFILE', financial_profile: profile}, null, 2), 'application/json')}>Export SEC financial profile</button>
    <details><summary>Financial profile assumptions</summary><p>{profile.policy}</p><ul>{profile.limitations.map(text => <li key={text}>{text}</li>)}</ul></details>
  </section>;
}
