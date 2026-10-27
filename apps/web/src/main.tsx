import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';
import { TechnicalEvidence, type Technical, type RelativeEvidence } from './TechnicalEvidence';
import { FinvizBrowser } from './FinvizBrowser';
import { SecEvidenceBrowser } from './SecEvidenceBrowser';
import type { PortfolioComparison } from './PortfolioComparisons';
import type { DailyRisk } from './DailyRiskPanel';
import type { Sensitivity } from './RankingSensitivity';
import type { NegativeControlReport } from './NegativeControls';
import { PriceChart, ThesisStudio, Settings, ValidationTools, CohortExplorer, RunTools, usePreferences, percent } from './ResearchTools';

type Fact = { metric: string; value: number; period_end: string; published_at: string;
  accession: string; source_id: string; amended: boolean };
export type Signal = { security_id: string; name: string; ticker: string; stage: string; score: number;
  close: number; base_high_60d: number; return_1d: number; return_5d: number; return_21d: number; return_63d: number;
  completeness: number; components: Record<string, number | null>; weights: Record<string, number>;
  dollar_volume_20d: number; relative_volume: number; asof_time: string; price_session: string;
  sector: string; cap_bucket: string; relative_strength_63d: number | null; sector_breadth: number | null;
  sector_peer_count: number; volatility_20d: number; consolidation: boolean; stage_reason: string;
  financials?: {numeric_limits?: string[]; period_end: string | null; revenue: number | null; revenue_growth: number | null; operating_margin: number | null; net_margin: number | null; cashflow_margin: number | null; revenue_growth_acceleration: number | null};
  risk_flags: string[]; stage_history: {asof: string; session: string; stage: string; reason: string; close: number; score: number}[];
  evidence: Fact[]; technical?: Technical; relative_evidence?: RelativeEvidence; chart: {date: string; close: number; volume?: number}[]; limitations: string[] };
type Label = { security_id: string; horizon_years: number; max_multiple: number | null;
  terminal_total_return: number | null; max_drawdown: number | null; coverage_flag: string };
export type Run = { run_id: string; asof: string; model_version: string; archive_integrity?: string; age_days: number;
  signals: Signal[]; limitations: string[]; thesis_status: string;
  sources: {source_id: string; sha256: string; latest_source_timestamp: string;
    coverage: string; license_note: string; market_provider: {reason: string}}[];
  discovery?: {sensitivity?: Sensitivity; policy: Record<string, unknown>; policy_sha256: string; stage_counts: Record<string, number>; breadth: number | null; regime: string; benchmark_return_63d: number | null};
  portfolio?: {comparator_runs?: PortfolioComparison[]; daily_risk?: DailyRisk; daily_curve?: {date: string; equity: number; basis: string}[]; policy: {capital: number; max_position: number; max_sector: number; participation: number; one_way_cost_bps: number}; ending_equity: number;
    comparators: {id?: string; allocation?: string; selector: string; metrics: {total_return: number | null; max_drawdown: number | null}; executions: number; excluded: number; ending_equity: number}[];
    metrics: {total_return: number | null; max_drawdown: number | null; win_rate: number | null}; limitations: string[];
    rows: {decision: string; deployment_fraction: number; costs: number; turnover: number; ending_equity: number}[];
    executions: {decision: string; security_id: string; sector: string; shares: number; entry_notional: number; starting_capital: number; capacity_limit: number; entry_cost: number; exit_cost: number; delisted: boolean}[]};
  validation?: {discovery_negative_controls?: NegativeControlReport; negative_controls?: NegativeControlReport; metrics: Record<string, {windows: number; total_return: number | null; cagr: number | null; max_drawdown: number | null; win_rate: number | null; payoff_ratio: number | null}>;
    holdout_status: string; partitions: {train: string[]; validation: string[]; holdout: string[]; purged: string[]; embargo_days: number};
    cost_sensitivity: {round_trip_bps: number; total_return: number | null; max_drawdown: number | null}[];
    paired_window_bootstrap: {resamples: number; mean_excess_versus_equal_weight: number | null; interval_95: number[] | null}};
  study: {cohorts?: {anchors: string[]; labels: (Label & {anchor: string; sector: string})[]; grid: {anchor: string; horizon_years: number; sector: string; threshold: number; eligible: number; complete: number; missing: number; cases: number; failed_terminal: number; delisted: number; observed_fraction: number | null}[]}; anchor: string; denominator: number; scope: string; labels: Label[];
    anchor_features: Signal[]; pairs: {case_security_id: string; control_security_id: string; control_weight: number}[]};
  backtest: {period_start: string; period_end: string; split: string; execution: string;
    cost_round_trip_bps: number; ending_wealth: Record<string, number>; limitations: string[];
    rows: {decision: string; entry: string; exit: string; security_id: string;
      net_return: number | null; equal_weight_net: number | null; benchmark_net: number | null}[];
    equity_curve: {date: string; selector: number; equal_weight: number; benchmark: number}[] } };

const pct = (n: number | null) => n === null ? 'Missing' : `${n >= 0 ? '+' : ''}${(n * 100).toFixed(2)}%`;
const money = (n: number) => new Intl.NumberFormat('en-US', {
  style: 'currency', currency: 'USD', maximumFractionDigits: 2,
}).format(n);
const pretty = (text: string) => text.replaceAll('_', ' ');
const pages = ['Command Center', 'BagHunter Radar', '100-Bagger Museum', 'Candidate DNA', 'Thesis Studio', 'Validation Lab', 'Data Quality', 'Settings', 'Finviz Observations'];

function LineChart({ series, label }: {series: {name: string; values: number[]}[]; label: string}) {
  const values = series.flatMap(s => s.values);
  const min = Math.min(...values), max = Math.max(...values);
  const width = 800, height = 210;
  return <figure className="chart"><svg viewBox={`0 0 ${width} ${height + 30}`} role="img" aria-label={label}>
    {[0, 1, 2, 3].map(i => <g key={i}>
      <line x1="55" x2="790" y1={i * 60 + 10} y2={i * 60 + 10} stroke="#29373e" strokeDasharray="3 5" />
      <text x="0" y={i * 60 + 15} fill="#aab9c2" fontSize="12">{(max - (max - min) * i / 3).toFixed(2)}</text>
    </g>)}
    {series.map((s, i) => <polyline key={s.name} fill="none" stroke={['#75e4cd', '#e5b56a', '#aab9ff'][i]}
      strokeWidth="2.5" points={s.values.map((n, j) => `${55 + j / Math.max(1, s.values.length - 1) * 735},${190 - (n - min) / (max - min || 1) * 180}`).join(' ')} />)}
  </svg><figcaption>{label} · {series.map(s => s.name).join(' / ')}</figcaption></figure>;
}

function App() {
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState('');
  const [page, setPage] = useState('Command Center');
  const [selected, setSelected] = useState('fx-compound');
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<'score' | 'return_63d' | 'relative_volume' | 'dollar_volume_20d' | 'completeness'>('score');
  const [stage, setStage] = useState('ALL');
  const [reload, setReload] = useState(0);
  const [activeRun, setActiveRun] = useState('current');
  const [preferences, setPreferences, storageError] = usePreferences();
  const [volumeFloor, setVolumeFloor] = useState(0);
  const [consolidationOnly, setConsolidationOnly] = useState(false);
  const [capBucket, setCapBucket] = useState('ALL');
  const [momentumFloor, setMomentumFloor] = useState(-100);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/runs/${activeRun}`, { signal: controller.signal }).then(async r => {
      if (!r.ok) throw new Error('No research run available. Run: uv run baghunter demo');
      return r.json() as Promise<Run>;
    }).then(data => { setRun(data); setError(''); }).catch((e: Error) => {
      if (e.name !== 'AbortError') setError(e.message);
    });
    return () => controller.abort();
  }, [reload, activeRun]);
  const candidate = run?.signals.find(s => s.security_id === selected) ?? run?.signals[0];
  const open = (s: Signal) => {setSelected(s.security_id); setPage('Candidate DNA');};
  const filtered = run?.signals.filter(s => `${s.ticker} ${s.security_id} ${s.name}`.toLowerCase()
    .includes(search.toLowerCase()) && (stage === 'ALL' || s.stage === stage)
    && s.dollar_volume_20d >= preferences.minLiquidity && s.completeness >= preferences.minCoverage
    && (preferences.sector === 'ALL' || s.sector === preferences.sector)
    && (!preferences.watchOnly || preferences.watchlist.includes(s.security_id))
    && (capBucket === 'ALL' || s.cap_bucket === capBucket) && s.return_63d * 100 >= momentumFloor
    && s.relative_volume >= volumeFloor && (!consolidationOnly || s.consolidation))
    .sort((a, b) => b[sort] - a[sort]) ?? [];
  const radar = <section className="panel"><div className="panel-title"><div><h2>Research queue</h2>
    <p>Trace every rank to its inputs. All names below are fictional.</p></div><span className="tag">FIXTURE</span></div>
    <div className="filters"><label>Find a security<input value={search} onChange={e => setSearch(e.target.value)} placeholder="Ticker or permanent ID" /></label>
      <label>Stage<select value={stage} onChange={e => setStage(e.target.value)}><option value="ALL">All stages</option>{['WATCH', 'IGNITION', 'EMERGING', 'CONFIRMED', 'EXTENDED/AGING', 'INVALIDATED'].map(s => <option key={s}>{s}</option>)}</select></label>
      <label>Rank by<select value={sort} onChange={e => setSort(e.target.value as typeof sort)}><option value="score">Research score</option><option value="return_63d">3-month momentum</option><option value="relative_volume">Relative volume</option><option value="dollar_volume_20d">Liquidity</option><option value="completeness">Evidence coverage</option></select></label>
      <label>Sector<select value={preferences.sector} onChange={e => setPreferences({...preferences, sector: e.target.value})}><option value="ALL">All sectors</option>{[...new Set(run?.signals.map(s => s.sector))].filter(Boolean).map(s => <option key={s}>{s}</option>)}</select></label>
      <label>Cap bucket (fixture strata)<select value={capBucket} onChange={e => setCapBucket(e.target.value)}><option value="ALL">All cap buckets</option>{[...new Set(run?.signals.map(s => s.cap_bucket))].filter(Boolean).map(b => <option key={b}>{b}</option>)}</select></label><label>Minimum 3M return (%)<input type="number" value={momentumFloor} onChange={e => setMomentumFloor(Number(e.target.value))} /></label><label>Minimum relative volume<input type="number" min="0" step=".1" value={volumeFloor} onChange={e => setVolumeFloor(Math.max(0, Number(e.target.value)))} /></label></div>
      <div className="button-row"><label className="check-label"><input type="checkbox" checked={preferences.watchOnly} onChange={e => setPreferences({...preferences, watchOnly: e.target.checked})} />Saved watchlist only</label><label className="check-label"><input type="checkbox" checked={consolidationOnly} onChange={e => setConsolidationOnly(e.target.checked)} />Consolidating bases only</label></div>
    <div className="table-scroll" tabIndex={0}><table><caption className="sr-only">Synthetic research candidates</caption><thead><tr><th>Security / permanent ID</th><th>Stage</th><th>Score*</th><th>1D</th><th>1W</th><th>1M</th><th>3M</th><th>Coverage</th><th>Saved</th></tr></thead>
      <tbody>{filtered.map(s => <tr key={s.security_id}><td><button className="security" onClick={() => open(s)}>{s.ticker}<small>{s.security_id}</small></button></td><td><span className="stage">{s.stage}</span></td><td><button className="score" aria-label={`${s.score.toFixed(1)} / 100 ↗ Score breakdown for ${s.ticker}`} onClick={() => open(s)}>{s.score.toFixed(1)} <span>/ 100 ↗</span></button></td>{[s.return_1d, s.return_5d, s.return_21d, s.return_63d].map((r, i) => <td className={r >= 0 ? 'positive' : 'negative'} key={i}>{pct(r)}</td>)}<td>{(s.completeness * 100).toFixed(0)}%</td><td><button aria-label={`${preferences.watchlist.includes(s.security_id) ? 'Saved' : 'Save'} ${s.ticker} to watchlist`} aria-pressed={preferences.watchlist.includes(s.security_id)} onClick={() => setPreferences({...preferences, watchlist: preferences.watchlist.includes(s.security_id) ? preferences.watchlist.filter(id => id !== s.security_id) : [...preferences.watchlist, s.security_id]})}>{preferences.watchlist.includes(s.security_id) ? 'Saved' : 'Save'}</button></td></tr>)}</tbody></table></div>
    {filtered.length === 0 && <p className="empty">No securities match these filters.</p>}
    <p className="footnote">*Unvalidated heuristic. Missing components reduce the attainable score; coverage is not a probability.</p></section>;

  return <div className="shell"><aside><a className="brand" href="#" onClick={() => setPage('Command Center')}><span className="brandmark">BH</span><span>BagHunter<small>100-BAGGER DNA LAB</small></span></a>
    <div className="nav-label">RESEARCH WORKSPACE</div><nav aria-label="Research views">{pages.map((p, i) => <button key={p} aria-current={p === page ? 'page' : undefined} onClick={() => setPage(p)}><span className="nav-icon" aria-hidden="true">{['◈', '⌁', '▦', '⌘', '▧', '◷', '◇', '⚙', '▤'][i]}</span>{p}</button>)}</nav>
    <div className="sidebar-note"><span className="dot"/> LOCAL LAB<small>Research & simulation only<br/>No order routing</small></div></aside>
    <div className="workspace"><header><div><span className="breadcrumb">WORKSPACE</span><span className="slash">/</span>{page}</div><span className="tag">{page === 'Finviz Observations' ? 'LOCAL SNAPSHOT' : page === 'Data Quality' ? 'SOURCE AUDIT' : 'OFFLINE FIXTURE'}</span></header>
      <main><div className="page-heading"><div><p className="eyebrow">EVIDENCE BEFORE CONVICTION</p><h1>{page}</h1><p className="subtitle">{page === 'Finviz Observations' ? 'Saved provider observations with unresolved coverage gaps.' : 'A point-in-time lens on asymmetric equity research.'}</p></div>{page !== 'Finviz Observations' && <button className="secondary" onClick={() => {setActiveRun('current'); setReload(n => n + 1);}}>↻ Reload local run</button>}</div>
      {page === 'Finviz Observations' ? <FinvizBrowser/> : <>{page === 'Data Quality' ? <><div className="warning" role="note"><strong>SOURCE AUDIT · RESEARCH ONLY</strong><span>Each source states its fixture or external scope. Evidence inspection does not activate research inputs.</span></div><SecEvidenceBrowser/></> : <div className="warning" role="note"><strong>SYNTHETIC FIXTURE · RESEARCH ONLY</strong><span>Fictional prices, filings and outcomes. No empirical alpha findings or live candidates.</span></div>}
      {error ? <section className="panel" role="alert"><h2>Research data unavailable</h2><p>{error}</p><button onClick={() => setReload(n => n + 1)}>Retry connection</button></section> : !run ? <p role="status">Loading local research run…</p> : <>
        <div className="asof"><span><span className="dot amber"/> Historical clock: {run.asof}</span><span>STALE / FIXTURE · {run.age_days} days old</span><span>Run {run.run_id}</span></div>
        {storageError && <p role="status">{storageError}</p>}
        {page === 'Command Center' && <><RunTools key={run.run_id} run={run} onSelect={setActiveRun} /><div className="stats"><article><p>ELIGIBLE RESEARCH UNIVERSE</p><strong>{run.signals.length.toString().padStart(2, '0')}</strong><small>Fictional common shares</small></article><article><p>NEW IGNITIONS</p><strong>{run.signals.filter(s => s.stage === 'IGNITION').length.toString().padStart(2, '0')}</strong><small>Rules applied at historical clock</small></article><article><p>SOURCE COVERAGE</p><strong>Fixture<span> only</span></strong><small>Research feed remains synthetic</small></article><article><p>VERIFIED LIVE THESES</p><strong>00</strong><small>Insufficient real evidence</small></article></div>
          <div className="overview"><section className="panel"><div className="panel-title"><div><h2>Observe. Compare. Falsify.</h2><p>Follow the evidence through the lab.</p></div><span className="tag">v0.1</span></div><div className="steps">{['Point-in-time inputs', 'Failed peer controls', 'Frozen screening rules', 'Transparent limitations'].map((s, i) => <div key={s}><span>0{i + 1}</span>{s}</div>)}</div></section><section className="panel"><h2>Research boundary</h2><p>Fixture regime: {run.discovery?.regime ?? 'Unavailable'}. Positive 1M breadth: {percent(run.discovery?.breadth)}. Benchmark 3M: {percent(run.discovery?.benchmark_return_63d)}. Descriptive fixture observations only; saved Finviz observations have a separate view.</p><button className="text-button" onClick={() => setPage('Data Quality')}>Inspect data quality →</button></section></div>{run.discovery && <section className="panel"><h2>Discovery stage distribution</h2><a href={`/api/runs/${run.run_id}/reports/discovery_digest.md`}>Download discovery digest</a><div className="stage-distribution">{['WATCH', 'IGNITION', 'EMERGING', 'CONFIRMED', 'EXTENDED/AGING', 'INVALIDATED'].map(s => <button key={s} onClick={() => {setStage(s); setPage('BagHunter Radar');}}>{s}<strong>{run.discovery?.stage_counts[s] ?? 0}</strong></button>)}</div></section>}{radar}</>}
        {page === 'BagHunter Radar' && radar}
        {page === 'Thesis Studio' && candidate && <><label>Thesis security<select value={candidate.security_id} onChange={e => setSelected(e.target.value)}>{run.signals.map(s => <option key={s.security_id} value={s.security_id}>{s.ticker}</option>)}</select></label><ThesisStudio key={`${run.run_id}-${candidate.security_id}`} candidate={candidate} run={run} /></>}
        {page === 'Settings' && <Settings key={run.run_id} run={run} preferences={preferences} onChange={setPreferences} />}
        {page === 'Candidate DNA' && candidate && <><section className="panel"><div className="panel-title"><div><p className="eyebrow">{candidate.security_id}</p><h2>{candidate.ticker} · {candidate.name}</h2><p>{candidate.stage} · price session {candidate.price_session} · {money(candidate.close)}</p></div><label>Security<select value={candidate.security_id} onChange={e => setSelected(e.target.value)}>{run.signals.map(s => <option key={s.security_id} value={s.security_id}>{s.ticker}</option>)}</select></label></div>
          <PriceChart candidate={candidate} /></section>
          <div className="overview"><section className="panel"><h2>Score ingredients</h2><p>Unvalidated score {candidate.score.toFixed(1)} / 100 · {(candidate.completeness * 100).toFixed(0)}% factor coverage</p>{Object.entries(candidate.components).map(([key, value]) => <div className="factor" key={key}><div><span>{pretty(key)}</span><span>{value === null ? 'Missing' : value.toFixed(1)} · weight {candidate.weights[key] * 100}%</span></div><div className="meter"><span style={{width: `${value ?? 0}%`}}/></div></div>)}<p className="footnote">Missing inputs stay null. Weights are not redistributed.</p></section><section className="panel"><h2>Disconfirmations & gaps</h2><ul>{candidate.limitations.map(s => <li key={s}>{s}</li>)}</ul><p>20D dollar volume: {money(candidate.dollar_volume_20d)}<br/>Relative volume: {candidate.relative_volume.toFixed(2)}×</p><p>{run.thesis_status}</p></section></div>
          <TechnicalEvidence technical={candidate.technical} relative={candidate.relative_evidence} runId={run.run_id} />
          <section className="panel"><div className="panel-title"><div><h2>Setup & stage history</h2><a href={`/api/runs/${run.run_id}/dossiers/${candidate.security_id}`}>Download research dossier</a><p>{candidate.stage_reason ?? 'Stage history unavailable in this archive'}</p></div><button className="secondary" onClick={() => setPage('Thesis Studio')}>Open Thesis Studio</button></div><p>Sector: {candidate.sector ?? 'Missing'} · 3M relative strength: {percent(candidate.relative_strength_63d)} · sector breadth: {percent(candidate.sector_breadth)} ({candidate.sector_peer_count ?? 0} peers) · annualized 20D volatility: {percent(candidate.volatility_20d)}</p><p>Prior 60-session base high: {money(candidate.base_high_60d)}; consolidation: {candidate.consolidation ? 'Within configured width' : 'Outside configured width'}. The table records the prior 60-session base rule at each clock.</p><div className="table-scroll" tabIndex={0}><table><caption className="sr-only">Dated discovery stage history</caption><thead><tr><th>Session</th><th>Stage</th><th>Close</th><th>Score</th><th>Reason</th></tr></thead><tbody>{candidate.stage_history?.map(h => <tr key={h.asof}><td>{h.session}</td><td>{h.stage}</td><td>{money(h.close)}</td><td>{h.score.toFixed(1)}</td><td className="wrap-cell">{h.reason}</td></tr>)}</tbody></table></div><p>20D moving average: {candidate.technical?.sma_20 != null ? money(candidate.technical.sma_20) : 'Missing'} · 50D: {candidate.technical?.sma_50 != null ? money(candidate.technical.sma_50) : 'Missing'} · 200D: {candidate.technical?.sma_200 == null ? 'Missing' : money(candidate.technical.sma_200)} · ATR20: {candidate.technical?.atr_20 != null ? money(candidate.technical.atr_20) : 'Missing'} · source age at historical clock: {candidate.technical?.stale_calendar_days ?? 'Missing'} calendar days.</p><p>Risk flags: {candidate.risk_flags?.join(', ') ?? 'Unavailable'}</p></section>
          <section className="panel"><h2>Dated financial statement ratios</h2><p>Annual USD statements at period {candidate.financials?.period_end ?? 'Missing'}. Revisions require the publication clock plus processing lag. Missing or incompatible units remain missing.</p>{!!candidate.financials?.numeric_limits?.length && <p>Financial arithmetic outside supported numeric range: {candidate.financials.numeric_limits.join(', ')}. Affected values remain missing.</p>}<div className="scenario-grid">{[['Revenue growth', candidate.financials?.revenue_growth], ['Growth acceleration', candidate.financials?.revenue_growth_acceleration], ['Operating margin', candidate.financials?.operating_margin], ['Net margin', candidate.financials?.net_margin], ['Cashflow margin', candidate.financials?.cashflow_margin]].map(([name, value]) => <article className="scenario-card" key={String(name)}><h3>{name}</h3><strong>{percent(value as number | undefined | null)}</strong></article>)}</div></section>
          <section className="panel"><h2>What was knowable</h2><p>24-hour processing lag after publication. Values below are fictional filing evidence.</p><div className="table-scroll" tabIndex={0}><table><caption className="sr-only">Point-in-time filing evidence</caption><thead><tr><th>Metric / period</th><th>Value</th><th>First public (UTC)</th><th>Source / accession</th></tr></thead><tbody>{candidate.evidence.map(f => <tr key={`${f.accession}-${f.metric}-${f.period_end}`}><td>{pretty(f.metric)}<small>{f.period_end}</small></td><td>{money(f.value)}</td><td>{f.published_at}</td><td><a href={`/api/sources/${f.source_id}`} target="_blank" rel="noreferrer">{f.accession} ↗</a>{f.amended && ' · amendment'}</td></tr>)}</tbody></table></div></section></>}
        {page === '100-Bagger Museum' && <><CohortExplorer run={run} /><section className="panel"><p className="eyebrow">HINDSIGHT OUTCOMES · ISOLATED FROM PREDICTORS</p><h2>One case. One failed lookalike.</h2><a href={`/api/runs/${run.run_id}/reports/historical_cases.md`}>Download historical case report</a><p>Anchor {run.study.anchor}. {run.study.scope}. Denominator: {run.study.denominator}.</p><p>One-year 5× maximum-hit case, matched by dated fixture strata. A max-hit multiple differs from a holding return.</p>{run.study.pairs.map(p => <div className="pair" key={p.case_security_id}><strong>{p.case_security_id} <span>vs</span> {p.control_security_id}</strong><p>Control sampling weight: {p.control_weight}. Retrospective sampling does not estimate population hit probability.</p></div>)}</section><section className="panel"><h2>Evidence at the historical anchor</h2><p>These profiles use only observations available by the anchor, separate from future outcomes.</p>{run.study.anchor_features.filter(f => run.study.pairs.some(p => p.case_security_id === f.security_id || p.control_security_id === f.security_id)).map(f => <details key={f.security_id}><summary>{f.name} · {f.security_id} · as-of {f.asof_time}</summary><p>Raw fixture close {money(f.close)} · 3M momentum {pct(f.return_63d)}</p><LineChart series={[{name: f.security_id, values: f.chart.map(p => p.close)}]} label={`Knowable fixture history through ${f.price_session} · raw USD`}/><ul>{f.evidence.map(e => <li key={`${e.accession}-${e.metric}-${e.period_end}`}>{pretty(e.metric)}: {money(e.value)} · period {e.period_end} · first public {e.published_at} · <a href={`/api/sources/${e.source_id}`} target="_blank" rel="noreferrer">{e.accession} ↗</a></li>)}</ul></details>)}</section><section className="panel"><h2>Prospective horizon labels</h2><div className="table-scroll" tabIndex={0}><table><caption className="sr-only">Fixture future outcomes</caption><thead><tr><th>Permanent ID</th><th>Horizon</th><th>Max multiple</th><th>Terminal return</th><th>Drawdown</th><th>Coverage</th><th>Saved</th></tr></thead><tbody>{run.study.labels.map(l => <tr key={`${l.security_id}-${l.horizon_years}`}><td>{l.security_id}</td><td>{l.horizon_years}Y</td><td>{l.max_multiple === null ? 'Missing' : `${l.max_multiple.toFixed(2)}×`}</td><td>{pct(l.terminal_total_return)}</td><td>{pct(l.max_drawdown)}</td><td>{pretty(l.coverage_flag)}</td></tr>)}</tbody></table></div></section></>}
        {page === 'Validation Lab' && <><ValidationTools run={run} /><section className="panel"><p className="eyebrow">DEMONSTRATION · NO EMPIRICAL VALIDATION</p><h2>Walk-forward mechanics</h2><p>{run.backtest.period_start} → {run.backtest.period_end}</p><p>{run.backtest.split}</p><p>{run.backtest.execution} · {run.backtest.cost_round_trip_bps} bps round trip.</p><LineChart series={(['selector', 'equal_weight', 'benchmark'] as const).map(key => ({name: pretty(key), values: run.backtest.equity_curve.map(p => p[key])}))} label="FIXTURE · wealth per initial dollar · synthetic cash-dividend basis"/><ul>{run.backtest.limitations.map(l => <li key={l}>{l}</li>)}</ul></section><section className="panel"><h2>Screening windows & baseline comparison</h2><div className="table-scroll" tabIndex={0}><table><caption className="sr-only">Toy evaluation execution audit</caption><thead><tr><th>Decision</th><th>Next-open entry</th><th>Exit</th><th>Selected</th><th>Net</th><th>Equal weight</th><th>Market</th></tr></thead><tbody>{run.backtest.rows.map(r => <tr key={r.decision}><td>{r.decision}</td><td>{r.entry}</td><td>{r.exit}</td><td>{r.security_id}</td><td>{pct(r.net_return)}</td><td>{pct(r.equal_weight_net)}</td><td>{pct(r.benchmark_net)}</td></tr>)}</tbody></table></div></section></>}
        {page === 'Data Quality' && <><section className="panel"><h2>Source ledger</h2><p>Selected run integrity: {run.archive_integrity ?? 'Legacy archive'}. Source checksums do not establish market-data entitlement or historical completeness.</p>{run.sources.map(s => <div key={s.source_id}><h3>{s.source_id} · SYNTHETIC</h3><p>{s.coverage}</p><p>{s.license_note}</p><p>Latest fixture timestamp: {s.latest_source_timestamp}. This differs from the research as-of cutoff.</p><label>Immutable raw SHA-256<code>{s.sha256}</code></label><p className="warning">BLOCKED: {s.market_provider.reason}</p></div>)}</section><section className="panel"><h2>Integrity & known limitations</h2><div className="button-row"><a href={`/api/runs/${run.run_id}/reports/source_manifest.json`}>Download source manifest</a><a href={`/api/runs/${run.run_id}/reports/research_limitations.md`}>Download limitations</a></div><ul>{run.limitations.map(l => <li key={l}>{l}</li>)}</ul><p>Feature version: {run.model_version}. SEC accession-bound facts remain quarantined until identity and original-vintage coverage are established.</p><p>No 3–5 live theses: zero names have sufficient real candidate evidence.</p><a href="https://www.sec.gov/search-filings/edgar-application-programming-interfaces" target="_blank" rel="noreferrer">SEC API documentation ↗</a></section></>}
      </>}
      </>}<footer>BagHunter <span>Research is a process of eliminating explanations.</span><span>LOCAL · v0.1.0</span></footer></main></div>
  </div>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);
