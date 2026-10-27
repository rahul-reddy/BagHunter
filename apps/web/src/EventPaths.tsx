import { useState } from 'react';

type Fact = {metric: string; value: number; unit: string; period_end: string; published_at: string;
  accepted_at: string; accession: string; source_id: string};
type Vector = {ticker: string; close: number; return_63d: number; source_ids: string[];
  latest_included_publication: string; evidence: Fact[];
  technical: {volatility_20d: number | null; volatility_60d: number | null; volatility_contraction: number | null; base_duration_windows: number | null; base_left_censored: boolean | null};
  financials: {period_end: string | null; revenue: number | null; revenue_growth: number | null; operating_margin: number | null}};
type Point = {offset: number; point_session: string | null; asof_time: string | null; timing: string; status: string; snapshot: Vector | null};
type Member = {security_id: string; name: string; sector: string; outcome_group: string; points: Point[];
  outcome: {max_multiple: number | null; terminal_total_return: number | null; max_drawdown: number | null; coverage_flag: string; delisted: boolean | null}};
type Pair = {case_security_id: string; control_security_id: string; control_weight: number; control_sampling_probability: number; strata: string[]};
export type EventPathReport = {mode: string; scope: string; policy_sha256: string; offsets: number[];
  policy: {version: string; horizon_years: number; max_hit_threshold: number; seed: number};
  calendar: {basis: string; start: string; end: string; sessions: number};
  anchors: {anchor: string; eligible: number; cases: number; missing_outcomes: number; unmatched_cases: string[]; members: Member[]; pairs: Pair[]}[];
  limitations: string[]};
type Metric = 'return_63d' | 'close' | 'revenue_growth';
const percent = (v: number | null | undefined) => v == null ? 'Missing' : `${(100*v).toFixed(2)}%`;
const number = (v: number | null | undefined) => v == null ? 'Missing' : v.toLocaleString('en-US',{maximumFractionDigits:3});
const human = (s: string) => s.replaceAll('_',' ');
const metricValue = (p: Point, metric: Metric) => !p.snapshot ? null : metric === 'revenue_growth' ? p.snapshot.financials.revenue_growth : p.snapshot[metric];

function PathChart({members, metric}: {members: Member[]; metric: Metric}) {
  const values = members.flatMap(m => m.points.map(p => metricValue(p,metric))).filter((v): v is number => v != null);
  if (!values.length) return <p>No available values for this path metric. Missing points are not interpolated.</p>;
  const low = Math.min(...values), high = Math.max(...values), spread = high-low || (metric === 'close' ? 1 : .01);
  const bottom = high === low ? low-spread : low;
  const x = (offset: number) => 70+(offset+120)/140*720;
  const y = (value: number) => 200-(value-bottom)/spread*160;
  const colors = ['#75e4cd','#efbe7b'];
  const title = metric === 'close' ? 'Raw close in fixture USD' : metric === 'revenue_growth' ? 'Dated annual revenue growth' : 'Trailing 63-observation raw close return';
  return <figure className="chart"><svg viewBox="0 0 840 270" role="img" aria-label={`Descriptive event paths: ${title}`}>
    <rect x={x(0)} y="20" width={x(20)-x(0)+12} height="194" fill="#3c3121"/>
    {[0,1,2,3].map(i => <g key={i}><line x1="70" x2="802" y1={40+i*160/3} y2={40+i*160/3} stroke="#33434d" strokeDasharray="3 5"/><text x="0" y={44+i*160/3} fill="#b8cbd4" fontSize="11">{metric === 'close' ? number(high-i*spread/3) : percent(high-i*spread/3)}</text></g>)}
    {[-120,-60,-20,0,20].map(o => <text key={o} x={x(o)-10} y="237" fill="#b8cbd4" fontSize="12">{o > 0 ? '+' : ''}{o}</text>)}
    {members.map((m,index) => {
      let connected = false;
      const d = m.points.map(p => {const v = metricValue(p,metric); if (v == null) {connected=false; return '';} const command = connected ? 'L' : 'M'; connected=true; return `${command}${x(p.offset)},${y(v)}`;}).join(' ');
      return <g key={m.security_id}><path d={d} fill="none" stroke={colors[index%2]} strokeWidth="2.5" strokeDasharray={index ? '6 4' : undefined}/>{m.points.map(p => {const v=metricValue(p,metric); return v == null ? null : <circle key={p.offset} cx={x(p.offset)} cy={y(v)} r="4" fill={colors[index%2]}/>;})}</g>;
    })}
    <text x="70" y="263" fill="#b8cbd4" fontSize="11">Offset in synthetic weekdays · t+20 is post-anchor hindsight</text>
  </svg><figcaption>{title}. {members.map((m,i)=>`${m.security_id} (${i ? 'dashed' : 'solid'})`).join(' / ')}. Shaded t→t+20 region is descriptive only. Lines break at missing points; no normalization by future anchor prices.</figcaption></figure>;
}

export function EventPaths({report,runId}: {report?: EventPathReport | null; runId: string}) {
  const [anchorId,setAnchorId] = useState('');
  const [pairId,setPairId] = useState('');
  const [memberId,setMemberId] = useState('');
  const [offset,setOffset] = useState(0);
  const [metric,setMetric] = useState<Metric>('return_63d');
  const selected = report?.anchors.find(a=>a.anchor===anchorId) ?? report?.anchors.find(a=>a.pairs.length) ?? report?.anchors[0];
  const pair = selected?.pairs.find(p=>`${p.case_security_id}__${p.control_security_id}`===pairId) ?? selected?.pairs[0];
  const standalone = selected?.members.find(m=>m.security_id===memberId) ?? selected?.members[0];
  const shown = pair ? selected?.members.filter(m=>[pair.case_security_id,pair.control_security_id].includes(m.security_id)).sort((a,b)=>Number(b.security_id===pair.case_security_id)-Number(a.security_id===pair.case_security_id)) ?? [] : standalone ? [standalone] : [];
  return <section className="panel event-paths" aria-label="Historical event paths"><h2>Declared calendar event paths</h2>
    {!report ? <p>Event paths unavailable in this archive. Rebuild the fixture pipeline to materialize the descriptive study.</p> : <>
      <p className="eyebrow">FIXTURE · RETROSPECTIVE GROUPING · LATER POINTS ARE HINDSIGHT</p>
      <p>Quarter-start anchors are declared independently of outcomes. Every eligible common ID and missing/unmatched group stays in the report. This is a descriptive case/control diagnostic; it supplies no population hit probability or causal finding.</p>
      <p>{report.policy.version} · {report.policy.horizon_years}-year maximum-hit threshold {report.policy.max_hit_threshold}× · seed {report.policy.seed}. Calendar {report.calendar.start} → {report.calendar.end}: synthetic weekdays, including exchange holidays.</p>
      <div className="filters"><label>Event anchor<select aria-label="Event anchor" value={selected?.anchor ?? ''} onChange={e=>{setAnchorId(e.target.value);setPairId('');setMemberId('');}}>{report.anchors.map(a=><option key={a.anchor}>{a.anchor}</option>)}</select></label>
        {pair ? <label>Event case/control pair<select aria-label="Event case/control pair" value={`${pair.case_security_id}__${pair.control_security_id}`} onChange={e=>setPairId(e.target.value)}>{selected?.pairs.map(p=><option key={p.case_security_id} value={`${p.case_security_id}__${p.control_security_id}`}>{p.case_security_id} / {p.control_security_id}</option>)}</select></label> : <label>Event cohort member<select aria-label="Event cohort member" value={standalone?.security_id ?? ''} onChange={e=>setMemberId(e.target.value)}>{selected?.members.map(m=><option key={m.security_id}>{m.security_id}</option>)}</select></label>}
        <label>Path metric<select aria-label="Path metric" value={metric} onChange={e=>setMetric(e.target.value as Metric)}><option value="return_63d">Trailing raw 63-observation return</option><option value="close">Raw close in fixture USD</option><option value="revenue_growth">Dated annual revenue growth</option></select></label>
        <label>Inspect path offset<select aria-label="Inspect path offset" value={offset} onChange={e=>setOffset(Number(e.target.value))}>{report.offsets.map(o=><option key={o} value={o}>{o>0?'+':''}{o}</option>)}</select></label></div>
      <p role="status">Anchor {selected?.anchor}: {selected?.cases} cases / {selected?.eligible} eligible; {selected?.missing_outcomes} missing horizons; {selected?.unmatched_cases.length} unmatched cases.</p>
      {pair ? <p>Case {pair.case_security_id} · control {pair.control_security_id}. Control probability {percent(pair.control_sampling_probability)}; sampling weight {pair.control_weight}. Matched strata: {pair.strata.join(', ')}. Sector is a fixture industry proxy; grouping and weights are retrospective.</p> : <p>No matched case/control pair at this anchor. The member path remains inspectable.</p>}
      <PathChart members={shown} metric={metric}/>
      <div className="table-scroll" tabIndex={0}><table><caption>Dated case/control path snapshots</caption><thead><tr><th>Security / offset</th><th>Point session</th><th>Coverage / timing</th><th>Raw close USD</th><th>Trailing 63 return</th><th>Annual revenue growth</th><th>Operating margin</th></tr></thead><tbody>{shown.flatMap(m=>m.points.map(p=><tr key={`${m.security_id}-${p.offset}`}><td>{m.security_id}<small>{p.offset>0?'+':''}{p.offset}</small></td><td>{p.point_session ?? 'Missing'}</td><td className="wrap-cell">{human(p.status)}<small>{human(p.timing)}</small></td><td>{number(p.snapshot?.close)}</td><td>{percent(p.snapshot?.return_63d)}</td><td>{percent(p.snapshot?.financials.revenue_growth)}</td><td>{percent(p.snapshot?.financials.operating_margin)}</td></tr>))}</tbody></table></div>
      {shown.map(m=>{const p=m.points.find(v=>v.offset===offset); const v=p?.snapshot; return <details key={m.security_id}><summary>{m.security_id} · selected offset {offset>0?'+':''}{offset} · dated evidence</summary><p>{p?.point_session ?? 'Outside calendar'} · {p ? human(p.status) : 'Missing point'} · {p ? human(p.timing) : 'Missing timing'}. Point clock {p?.asof_time ?? 'Missing'}.</p>{v ? <><p>Latest included publication {v.latest_included_publication}; price session {p?.point_session}. Source IDs: {v.source_ids.join(', ')}. Filing processing lag: 24 hours after acceptance/publication. Financial period: {v.financials.period_end ?? 'Missing'}.</p><p>Annualized volatility20 / 60: {percent(v.technical.volatility_20d)} / {percent(v.technical.volatility_60d)}; contraction: {number(v.technical.volatility_contraction)}. Base windows: {v.technical.base_duration_windows == null ? 'Missing' : `${v.technical.base_duration_windows}${v.technical.base_left_censored ? ' or more' : ''}`}. Values are raw-price descriptive diagnostics.</p><ul>{v.evidence.map(f=><li key={`${f.accession}-${f.metric}-${f.period_end}`}>{f.metric} {number(f.value)} {f.unit}; period {f.period_end}; first public {f.published_at}; accepted {f.accepted_at}. <a href={`/api/sources/${encodeURIComponent(f.source_id)}`} target="_blank" rel="noreferrer">{f.accession} · fixture source ledger</a></li>)}</ul>{!v.evidence.length && <p>No filings available at this point.</p>}</> : <p>No snapshot is substituted for this missing point.</p>}<p>Separate hindsight outcome: maximum {number(m.outcome.max_multiple)}×; terminal {percent(m.outcome.terminal_total_return)}; drawdown {percent(m.outcome.max_drawdown)}; {human(m.outcome.coverage_flag)}. Outcome group {m.outcome_group}.</p></details>;})}
      <details><summary>Event policy fingerprint and limitations</summary><code>{report.policy_sha256}</code><ul>{report.limitations.map(l=><li key={l}>{l}</li>)}</ul></details>
    </>}
    <div className="button-row"><a href={`/api/runs/${runId}/reports/event_paths.json`}>Download descriptive event paths</a><a href={`/api/runs/${runId}/reports/event_paths.md`}>Download event-study report</a></div>
  </section>;
}
